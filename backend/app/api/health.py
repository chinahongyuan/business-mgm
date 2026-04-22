from flask import jsonify

from app.api import bp


@bp.get("/health")
def health():
    return jsonify({"ok": True})
