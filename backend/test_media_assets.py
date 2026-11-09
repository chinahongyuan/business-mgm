"""Media generation and read-only delivery contract; no database required."""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from types import SimpleNamespace
from urllib.parse import unquote

import pytest
from PIL import Image
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent))


def service():
    assert importlib.util.find_spec("app.services.media_assets"), "Media service must exist"
    return importlib.import_module("app.services.media_assets")


def make_image(root, size=(1600, 1000), name="商品/a.jpg"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (90, 120, 180)).save(path)
    return path


def local_file(root, url):
    return root / unquote(url.removeprefix("/uploads/"))


def test_image_variants_are_real_webp_and_original_is_untouched(tmp_path):
    media = service()
    path = make_image(tmp_path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    result = media.process_media(path, tmp_path)
    assert result["status"] == "ready"
    asset = media.get_media("/uploads/%E5%95%86%E5%93%81/a.jpg", tmp_path)
    assert asset["width"] == 1600 and asset["height"] == 1000
    assert [v["width"] for v in asset["images"]] == [320, 640, 720, 1080]
    for variant in asset["images"]:
        derived = local_file(tmp_path, variant["url"])
        with Image.open(derived) as image:
            assert image.format == "WEBP"
            assert image.size == (variant["width"], variant["height"])
        assert variant["bytes"] == derived.stat().st_size
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert media.process_media(path, tmp_path)["media"] == asset


def test_small_image_is_not_upscaled_and_animation_falls_back(tmp_path):
    media = service()
    small = make_image(tmp_path, (150, 90))
    result = media.process_media(small, tmp_path)
    assert [v["width"] for v in result["media"]["images"]] == [150]
    animated = tmp_path / "animation.gif"
    Image.new("RGB", (100, 100), "red").save(
        animated, save_all=True, append_images=[Image.new("RGB", (100, 100), "blue")], duration=100, loop=0
    )
    assert media.process_media(animated, tmp_path)["status"] == "skipped"
    assert media.get_media("/uploads/animation.gif", tmp_path) is None


@pytest.mark.parametrize("url", ["https://host/uploads/a.jpg", "//host/uploads/a.jpg", "/uploads/../secret.jpg", "/uploads/%2e%2e/secret.jpg", "/uploads/a%5c..%5csecret.jpg", "/uploads/C:/secret.jpg", "/uploads/a.jpg?x=1", "/uploads/%00.jpg"])
def test_untrusted_urls_never_resolve(tmp_path, url):
    assert service().get_media(url, tmp_path) is None


def test_corrupt_stale_or_missing_derived_metadata_falls_back_without_writes(tmp_path):
    media = service()
    path = make_image(tmp_path)
    result = media.process_media(path, tmp_path)
    url = result["media"]["original"]
    manifest = next((tmp_path / "_media").glob("*.json"))
    original_json = manifest.read_bytes()
    manifest.write_text("[broken", encoding="utf-8")
    assert media.get_media(url, tmp_path) is None
    assert manifest.read_text(encoding="utf-8") == "[broken"
    manifest.write_bytes(original_json)
    local_file(tmp_path, result["media"]["images"][0]["url"]).unlink()
    assert media.get_media(url, tmp_path) is None
    media.process_media(path, tmp_path)
    Image.new("RGB", (1800, 1000), "green").save(path)
    assert media.get_media(url, tmp_path) is None


def test_detail_map_preserves_exact_html_urls_and_read_path_does_not_generate(tmp_path):
    media = service()
    path = make_image(tmp_path)
    media.process_media(path, tmp_path)
    raw = "/uploads/商品/a.jpg"
    html = f'<img src="{raw}"><video src="/uploads/movie.mp4"><source src="https://host/movie.mp4"></video>'
    assets = media.detail_media(html, tmp_path)
    assert set(assets) == {raw, "/uploads/movie.mp4", "https://host/movie.mp4"}
    assert assets[raw]["original"] == raw
    assert assets["/uploads/movie.mp4"] is None
    assert assets["https://host/movie.mp4"] is None


def test_missing_video_tools_record_failure_and_preserve_upload(tmp_path, monkeypatch):
    media = service()
    monkeypatch.setenv("MEDIA_FFMPEG", str(tmp_path / "absent-ffmpeg"))
    monkeypatch.setenv("MEDIA_FFPROBE", str(tmp_path / "absent-ffprobe"))
    source = tmp_path / "movie.mp4"
    source.write_bytes(b"original-movie")
    result = media.process_media(source, tmp_path)
    assert result["status"] == "failed"
    assert "missing" in result["reason"].lower()
    assert media.get_media("/uploads/movie.mp4", tmp_path) is None
    assert source.read_bytes() == b"original-movie"


def test_upload_delivery_limits_cache_and_preserves_ranges(tmp_path, monkeypatch):
    from app import _register_upload_routes
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    known = "a" * 32 + ".mp4"
    (tmp_path / known).write_bytes(b"0123456789")
    (tmp_path / "mutable.mp4").write_bytes(b"0123456789")
    app = Flask(__name__)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 604800
    _register_upload_routes(app)
    with app.test_client() as client:
        response = client.get(f"/uploads/{known}", headers={"Range": "bytes=2-5"})
        assert response.status_code == 206
        assert response.data == b"2345"
        assert response.headers["Content-Range"] == "bytes 2-5/10"
        assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        response = client.get("/uploads/mutable.mp4")
        assert response.headers["Cache-Control"] == "no-cache, max-age=0, must-revalidate"


@pytest.mark.parametrize("size, expected", [
    ("1280x720", [(852, 480), (1280, 720)]),
    ("320x180", [(320, 180)]),
    ("720x1280", [(480, 852), (720, 1280)]),
])
def test_real_transcode_creates_low_first_video_and_poster(tmp_path, size, expected):
    import os
    ffmpeg = os.environ.get("MEDIA_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("MEDIA_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("Install ffmpeg + ffprobe to run the real transcode test")
    source = tmp_path / "movie.mp4"
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c=blue:s={size}:r=24", "-f", "lavfi", "-i", "sine=frequency=440", "-t", "0.3", "-c:v", "libx264", "-c:a", "aac", str(source)], check=True, capture_output=True)
    original = source.read_bytes()
    result = service().process_media(source, tmp_path)
    assert result["status"] == "ready", result
    asset = result["media"]
    assert [v["label"] for v in asset["videos"]] == ["480p", "720p"][:len(expected)]
    assert [(v["width"], v["height"]) for v in asset["videos"]] == expected
    assert local_file(tmp_path, asset["poster"]).exists()
    for variant in asset["videos"]:
        output = local_file(tmp_path, variant["url"])
        data = output.read_bytes()
        assert data.find(b"moov") < data.find(b"mdat")
        probe = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-of", "json", str(output)], check=True, capture_output=True, text=True)
        streams = json.loads(probe.stdout)["streams"]
        assert {stream["codec_name"] for stream in streams} == {"h264", "aac"}
    assert source.read_bytes() == original


def test_queue_is_bounded_persists_overflow_and_recovers_after_restart(tmp_path, monkeypatch):
    media = service()
    assert hasattr(media, "MediaQueue"), "A bounded background queue is required"
    started, release = threading.Event(), threading.Event()
    processed = []

    def processor(path, root):
        started.set()
        release.wait(5)
        processed.append(Path(path).name)
        return media.process_media(path, root)

    monkeypatch.setenv("MEDIA_FFMPEG", str(tmp_path / "missing-ffmpeg"))
    queue = media.MediaQueue(capacity=1, processor=processor)
    try:
        for name in ("first.mp4", "second.mp4", "overflow.mp4"):
            (tmp_path / name).write_bytes(b"movie")
        assert queue.submit(tmp_path / "first.mp4", tmp_path)["status"] == "pending"
        assert started.wait(2)
        assert queue.submit(tmp_path / "second.mp4", tmp_path)["status"] == "pending"
        overflow = queue.submit(tmp_path / "overflow.mp4", tmp_path)
        assert overflow["status"] == "pending" and "full" in overflow["reason"]
        assert media.get_media("/uploads/overflow.mp4", tmp_path) is None
        release.set()
        queue.join()
    finally:
        release.set()
        queue.close()
    restarted = media.MediaQueue(capacity=1)
    try:
        restarted.recover(tmp_path)
        restarted.join()
        record = media.media_status(tmp_path / "overflow.mp4", tmp_path)
        assert record["status"] == "failed" and "missing" in record["reason"]
    finally:
        restarted.close()


def test_upload_response_and_list_serializer_expose_additive_media(tmp_path, monkeypatch):
    from app.api import upload, mobile_public
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    image = io.BytesIO()
    Image.new("RGB", (800, 600), "red").save(image, "JPEG")
    original = image.getvalue()
    image.seek(0)
    app = Flask(__name__)
    with app.test_request_context("/api/upload", method="POST", data={"file": (image, "original.jpg"), "productName": "商品"}):
        response = upload.upload_file.__wrapped__()
    data = response.get_json()["data"]
    assert data.get("mediaStatus") == "ready"
    assert data["media"]["original"] == data["url"]
    assert local_file(tmp_path, data["url"]).read_bytes() == original
    fields = {"id": 1, "name": "sample", "cover_image": data["url"], "category": None, "tags": [], "star_rating": 1, "status": "active", "price": 1, "address": "", "city": "", "district": "", "longitude": None, "latitude": None, "category_id": None, "flag1": False, "flag2": False, "created_at": None, "visit_count": 0}
    serialized = mobile_public._serialize_product_mobile(SimpleNamespace(**fields))
    assert serialized["coverImage"] == data["url"]
    assert serialized["coverMedia"] == data["media"]


def test_internal_files_and_symlink_escape_are_not_public(tmp_path, monkeypatch):
    from app import _register_upload_routes
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    path = make_image(tmp_path)
    asset = service().process_media(path, tmp_path)["media"]
    app = Flask(__name__)
    _register_upload_routes(app)
    with app.test_client() as client:
        manifest = next((tmp_path / "_media").glob("*.json"))
        assert client.get("/uploads/_media/" + manifest.name).status_code == 404
        assert client.get(asset["images"][0]["url"]).headers["Cache-Control"].endswith("immutable")
    outside = tmp_path.parent / (tmp_path.name + "-outside.jpg")
    Image.new("RGB", (10, 10), "blue").save(outside)
    try:
        (tmp_path / "escape.jpg").symlink_to(outside)
    except OSError:
        pytest.skip("Host does not permit symlink creation")
    assert service().get_media("/uploads/escape.jpg", tmp_path) is None
    assert service().process_media(tmp_path / "escape.jpg", tmp_path)["status"] == "failed"
    with app.test_client() as client:
        assert client.get("/uploads/escape.jpg").status_code == 404


def test_cli_dry_run_is_read_only_apply_is_resumable_and_reports_missing_tools(tmp_path):
    media = service()
    path = make_image(tmp_path)
    cli = Path(__file__).parent / "media_cli.py"
    assert cli.exists(), "Backfill CLI must be available"
    command = [sys.executable, str(cli), "--root", str(tmp_path)]
    dry_run = subprocess.run(command + ["--dry-run"], check=True, capture_output=True, text=True)
    report = json.loads(dry_run.stdout)
    assert report["mode"] == "dry-run" and len(report["items"]) == 1
    assert not (tmp_path / "_media").exists()
    apply = subprocess.run(command + ["--apply"], check=True, capture_output=True, text=True)
    assert json.loads(apply.stdout)["items"][0]["status"] == "ready"
    output = media.get_media("/uploads/%E5%95%86%E5%93%81/a.jpg", tmp_path)["images"][0]["url"]
    before = local_file(tmp_path, output).stat().st_mtime_ns
    subprocess.run(command + ["--apply"], check=True, capture_output=True, text=True)
    assert local_file(tmp_path, output).stat().st_mtime_ns == before
    assert path.exists()


def test_truncated_derivatives_are_repaired_and_mutated_original_gets_new_urls(tmp_path):
    media = service()
    source = make_image(tmp_path)
    first = media.process_media(source, tmp_path)["media"]
    variant = first["images"][0]
    local_file(tmp_path, variant["url"]).write_bytes(b"broken")
    assert media.get_media(first["original"], tmp_path) is None
    media.process_media(source, tmp_path)
    assert media.get_media(first["original"], tmp_path) is not None
    Image.new("RGB", (1600, 1000), "green").save(source)
    second = media.process_media(source, tmp_path)["media"]
    assert first["images"][0]["url"] != second["images"][0]["url"]


@pytest.mark.parametrize("mutate", [
    lambda value: value["media"]["images"][0].update(url="https://host/remote.webp"),
    lambda value: value["media"]["images"][0].update(width=True),
    lambda value: value["media"]["images"].reverse(),
    lambda value: value["media"].update(images=[value["media"]["images"][0]] * 2),
    lambda value: value["media"]["images"][0].update(width=319),
    lambda value: value.update(sha256="f" * 64),
    lambda value: value.update(status="pending"),
])
def test_invalid_manifest_never_reaches_client(tmp_path, mutate):
    media = service()
    source = make_image(tmp_path)
    asset = media.process_media(source, tmp_path)["media"]
    manifest = next((tmp_path / "_media").glob("*.json"))
    data = json.loads(manifest.read_text(encoding="utf-8"))
    mutate(data)
    manifest.write_text(json.dumps(data), encoding="utf-8")
    assert media.get_media(asset["original"], tmp_path) is None


def test_queue_worker_failure_is_persisted_and_does_not_stop_next_job(tmp_path):
    media = service()
    handled = []
    def fail(path, root):
        handled.append(Path(path).name)
        raise RuntimeError("encoder unexpectedly stopped")
    queue = media.MediaQueue(processor=fail)
    try:
        for name in ("one.mp4", "two.mp4"):
            path = tmp_path / name
            path.write_bytes(b"original")
            queue.submit(path, tmp_path)
        queue.join()
        assert handled == ["one.mp4", "two.mp4"]
        for name in handled:
            assert media.media_status(tmp_path / name, tmp_path)["status"] == "failed"
    finally:
        queue.close()


def test_cli_check_reports_missing_tools_without_modifying_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_FFMPEG", str(tmp_path / "missing-ffmpeg"))
    monkeypatch.setenv("MEDIA_FFPROBE", str(tmp_path / "missing-ffprobe"))
    cli = Path(__file__).parent / "media_cli.py"
    result = subprocess.run([sys.executable, str(cli), "--root", str(tmp_path), "--check-tools"], capture_output=True, text=True)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["tools"]["ffmpeg"]["status"] == "missing"
    assert list(tmp_path.iterdir()) == []


def test_read_without_explicit_root_does_not_create_missing_upload_directory(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    monkeypatch.setenv("UPLOAD_DIR", str(missing))
    assert service().get_media("/uploads/example.jpg") is None
    assert not missing.exists()


def test_detail_endpoint_adds_exact_media_map_without_changing_html(tmp_path, monkeypatch):
    from app.api import mobile_public
    from app import disable_api_cache
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    source = make_image(tmp_path)
    asset = service().process_media(source, tmp_path)["media"]
    html = '<p>details</p><img src="/uploads/商品/a.jpg"><video src="/uploads/missing.mp4"></video>'
    fields = {"id": 1, "name": "sample", "cover_image": asset["original"], "detail_html": html, "category": None, "tags": [], "star_rating": 1, "status": "active", "price": 1, "address": "", "city": "", "district": "", "longitude": None, "latitude": None, "flag1": False, "flag2": False, "flag3": True, "visit_count": 0}
    product = SimpleNamespace(**fields)
    class Query:
        def options(self, *args): return self
        def filter(self, *args): return self
        def first(self): return product
    session = SimpleNamespace(query=lambda *args: Query(), commit=lambda: None)
    monkeypatch.setattr(mobile_public, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(mobile_public, "_auth_mobile_visitor", lambda key: SimpleNamespace(status="disabled"))
    monkeypatch.setattr(mobile_public, "_product_ids_with_approved_messages", lambda ids: set())
    app = Flask(__name__)
    app.register_blueprint(mobile_public.bp, url_prefix="/api")
    app.after_request(disable_api_cache)
    with app.test_client() as client:
        response = client.get("/api/mobile/products/1?visitorKey=test1234")
    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    data = response.get_json()["data"]
    assert data["detailHtml"] == html
    assert data["coverImage"] == asset["original"] and data["coverMedia"] == asset
    assert data["detailMedia"]["/uploads/商品/a.jpg"]["images"] == asset["images"]
    assert data["detailMedia"]["/uploads/missing.mp4"] is None
    assert data["visitCount"] == 1


def test_product_named_media_keeps_historical_and_new_uploads_accessible(tmp_path, monkeypatch):
    import io
    from app import _register_upload_routes
    from app.api import upload
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    old = make_image(tmp_path, (800, 600), "_media/" + "a" * 32 + ".jpg")
    old_bytes = old.read_bytes()
    app = Flask(__name__)
    _register_upload_routes(app)
    with app.test_client() as client:
        response = client.get("/uploads/_media/" + old.name)
        assert response.status_code == 200
        assert response.data == old_bytes
    old_result = service().process_media(old, tmp_path)
    assert old_result["status"] == "ready"
    assert service().get_media("/uploads/_media/" + old.name, tmp_path) == old_result["media"]
    with app.test_request_context("/api/upload", method="POST", data={"file": (io.BytesIO(old_bytes), "photo.jpg"), "productName": "_media"}):
        data = upload.upload_file.__wrapped__().get_json()["data"]
    assert data["url"].startswith("/uploads/_media/")
    assert data["mediaStatus"] == "ready"
    with app.test_client() as client:
        assert client.get(data["url"]).data == old_bytes
        for metadata in (tmp_path / "_media").glob("*.json"):
            assert client.get("/uploads/_media/" + metadata.name).status_code == 404
    assert old.read_bytes() == old_bytes


def test_cli_backfills_uuid_originals_in_media_product_directory(tmp_path):
    source = make_image(tmp_path, (800, 600), "_media/" + "b" * 32 + ".jpg")
    internal = tmp_path / "_media/work-interrupted/private.jpg"
    internal.parent.mkdir()
    Image.new("RGB", (100, 100), "red").save(internal)
    cli = Path(__file__).parent / "media_cli.py"
    command = [sys.executable, str(cli), "--root", str(tmp_path)]
    inspection = subprocess.run(command + ["--dry-run"], check=True, capture_output=True, text=True)
    assert [item["source"] for item in json.loads(inspection.stdout)["items"]] == ["_media/" + source.name]
    result = subprocess.run(command + ["--apply"], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["items"][0]["status"] == "ready"
    again = subprocess.run(command + ["--dry-run"], check=True, capture_output=True, text=True)
    assert len(json.loads(again.stdout)["items"]) == 1


@pytest.mark.parametrize("rotation, expected_ratio", [(0, 4 / 3), (90, 3 / 4)])
def test_anamorphic_video_and_poster_keep_display_aspect_ratio(tmp_path, rotation, expected_ratio):
    import os
    ffmpeg = os.environ.get("MEDIA_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("MEDIA_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("Install ffmpeg + ffprobe to test anamorphic video")
    original = tmp_path / "anamorphic.mp4"
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc2=s=720x576:r=24", "-t", "0.3", "-vf", "setsar=16/15", "-c:v", "libx264", str(original)], check=True, capture_output=True)
    source = original
    if rotation:
        source = tmp_path / "rotated.mp4"
        rotated = subprocess.run([ffmpeg, "-y", "-display_rotation", str(rotation), "-i", str(original), "-c", "copy", str(source)], capture_output=True)
        if rotated.returncode:  # FFmpeg 5 uses the legacy metadata option.
            subprocess.run([ffmpeg, "-y", "-i", str(original), "-c", "copy", "-metadata:s:v:0", f"rotate={rotation}", str(source)], check=True, capture_output=True)
        source_probe = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-of", "json", str(source)], check=True, capture_output=True, text=True)
        source_stream = json.loads(source_probe.stdout)["streams"][0]
        assert any(abs(side.get("rotation", 0)) == 90 for side in source_stream.get("side_data_list", []))
    result = service().process_media(source, tmp_path)
    assert result["status"] == "ready", result
    asset = result["media"]
    assert asset["width"] / asset["height"] == pytest.approx(expected_ratio, abs=0.01)
    with Image.open(local_file(tmp_path, asset["poster"])) as poster:
        assert poster.width / poster.height == pytest.approx(expected_ratio, abs=0.01)
    for variant in asset["videos"]:
        output = local_file(tmp_path, variant["url"])
        probe = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-of", "json", str(output)], check=True, capture_output=True, text=True)
        video = json.loads(probe.stdout)["streams"][0]
        assert video["width"] / video["height"] == pytest.approx(expected_ratio, abs=0.01)
        assert video["sample_aspect_ratio"] == "1:1"
        assert variant["width"] <= asset["width"] and variant["height"] <= asset["height"]


@pytest.mark.parametrize("extension", [".mp4", ".mov", ".webm"])
@pytest.mark.parametrize("reference", ["relative", "absolute"])
@pytest.mark.parametrize("stage", ["probe", "encoder"])
def test_disguised_dash_cannot_publish_media_outside_upload_root(tmp_path_factory, monkeypatch, extension, reference, stage):
    import os
    from html import escape
    ffmpeg = os.environ.get("MEDIA_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("MEDIA_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("Install ffmpeg + ffprobe to test input demuxer confinement")
    tmp_path = tmp_path_factory.mktemp("dash")  # Keep Windows derived paths below MAX_PATH.
    # Only the disguised XML is uploaded. It must never disclose a video from
    # outside the upload root through publicly served derived files.
    private_file = tmp_path / "private.mp4"
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=red:s=320x180:r=24", "-t", "1", "-c:v", "libx264", "-movflags", "+faststart", str(private_file)], check=True, capture_output=True)
    root = tmp_path / "uploads"
    root.mkdir()
    base_url = "../private.mp4" if reference == "relative" else private_file.as_posix()
    source = root / ("disguised" + extension)
    source.write_text('<?xml version="1.0" encoding="utf-8"?>'
                      '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT1S" minBufferTime="PT1S" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011">'
                      '<Period duration="PT1S"><AdaptationSet mimeType="video/mp4"><Representation id="0" bandwidth="1000">'
                      f'<BaseURL>{escape(base_url)}</BaseURL><SegmentBase/>'
                      '</Representation></AdaptationSet></Period></MPD>', encoding="utf-8")
    original = source.read_bytes()
    unrestricted = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-of", "json", str(source)], capture_output=True, text=True)
    assert unrestricted.returncode == 0, unrestricted.stderr
    media = service()
    if stage == "encoder":
        # Even if probing were accidentally weakened, encoding must independently
        # refuse external-resource containers before opening their references.
        monkeypatch.setattr(media, "_probe", lambda path, binary: (320, 180))
    result = media.process_media(source, root)
    assert result["status"] == "failed", result
    assert Path(ffprobe if stage == "probe" else ffmpeg).name in result["reason"]
    assert media.get_media("/uploads/" + source.name, root) is None
    assert not list((root / "_media").glob("*.webp"))
    assert not list((root / "_media").glob("*.mp4"))
    assert source.read_bytes() == original


@pytest.mark.parametrize("extension, codec", [(".mp4", "libx264"), (".mov", "libx264"), (".webm", "libvpx-vp9")])
def test_supported_real_video_containers_still_generate(tmp_path, extension, codec):
    import os
    ffmpeg = os.environ.get("MEDIA_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("MEDIA_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("Install ffmpeg + ffprobe to test supported containers")
    source = tmp_path / ("video" + extension)
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=24", "-t", "0.3", "-c:v", codec, str(source)], check=True, capture_output=True)
    original = source.read_bytes()
    result = service().process_media(source, tmp_path)
    assert result["status"] == "ready", result
    assert result["media"]["videos"][0]["width"] == 320
    assert source.read_bytes() == original
