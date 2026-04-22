from __future__ import annotations

import os
import uuid
from datetime import datetime

from flask import current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.api import bp
from app.auth_utils import require_auth
from app.runtime_paths import uploads_dir


def _upload_dir() -> str:
    return uploads_dir()


def _allowed(name: str) -> bool:
    ext = os.path.splitext(name)[1].lower()
    return ext in {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".mp4",
        ".webm",
        ".mov",
    }


@bp.post("/upload")
@require_auth
def upload_file():
    """Multipart file upload; returns public URL path under /uploads/."""
    if "file" not in request.files:
        return jsonify({"message": "缺少 file 字段"}), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"message": "未选择文件"}), 400
    raw = secure_filename(f.filename)
    if not raw or not _allowed(raw):
        return jsonify({"message": "不支持的文件类型"}), 400
    ext = os.path.splitext(raw)[1].lower()
    sub = datetime.utcnow().strftime("%Y%m")
    rel_dir = os.path.join(sub)
    dest_dir = os.path.join(_upload_dir(), rel_dir)
    os.makedirs(dest_dir, exist_ok=True)
    new_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(dest_dir, new_name)
    f.save(path)
    url = f"/uploads/{rel_dir.replace(os.sep, '/')}/{new_name}"
    return jsonify({"data": {"url": url, "name": new_name}})
