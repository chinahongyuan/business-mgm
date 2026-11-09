"""Local media derivatives. Reads never transcode; originals are never modified.

The sidecar is an atomic index, not trusted input. A ready record must match the
source's current stat signature and every local derivative before it is exposed.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction
import hashlib
from html.parser import HTMLParser
import json
import logging
import os
from pathlib import Path
import re
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.parse import quote, unquote, urlsplit

from PIL import Image, ImageOps

from app.runtime_paths import app_package_dir, exe_dir, is_frozen

VERSION = 3
IMAGE_WIDTHS = (320, 640, 720, 1080)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
MAX_PIXELS = 40_000_000
MAX_VIDEO_SECONDS = 1800
GENERATED_NAME = re.compile(r"[a-f0-9]{64}-v[1-9][0-9]*-[a-z0-9]+-[a-f0-9]{64}\.(?:webp|mp4)\Z")
UUID_NAME = re.compile(r"[a-f0-9]{32}\.(?:jpg|jpeg|png|gif|webp|bmp|mp4|webm|mov)\Z")
log = logging.getLogger(__name__)


def _root(root=None):
    return Path(root if root is not None else default_media_root()).resolve()


def default_media_root():
    """Same deployment layout as uploads_dir(), without creating directories."""
    override = (os.environ.get("UPLOAD_DIR") or "").strip()
    if override:
        return Path(override)
    return Path(exe_dir()) / "data/uploads" if is_frozen() else Path(app_package_dir()) / "static/uploads"


def confined_path(rel_path: str, root=None):
    """Resolve a decoded relative path, rejecting traversal and escaping symlinks."""
    if not isinstance(rel_path, str) or not rel_path or any(c in rel_path for c in "\\:\x00"):
        return None
    if any(ord(c) < 32 for c in rel_path):
        return None
    if any(part in ("", ".", "..") for part in rel_path.split("/")):
        return None
    base = _root(root)
    try:
        path = (base / rel_path).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            return None
        return path
    except (OSError, ValueError, RuntimeError):
        return None


def _from_url(url, root):
    if not isinstance(url, str) or not url.startswith("/uploads/"):
        return None
    try:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or parts.query or parts.fragment:
            return None
        return confined_path(unquote(parts.path[9:], errors="strict"), root)
    except (ValueError, UnicodeError):
        return None


def _url(path, root):
    return "/uploads/" + quote(path.relative_to(root).as_posix(), safe="/")


def _signature(path):
    stat = path.stat()
    return {"size": stat.st_size, "mtimeNs": stat.st_mtime_ns}


def _media_dir(root, create=False):
    directory = root / "_media"
    # Derived outputs must stay in a real directory, never a linked destination.
    if directory.is_symlink() or directory.resolve() != directory:
        raise ValueError("unsafe media directory")
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def _manifest(path, root):
    key = hashlib.sha256(path.relative_to(root).as_posix().encode()).hexdigest()
    return _media_dir(root) / f"{key}.json"


def _read_record(path, root):
    try:
        metadata = _manifest(path, root)
        if metadata.is_symlink() or metadata.stat().st_size > 64 * 1024:
            return None
        data = json.loads(metadata.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != VERSION:
            return None
        if data.get("source") != path.relative_to(root).as_posix() or data.get("signature") != _signature(path):
            return None
        return data
    except (OSError, ValueError, TypeError, RuntimeError):
        return None


def _valid_variant(variant, root):
    if not isinstance(variant, dict):
        return False
    if any(type(variant.get(key)) is not int or variant[key] <= 0 for key in ("width", "height", "bytes")):
        return False
    return _valid_output(variant.get("url"), root, variant["bytes"])


def _valid_output(url, root, size=None):
    path = _from_url(url, root)
    return bool(path and path.parent == root / "_media" and GENERATED_NAME.fullmatch(path.name)
                and (size is None or path.stat().st_size == size))


def _is_original(path, root):
    if path is None or not path.is_relative_to(root) or not path.is_file():
        return False
    if path.is_relative_to(root / "_media"):
        # `_media` was a valid product name before derivatives were introduced.
        # Its historical UUID originals coexist safely with distinct internal names.
        return path.parent == root / "_media" and bool(UUID_NAME.fullmatch(path.name))
    return True


def get_media(url, root=None):
    """Return validated MediaAsset or None. This function performs no writes."""
    try:
        base = _root(root)
        path = _from_url(url, base)
        if not _is_original(path, base):
            return None
        record = _read_record(path, base)
        if not record or record.get("status") != "ready":
            return None
        asset = record.get("media")
        if not isinstance(asset, dict) or asset.get("original") != _url(path, base):
            return None
        if any(type(asset.get(key)) is not int or asset[key] <= 0 for key in ("width", "height")):
            return None
        source_hash = record.get("sha256")
        if not isinstance(source_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", source_hash):
            return None
        images, videos = asset.get("images"), asset.get("videos")
        if bool(images) == bool(videos):
            return None
        variants = images or videos
        if not isinstance(variants, list) or not 1 <= len(variants) <= 4:
            return None
        if not all(_valid_variant(v, base) for v in variants):
            return None
        widths = [v["width"] for v in variants]
        if widths != sorted(set(widths)):
            return None
        if any(v["width"] > asset["width"] or v["height"] > asset["height"] for v in variants):
            return None
        if images:
            expected = [w for w in IMAGE_WIDTHS if w <= asset["width"]] or [asset["width"]]
            if path.suffix.lower() not in IMAGE_EXTENSIONS or widths != expected:
                return None
            for variant in images:
                if variant["height"] != max(1, round(asset["height"] * variant["width"] / asset["width"])):
                    return None
                if not _matches_output(variant["url"], source_hash, f'w{variant["width"]}', ".webp"):
                    return None
        if videos:
            if path.suffix.lower() not in VIDEO_EXTENSIONS or not _valid_output(asset.get("poster"), base):
                return None
            if not _matches_output(asset["poster"], source_hash, "poster", ".webp"):
                return None
            if [v.get("label") for v in videos] not in (["480p"], ["480p", "720p"]):
                return None
            for variant in videos:
                if not _matches_output(variant["url"], source_hash, "p" + variant["label"][:-1], ".mp4"):
                    return None
        # HTML may use decoded Unicode. Keep the caller's exact fallback URL.
        return {**asset, "original": url}
    except (OSError, ValueError, TypeError, RuntimeError):
        return None


def _matches_output(url, source_hash, label, extension):
    name = url.rsplit("/", 1)[-1]
    return name.startswith(f"{source_hash}-v{VERSION}-{label}-") and name.endswith(extension)


class _MediaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = dict.fromkeys([])

    def handle_starttag(self, tag, attrs):
        if tag in ("img", "video", "source"):
            for key, value in attrs:
                if key == "src" and value:
                    self.urls[value] = None


def detail_media(html, root=None):
    parser = _MediaParser()
    parser.feed(html or "")
    return {url: get_media(url, root) for url in parser.urls}


def _atomic_record(path, root, record):
    directory = _media_dir(root, create=True)
    destination = _manifest(path, root)
    fd, temp_name = tempfile.mkstemp(prefix="record-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
    finally:
        Path(temp_name).unlink(missing_ok=True)


@contextmanager
def _source_lock(path, root):
    """OS locks are released on process exit; leftover lock files are harmless."""
    _media_dir(root, create=True)
    lock = _manifest(path, root).with_suffix(".lock")
    if lock.is_symlink():
        raise ValueError("unsafe media lock")
    with lock.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _publish(temp, root, source_hash, label):
    destination = _media_dir(root) / f"{source_hash}-v{VERSION}-{label}-{_digest(temp)}{temp.suffix}"
    if destination.is_symlink():
        raise ValueError("unsafe derived output")
    if not destination.exists() or _digest(destination) != _digest(temp):
        os.replace(temp, destination)
    return destination


def _variant(path, root, width, height):
    return {"url": _url(path, root), "width": width, "height": height, "bytes": path.stat().st_size}


def _images(path, root, work, source_hash):
    with Image.open(path) as opened:
        if getattr(opened, "is_animated", False):
            return None
        if opened.width * opened.height > MAX_PIXELS:
            raise ValueError("image exceeds 40 million pixel limit")
        image = ImageOps.exif_transpose(opened)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        width, height = image.size
        targets = [target for target in IMAGE_WIDTHS if target <= width] or [width]
        variants = []
        for target in targets:
            resized = image.resize((target, max(1, round(height * target / width))), Image.Resampling.LANCZOS)
            temp = work / f"image-{target}.webp"
            resized.save(temp, "WEBP", quality=80, method=4)
            output = _publish(temp, root, source_hash, f"w{target}")
            variants.append(_variant(output, root, *resized.size))
        return {"original": _url(path, root), "width": width, "height": height, "images": variants}


def check_tools():
    """Discover configured binaries without running or downloading anything."""
    result = {}
    for name in ("ffmpeg", "ffprobe"):
        configured = os.environ.get(f"MEDIA_{name.upper()}", name)
        found = shutil.which(configured)
        result[name] = {"status": "available" if found else "missing", "path": found}
    return result


def _run(command, timeout=600):
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    result = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=timeout, **kwargs)
    if result.returncode:
        raise ValueError(f"{Path(command[0]).name}: {result.stderr[-1000:]}")
    return result.stdout


def _video_input_options(path):
    """Never autodetect playlists that can reference files outside the root.

    Protocol restrictions alone do not confine local file references. Force a
    supported self-contained demuxer on both inspection and encoding, and disable
    QuickTime external tracks explicitly rather than depending on FFmpeg defaults.
    """
    extension = path.suffix.lower()
    if extension in (".mp4", ".mov"):
        return ["-f", "mov", "-protocol_whitelist", "file", "-enable_drefs", "0", "-use_absolute_path", "0"]
    if extension == ".webm":
        return ["-f", "matroska", "-protocol_whitelist", "file"]
    raise ValueError("unsupported video container")


def _probe(path, binary):
    info = json.loads(_run([binary, "-v", "error", "-show_streams", "-show_format", "-of", "json",
                           *_video_input_options(path), "-i", str(path)], timeout=30))
    stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if not stream:
        raise ValueError("video stream missing")
    width, height = int(stream["width"]), int(stream["height"])
    duration = float(info.get("format", {}).get("duration") or stream.get("duration") or 0)
    if not 0 < width * height <= MAX_PIXELS or not 0 < duration <= MAX_VIDEO_SECONDS:
        raise ValueError("video exceeds dimension/duration limits or duration missing")
    try:
        sar = Fraction(str(stream.get("sample_aspect_ratio", "1:1")).replace(":", "/"))
        if sar <= 0:
            sar = Fraction(1)
    except (ValueError, ZeroDivisionError):
        sar = Fraction(1)
    # Normalize non-square pixels by reducing one axis, never increasing either.
    # FFmpeg autorotates the input before our explicit square-pixel scale filter.
    if sar > 1:
        height = int(height / sar)
    elif sar < 1:
        width = int(width * sar)
    width, height = width // 2 * 2, height // 2 * 2
    if min(width, height) < 2:
        raise ValueError("video display dimensions below encoder minimum")
    rotation = int(stream.get("tags", {}).get("rotate", 0))
    for side in stream.get("side_data_list", []):
        rotation = int(side.get("rotation", rotation))
    if abs(rotation) % 180 == 90:
        width, height = height, width
    return width, height


def _videos(path, root, work, source_hash):
    binaries = check_tools()
    missing = [name for name, info in binaries.items() if info["status"] != "available"]
    if missing:
        raise ValueError("missing tools: " + ", ".join(missing))
    ffmpeg, ffprobe = binaries["ffmpeg"]["path"], binaries["ffprobe"]["path"]
    width, height = _probe(path, ffprobe)
    base = [ffmpeg, "-hide_banner", "-v", "error", "-nostdin", "-y", *_video_input_options(path), "-threads", "2", "-i", str(path)]
    poster = work / "poster.webp"
    poster_width = min(720, width)
    poster_height = max(1, round(height * poster_width / width))
    _run(base + ["-map", "0:v:0", "-frames:v", "1", "-vf", f"scale={poster_width}:{poster_height},setsar=1", "-threads", "2", str(poster)])
    poster = _publish(poster, root, source_hash, "poster")
    variants = []
    previous_size = None
    for target in (480, 720):
        # Short-edge tiers keep portrait video bounded too. Never upscale.
        scale = min(1, target / min(width, height))
        out_width = max(2, int(width * scale) // 2 * 2)
        out_height = max(2, int(height * scale) // 2 * 2)
        if (out_width, out_height) == previous_size:
            continue
        previous_size = out_width, out_height
        temp = work / f"video-{target}.mp4"
        _run(base + ["-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn", "-vf", f"scale={out_width}:{out_height},setsar=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p", "-threads", "2", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", "-map_metadata", "-1", str(temp)])
        output = _publish(temp, root, source_hash, f"p{target}")
        variants.append({**_variant(output, root, out_width, out_height), "label": f"{target}p"})
    return {"original": _url(path, root), "width": width, "height": height, "poster": _url(poster, root), "videos": variants}


def process_media(path, root=None):
    """Synchronous resumable processing used by uploads, queue and backfill CLI."""
    base = _root(root)
    source = Path(path).resolve()
    if not _is_original(source, base):
        return {"status": "failed", "media": None, "reason": "source outside upload root or missing"}
    record = {"version": VERSION, "source": source.relative_to(base).as_posix(), "signature": _signature(source),
              "status": "processing", "media": None, "reason": None}
    try:
        with _source_lock(source, base) as acquired:
            if not acquired:
                return {**record, "status": "pending", "reason": "already processing"}
            existing = get_media(_url(source, base), base)
            if existing:
                return {**record, "status": "ready", "media": existing}
            _atomic_record(source, base, record)
            try:
                source_hash = _digest(source)
                record["sha256"] = source_hash
                with tempfile.TemporaryDirectory(prefix="work-", dir=_media_dir(base)) as workspace:
                    extension = source.suffix.lower()
                    if extension in IMAGE_EXTENSIONS:
                        record["media"] = _images(source, base, Path(workspace), source_hash)
                        record["status"] = "ready" if record["media"] else "skipped"
                        record["reason"] = None if record["media"] else "animated image retains original"
                    elif extension in VIDEO_EXTENSIONS:
                        record["media"] = _videos(source, base, Path(workspace), source_hash)
                        record["status"] = "ready"
                    else:
                        record.update(status="skipped", reason="unsupported media format")
                if _signature(source) != record["signature"]:
                    raise ValueError("source changed during processing")
            except Exception as error:
                record.update(status="failed", media=None, reason=str(error)[:1200])
            _atomic_record(source, base, record)
    except Exception as error:
        record.update(status="failed", media=None, reason=str(error)[:1200])
        log.warning("Media processing unavailable: %s", error)
    return record


def immutable_upload(rel_path):
    parts = rel_path.split("/")
    if len(parts) == 2 and parts[0] == "_media":
        return bool(GENERATED_NAME.fullmatch(parts[1]) or UUID_NAME.fullmatch(parts[1]))
    return "_media" not in parts and bool(UUID_NAME.fullmatch(parts[-1]))


def public_upload_path(rel_path, root=None):
    """Do not expose manifests, locks or partially written work files."""
    parts = rel_path.split("/")
    if "_media" in parts and not (len(parts) == 2 and parts[0] == "_media" and
                                  (GENERATED_NAME.fullmatch(parts[1]) or UUID_NAME.fullmatch(parts[1]))):
        return None
    base = _root(root)
    path = confined_path(rel_path, base)
    if path and path.is_relative_to(base / "_media"):
        if path.parent != base / "_media" or not (GENERATED_NAME.fullmatch(path.name) or UUID_NAME.fullmatch(path.name)):
            return None
    return path


def media_status(path, root=None):
    """Inspect processing status without creating sidecars or doing work."""
    base, source = _root(root), Path(path).resolve()
    if not _is_original(source, base):
        return {"status": "missing", "media": None, "reason": "source missing or outside upload root"}
    record = _read_record(source, base)
    if record and record.get("status") == "ready" and get_media(_url(source, base), base) is None:
        return {"status": "stale", "media": None, "reason": "invalid or missing derivative"}
    return record or {"status": "missing", "media": None, "reason": "no current metadata"}


class MediaQueue:
    """One encoder, at most capacity waiting jobs; overflow persists for recovery.

    The worker also scans pending sidecars while idle, so a full queue never
    loses a job. OS source locks coordinate CLI work and multiple server workers.
    """
    def __init__(self, capacity=8, processor=process_media):
        self.jobs = queue.Queue(maxsize=capacity)
        self.processor = processor
        self._members = set()
        self._roots = set()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._next_recovery = 0.0
        self._thread = threading.Thread(target=self._work, name="media-encoder", daemon=True)
        self._thread.start()

    def submit(self, path, root=None):
        base, source = _root(root), Path(path).resolve()
        if not _is_original(source, base):
            return {"status": "failed", "media": None, "reason": "source outside upload root or missing"}
        record = {"version": VERSION, "source": source.relative_to(base).as_posix(), "signature": _signature(source),
                  "status": "pending", "media": None, "reason": None}
        key = str(source), str(base)
        try:
            with self._lock:
                self._roots.add(base)
                if key in self._members:
                    return record
                if self._stop.is_set():
                    return {**record, "reason": "queue stopped; recover on restart"}
                with _source_lock(source, base) as acquired:
                    if not acquired:
                        return {**record, "reason": "already processing"}
                    current = get_media(_url(source, base), base)
                    if current:
                        return {**record, "status": "ready", "media": current}
                    full = self.jobs.full()
                    if full:
                        record["reason"] = "queue full; pending recovery"
                    _atomic_record(source, base, record)
                    if not full:
                        self._members.add(key)
                        self.jobs.put_nowait(key)
            return record
        except Exception as error:
            log.warning("Media enqueue unavailable: %s", error)
            return {**record, "status": "failed", "reason": str(error)[:1200]}

    def recover(self, root=None):
        base = _root(root)
        with self._lock:
            self._roots.add(base)
        try:
            for metadata in _media_dir(base).glob("*.json"):
                if self._stop.is_set() or self.jobs.full():
                    break
                if metadata.is_symlink() or metadata.stat().st_size > 64 * 1024:
                    continue
                try:
                    record = json.loads(metadata.read_text(encoding="utf-8"))
                    if not isinstance(record, dict) or record.get("status") not in ("pending", "processing"):
                        continue
                    source = confined_path(record.get("source"), base)
                    if source and source.suffix.lower() in VIDEO_EXTENSIONS:
                        self.submit(source, base)
                except (OSError, ValueError, TypeError):
                    continue
        except (OSError, ValueError):
            log.warning("Unable to scan media queue metadata", exc_info=True)

    def _work(self):
        while not self._stop.is_set():
            try:
                key = self.jobs.get(timeout=0.5)
            except queue.Empty:
                if time.monotonic() >= self._next_recovery:
                    self._next_recovery = time.monotonic() + 30
                    with self._lock:
                        roots = tuple(self._roots)
                    for root in roots:
                        self.recover(root)
                continue
            source, root = map(Path, key)
            try:
                self.processor(source, root)
            except Exception as error:
                log.exception("Media worker failed")
                try:
                    record = {"version": VERSION, "source": source.relative_to(root).as_posix(), "signature": _signature(source),
                              "status": "failed", "media": None, "reason": str(error)[:1200]}
                    with _source_lock(source, root) as acquired:
                        if acquired:
                            _atomic_record(source, root, record)
                except Exception:
                    log.exception("Unable to persist media worker failure")
            finally:
                with self._lock:
                    self._members.discard(key)
                self.jobs.task_done()

    def join(self):
        self.jobs.join()

    def close(self):
        self._stop.set()
        self._thread.join(timeout=2)


_background_queue = None
_background_lock = threading.Lock()


def _queue():
    global _background_queue
    with _background_lock:
        if _background_queue is None:
            _background_queue = MediaQueue()
        return _background_queue


def enqueue_media(path, root=None):
    """Upload entrypoint: images synchronously, videos via bounded daemon queue."""
    try:
        if Path(path).suffix.lower() in VIDEO_EXTENSIONS:
            return _queue().submit(path, root)
        return process_media(path, root)
    except Exception as error:
        log.exception("Media generation failed; retaining original upload")
        return {"status": "failed", "media": None, "reason": str(error)[:1200]}


def recover_pending(root=None):
    """Startup hook. Only existing pending videos are considered, never all uploads."""
    base = _root(root)
    try:
        if _media_dir(base).is_dir():
            _queue().recover(base)
    except (OSError, ValueError):
        log.warning("Media recovery unavailable", exc_info=True)
