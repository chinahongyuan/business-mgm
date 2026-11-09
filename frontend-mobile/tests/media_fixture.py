"""Local-only media fixture server. Never initializes or queries the application DB."""
from pathlib import Path
import os
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, ImageDraw
from app import _register_upload_routes, disable_api_cache
from app.services.media_assets import process_media, get_media, detail_media, check_tools

UPLOADS = ROOT / "output/media-review/uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
os.environ["UPLOAD_DIR"] = str(UPLOADS)
urls = []
for i in range(3):
    name = f"{i + 1:032x}.jpg"
    path = UPLOADS / name
    if not path.exists():
        # Deterministic synthetic texture, explicitly not production imagery.
        noise = random.Random(i + 17).randbytes(1280 * 960)
        image = Image.frombytes("L", (1280, 960), noise).convert("RGB")
        draw = ImageDraw.Draw(image)
        draw.rectangle((120, 120, 1160, 840), fill=(64 + i * 25, 110, 150))
        draw.ellipse((320, 160, 960, 800), fill=(180, 200, 215))
        image.save(path, quality=95)
    process_media(path, UPLOADS)
    urls.append(f"/uploads/{name}")

video_name = "f" * 32 + ".mp4"
video_path = UPLOADS / video_name
tools = check_tools()
ffmpeg = os.environ.get("MEDIA_FFMPEG") or "ffmpeg"
if not video_path.exists():
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30",
                    "-t", "5", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
                    str(video_path)], check=True, timeout=60)
process_media(video_path, UPLOADS)
video_url = f"/uploads/{video_name}"
html = f'<p>媒体加载验证</p><img src="{urls[0]}" alt="测试图片"><video controls preload="metadata" src="{video_url}"></video>'
html += f'<p style="height:900px"></p><img src="{urls[1]}" alt="屏外图片">'

app = Flask(__name__, static_folder=None)
_register_upload_routes(app)
app.after_request(disable_api_cache)


@app.get("/__audit")
def audit_entry():
    return "<script>localStorage.setItem('bm_mobile_visitor_key_v2','media-fixture-only');location.replace('/products')</script>"


def product(i=0):
    original = request.cookies.get("media_fixture_mode") == "original"
    return {"id": i + 1, "name": f"媒体测试商品 {i + 1}", "price": 128, "status": "on", "starRating": 4,
            "address": "测试地址", "coverImage": urls[i], "coverMedia": None if original else get_media(urls[i], UPLOADS),
            "detailHtml": html, "detailMedia": {} if original else detail_media(html, UPLOADS)}


@app.route("/api/<path:path>", methods=["GET", "POST"])
def api(path):
    if path == "mobile/products":
        return jsonify(data={"items": [product(i) for i in range(3)], "total": 3})
    if path.startswith("mobile/products/") and path.endswith("messages"):
        return jsonify(data={"items": []})
    if path.startswith("mobile/products/"):
        return jsonify(data=product())
    if path == "mobile/meta":
        return jsonify(data={"cities": [], "districts": [], "tags": [], "categories": []})
    if path == "mobile/home-page":
        return jsonify(data={"mobileTitle": "媒体验证", "published": False})
    return jsonify(data={"published": False})


@app.get("/")
@app.get("/<path:path>")
def frontend(path=""):
    static = ROOT / "backend/app/static/mobile"
    target = (static / path).resolve()
    if target.is_relative_to(static) and target.is_file():
        return send_from_directory(static, path)
    return send_from_directory(static, "index.html", max_age=0)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5015, threaded=True)
