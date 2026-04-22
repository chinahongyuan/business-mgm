/**
 * 详情富文本预处理。
 * 给所有 video 标签添加 playsinline 属性，确保在移动端 WebView 内联播放。
 */
export function enhanceDetailHtml(html: string): string {
  if (!html) return "";
  return html.replace(/<video(\s+[^>]*)?>/gi, (match, attrs = "") => {
    if (attrs.toLowerCase().includes("playsinline")) {
      return match;
    }
    return `<video${attrs} playsinline>`;
  });
}

/**
 * 详情区内多个 video：同一时间仅允许一个播放。
 * - document 捕获阶段监听 play/playing（部分 WebView 内事件不到达 root）
 * - 每个 video 再绑 play/playing/seeked（原生控件路径）
 * - 短轮询兜底：仍有多路同时播放时只保留最后一个（MYUI 等环境）
 */
export function attachExclusiveVideoPlayback(root: HTMLElement | null): () => void {
  if (!root) {
    return () => {};
  }

  let lastPlayedEl: HTMLVideoElement | null = null;

  const pauseOthers = (except: HTMLVideoElement) => {
    root.querySelectorAll<HTMLVideoElement>("video").forEach((v) => {
      if (v !== except) {
        try {
          v.pause();
        } catch {
          /* ignore */
        }
      }
    });
  };

  const onPointerDown = (e: Event) => {
    const t = e.target;
    if (!(t instanceof HTMLVideoElement)) {
      return;
    }
    if (!root.contains(t)) {
      return;
    }
    lastPlayedEl = t;
    pauseOthers(t);
  };

  const onPlayLike = (e: Event) => {
    const t = e.target;
    if (!(t instanceof HTMLVideoElement)) {
      return;
    }
    if (!root.contains(t)) {
      return;
    }
    lastPlayedEl = t;
    pauseOthers(t);
  };

  const perVideoCleanups: (() => void)[] = [];
  const boundVideos = new WeakSet<HTMLVideoElement>();

  const bindOne = (v: HTMLVideoElement) => {
    if (boundVideos.has(v)) return;
    boundVideos.add(v);
    const fn = () => {
      lastPlayedEl = v;
      pauseOthers(v);
    };
    v.addEventListener("play", fn);
    v.addEventListener("playing", fn);
    v.addEventListener("seeked", fn);
    v.addEventListener("pointerdown", fn);
    perVideoCleanups.push(() => {
      v.removeEventListener("play", fn);
      v.removeEventListener("playing", fn);
      v.removeEventListener("seeked", fn);
      v.removeEventListener("pointerdown", fn);
    });
  };

  root.querySelectorAll("video").forEach((v) => {
    if (v instanceof HTMLVideoElement) bindOne(v);
  });

  const mo = new MutationObserver((records) => {
    for (const rec of records) {
      rec.addedNodes.forEach((node) => {
        if (node instanceof HTMLVideoElement) {
          bindOne(node);
        } else if (node instanceof Element) {
          node.querySelectorAll("video").forEach((el) => {
            if (el instanceof HTMLVideoElement) bindOne(el);
          });
        }
      });
    }
  });
  mo.observe(root, { childList: true, subtree: true });

  document.addEventListener("play", onPlayLike, true);
  document.addEventListener("playing", onPlayLike, true);
  root.addEventListener("play", onPlayLike, true);
  root.addEventListener("playing", onPlayLike, true);
  root.addEventListener("pointerdown", onPointerDown);

  const enforceSingle = () => {
    const vids = [...root.querySelectorAll<HTMLVideoElement>("video")];
    const playing = vids.filter((x) => !x.paused && !x.ended);
    if (playing.length <= 1) return;
    const keeper =
      lastPlayedEl && playing.includes(lastPlayedEl) ? lastPlayedEl : playing[playing.length - 1];
    playing.forEach((v) => {
      if (v !== keeper) {
        try {
          v.pause();
        } catch {
          /* ignore */
        }
      }
    });
  };
  const pollId = window.setInterval(enforceSingle, 150);

  return () => {
    document.removeEventListener("play", onPlayLike, true);
    document.removeEventListener("playing", onPlayLike, true);
    root.removeEventListener("play", onPlayLike, true);
    root.removeEventListener("playing", onPlayLike, true);
    root.removeEventListener("pointerdown", onPointerDown);
    mo.disconnect();
    window.clearInterval(pollId);
    perVideoCleanups.forEach((c) => c());
  };
}

/** 详情富文本内点击图片：委托点击，由页面展示大图层。 */
export function attachDetailImageClicks(root: HTMLElement, onOpen: (imageUrl: string) => void): () => void {
  const handler = (e: MouseEvent) => {
    const el = e.target;
    if (!el || el.nodeName !== "IMG") {
      return;
    }
    const img = el as HTMLImageElement;
    const src = img.currentSrc || img.src;
    if (!src) {
      return;
    }
    e.preventDefault();
    e.stopPropagation();
    onOpen(src);
  };
  root.addEventListener("click", handler, true);
  return () => root.removeEventListener("click", handler, true);
}
