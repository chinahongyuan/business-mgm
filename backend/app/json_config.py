"""从 config.json 加载配置（与 wsgi.py 同级目录或项目根目录）。"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote_plus


def _backend_dir() -> str:
    # 本文件位于 backend/app/json_config.py → backend/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _project_root() -> str:
    return os.path.dirname(_backend_dir())


def resolve_config_json_path() -> str | None:
    """返回第一个存在的 config.json 路径。

    优先读取项目根目录 config.json，再读 backend/config.json，避免在根目录维护的
    baidu_map 等配置被空的 backend/config.json 覆盖。
    """
    candidates = [
        os.environ.get("CONFIG_JSON", "").strip(),
        os.path.join(_project_root(), "config.json"),
        os.path.join(_backend_dir(), "config.json"),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def load_raw_config() -> dict[str, Any] | None:
    path = resolve_config_json_path()
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_database_url(data: dict[str, Any]) -> str | None:
    if url := (data.get("database_url") or "").strip():
        return url
    db = data.get("database")
    if not isinstance(db, dict):
        return None
    host = str(db.get("host", "127.0.0.1"))
    port = int(db.get("port", 3306))
    user = quote_plus(str(db.get("user", "root")))
    password = quote_plus(str(db.get("password", "")))
    name = str(db.get("name", "business_mgm"))
    charset = str(db.get("charset", "utf8mb4"))
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset={charset}"


def apply_config_json(app: Any) -> None:
    """将 config.json 合并到 Flask app.config（覆盖类默认值）。"""
    raw = load_raw_config()
    if not raw:
        app.logger.warning("config.json not found or empty; baidu_map and DB from env only")
        return

    cfg_path = resolve_config_json_path()
    app.logger.info("config.json path: %s", cfg_path or "(unknown)")

    if url := build_database_url(raw):
        app.config["SQLALCHEMY_DATABASE_URI"] = url

    sec = raw.get("security")
    if isinstance(sec, dict):
        if v := sec.get("secret_key"):
            app.config["SECRET_KEY"] = str(v)
        if v := sec.get("jwt_secret"):
            app.config["JWT_SECRET"] = str(v)
        if v := sec.get("jwt_expires_hours"):
            app.config["JWT_EXPIRES_HOURS"] = int(v)

    srv = raw.get("server")
    if isinstance(srv, dict):
        if "host" in srv:
            app.config["HOST"] = str(srv["host"])
        if "port" in srv:
            app.config["PORT"] = int(srv["port"])
        if "debug" in srv:
            app.config["DEBUG"] = bool(srv["debug"])

    p = resolve_config_json_path()
    if p:
        app.config["CONFIG_JSON_PATH"] = p

    bm = raw.get("baidu_map")
    if isinstance(bm, dict) and (bm.get("ak") is not None and str(bm.get("ak")).strip()):
        app.config["BAIDU_MAP_AK"] = str(bm["ak"]).strip()
        app.logger.info(
            "baidu_map.ak loaded from config (length=%s)",
            len(app.config["BAIDU_MAP_AK"]),
        )
    elif isinstance(bm, dict):
        app.logger.warning(
            "baidu_map present but ak missing or empty; Baidu map script will not load"
        )
