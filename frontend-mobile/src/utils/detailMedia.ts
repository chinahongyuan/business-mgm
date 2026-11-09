import { imageSrcset, type MediaMap } from "./media";

/** Transform in an inert template BEFORE mounting: parsing must not start video requests. */
export function prepareDetailMedia(html: string, media: MediaMap = {}): string {
  if (!html) return "";
  const template = document.createElement("template");
  template.innerHTML = html;
  template.content.querySelectorAll<HTMLImageElement>("img").forEach((img, index) => {
    const original = img.getAttribute("src") || "";
    const asset = media[original];
    img.dataset.original = original;
    img.loading = index === 0 ? "eager" : "lazy";
    img.decoding = "async";
    img.setAttribute("fetchpriority", index === 0 ? "high" : "auto");
    if (asset?.width && asset.height) {
      img.width = asset.width;
      img.height = asset.height;
    }
    const srcset = imageSrcset(asset);
    if (srcset && !img.closest("picture")) {
      const picture = document.createElement("picture");
      const source = document.createElement("source");
      source.type = "image/webp";
      source.srcset = srcset;
      source.sizes = "(min-width: 1280px) 680px, (min-width: 1024px) 620px, calc(100vw - 58px)";
      img.removeAttribute("srcset");
      img.replaceWith(picture);
      picture.append(source, img);
    }
  });
  template.content.querySelectorAll<HTMLVideoElement>("video").forEach((video) => {
    const original = video.getAttribute("src") || video.querySelector("source")?.getAttribute("src") || "";
    const asset = media[original];
    for (const element of [video, ...video.querySelectorAll("source")]) {
      const src = element.getAttribute("src");
      if (src) element.setAttribute("data-src", src);
      element.removeAttribute("src");
    }
    video.removeAttribute("autoplay");
    video.preload = "none";
    video.controls = false;
    video.setAttribute("playsinline", "");
    if (asset?.poster) video.poster = asset.poster;
    if (asset?.width && asset.height) {
      video.width = asset.width;
      video.height = asset.height;
      video.style.aspectRatio = `${asset.width} / ${asset.height}`;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "detail-video";
    video.replaceWith(wrapper);
    wrapper.append(video);
    const toolbar = document.createElement("div");
    toolbar.className = "detail-video__toolbar";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "detail-video__play";
    button.textContent = "播放视频";
    toolbar.append(button);
    if (asset?.videos?.length) {
      const select = document.createElement("select");
      select.className = "detail-video__quality";
      select.setAttribute("aria-label", "视频清晰度");
      asset.videos.forEach((variant, index) => {
        const option = document.createElement("option");
        option.value = variant.url;
        option.textContent = index === 0 ? "流畅" : "高清";
        select.append(option);
      });
      // A single derivative needs no selector, but still supplies the initial playback URL.
      select.hidden = asset.videos.length < 2;
      toolbar.append(select);
    }
    const status = document.createElement("span");
    status.className = "detail-video__status";
    status.setAttribute("role", "status");
    toolbar.append(status);
    wrapper.append(toolbar);
  });
  return template.innerHTML;
}

/** One lifecycle owner per rich-text root; teardown aborts downloads on navigation. */
export function attachDeferredMedia(root: HTMLElement): () => void {
  const cleanups: (() => void)[] = [];
  root.querySelectorAll<HTMLElement>(".detail-video").forEach((wrapper) => {
    const video = wrapper.querySelector("video")!;
    const button = wrapper.querySelector<HTMLButtonElement>(".detail-video__play")!;
    const select = wrapper.querySelector<HTMLSelectElement>("select");
    const status = wrapper.querySelector<HTMLElement>("[role=status]")!;
    let disposed = false;
    let started = false;
    let failed = false;
    let original = false;
    let generation = 0;
    let seekTo = 0;
    const sourceErrors = new Set<HTMLSourceElement>();
    let startTimer: ReturnType<typeof setTimeout> | undefined;

    const fail = () => {
      if (disposed) return;
      failed = true;
      clearTimeout(startTimer);
      button.hidden = false;
      button.disabled = false;
      button.textContent = "重试播放";
      status.textContent = "视频加载失败";
    };
    const play = () => {
      const attempt = ++generation;
      clearTimeout(startTimer);
      startTimer = setTimeout(fail, 20_000);
      status.textContent = "正在加载";
      button.disabled = true;
      void video.play().catch((error: unknown) => {
        if (disposed || attempt !== generation) return;
        // A native pause (including exclusive playback of another video) cancels play().
        if (error instanceof DOMException && error.name === "AbortError" && video.paused) {
          pause();
          return;
        }
        fail();
      });
    };
    const load = () => {
      sourceErrors.clear();
      video.pause();
      video.removeAttribute("src");
      video.querySelectorAll("source").forEach((source) => source.removeAttribute("src"));
      if (select?.value && !original) video.src = select.value;
      else {
        if (video.dataset.src) video.src = video.dataset.src;
        video.querySelectorAll<HTMLSourceElement>("source[data-src]").forEach((source) => {
          source.src = source.dataset.src!;
        });
      }
      video.load();
    };
    const start = () => {
      if (!started || failed) load();
      started = true;
      failed = false;
      video.controls = true;
      play();
    };
    const clickPoster = () => { if (!started) start(); };
    const changeQuality = () => {
      original = false;
      failed = false;
      if (!started) return; // Choosing a quality before play must not download video.
      seekTo = video.currentTime;
      load();
      play();
    };
    const metadata = () => {
      if (seekTo > 0 && Number.isFinite(video.duration)) {
        video.currentTime = Math.min(seekTo, Math.max(0, video.duration - 0.1));
      }
      seekTo = 0;
    };
    const playing = () => {
      failed = false;
      clearTimeout(startTimer);
      button.hidden = true;
      button.disabled = false;
      status.textContent = "";
    };
    const waiting = () => { if (started) status.textContent = "缓冲中"; };
    const pause = () => {
      if (!video.paused || video.error || failed) return;
      clearTimeout(startTimer);
      status.textContent = "";
      button.disabled = false;
      button.hidden = false;
      button.textContent = "播放视频";
    };
    const error = (event: Event) => {
      if (!started || disposed) return;
      if (event.target instanceof HTMLSourceElement) {
        if (video.getAttribute("src")) return;
        sourceErrors.add(event.target);
        // Source errors do not bubble. Wait for every alternative before exposing retry.
        const alternatives = [...video.querySelectorAll<HTMLSourceElement>("source[src]")];
        if (alternatives.some((source) => !sourceErrors.has(source))) return;
      }
      if (select?.value && !original) {
        original = true;
        seekTo = video.currentTime || seekTo;
        load();
        play();
      } else fail();
    };
    button.addEventListener("click", start);
    video.addEventListener("click", clickPoster);
    select?.addEventListener("change", changeQuality);
    video.addEventListener("loadedmetadata", metadata);
    video.addEventListener("playing", playing);
    video.addEventListener("waiting", waiting);
    video.addEventListener("pause", pause);
    video.addEventListener("error", error, true);
    cleanups.push(() => {
      disposed = true;
      clearTimeout(startTimer);
      generation++;
      button.removeEventListener("click", start);
      video.removeEventListener("click", clickPoster);
      select?.removeEventListener("change", changeQuality);
      video.removeEventListener("loadedmetadata", metadata);
      video.removeEventListener("playing", playing);
      video.removeEventListener("waiting", waiting);
      video.removeEventListener("pause", pause);
      video.removeEventListener("error", error, true);
      video.pause();
      video.removeAttribute("src");
      video.querySelectorAll("source").forEach((source) => source.removeAttribute("src"));
      video.load();
    });
  });

  const retries = new Map<HTMLImageElement, HTMLButtonElement>();
  const onImageError = (event: Event) => {
    const img = event.target;
    if (!(img instanceof HTMLImageElement)) return;
    const picture = img.closest("picture");
    if (picture?.querySelector("source") || img.hasAttribute("srcset")) {
      picture?.querySelectorAll("source").forEach((source) => source.remove());
      img.removeAttribute("srcset");
      img.src = img.dataset.original || img.src;
      return;
    }
    if (retries.has(img)) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "detail-image__retry";
    button.textContent = "重新加载图片";
    button.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      button.remove();
      retries.delete(img);
      const src = img.dataset.original || img.src;
      img.removeAttribute("src");
      img.src = src;
    };
    (picture || img).after(button);
    retries.set(img, button);
  };
  root.addEventListener("error", onImageError, true);
  // Cached failures may occur before this root's mounted hook.
  root.querySelectorAll<HTMLImageElement>("img").forEach((img) => {
    if (img.complete && !img.naturalWidth && img.getAttribute("src")) {
      img.dispatchEvent(new Event("error"));
    }
  });
  return () => {
    root.removeEventListener("error", onImageError, true);
    retries.forEach((button) => { button.onclick = null; button.remove(); });
    cleanups.forEach((cleanup) => cleanup());
  };
}
