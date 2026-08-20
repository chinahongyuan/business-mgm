from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "backend")

from flask import Flask

from app.api import mobile_public


def test_unknown_mobile_visitor_is_an_invalid_session(monkeypatch):
    with Flask(__name__).app_context():
        response, status = mobile_public._mobile_session_error()

    assert status == 401
    assert response.get_json() == {
        "code": "MOBILE_SESSION_INVALID",
        "message": "登录已失效，请重新登录",
    }


def test_unknown_login_key_is_not_reused():
    assert mobile_public._login_visitor_key() != "old-visitor-key"
    assert len(mobile_public._login_visitor_key()) >= 32


def test_api_cache_headers_are_disabled():
    app = Flask(__name__)
    app.register_blueprint(mobile_public.bp, url_prefix="/api")
    from app import disable_api_cache

    app.after_request(disable_api_cache)
    mobile_public._get_home_page_row = lambda: None

    with app.test_client() as client:
        response = client.get("/api/mobile/home-page")

    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Pragma"] == "no-cache"


def test_spa_index_cache_headers_are_disabled(tmp_path: Path):
    from app import _send_spa_index

    (tmp_path / "index.html").write_text("<!doctype html>", encoding="utf-8")
    app = Flask(__name__)

    with app.test_request_context("/"):
        response = _send_spa_index(str(tmp_path))

    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
