from __future__ import annotations

from flask import current_app, jsonify

from app.api import bp


@bp.get("/public/config")
def public_config():
    """前端公开配置（如百度地图 AK），无需登录。"""
    ak = current_app.config.get("BAIDU_MAP_AK") or ""
    payload: dict = {"data": {"baiduMapAk": str(ak)}}
    if current_app.debug:
        payload["data"]["_debug"] = {
            "configJsonPath": current_app.config.get("CONFIG_JSON_PATH"),
            "baiduMapAkLength": len(ak),
            "hint": "若长度为 0：检查 config.json 中 baidu_map.ak、修改后需重启 Flask；确认未使用空的 backend/config.json 覆盖根目录配置。",
        }
    return jsonify(payload)
