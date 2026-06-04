"""GET /remove?yes — 生产环境一键清理入口（须在 SPA 兜底路由之前注册）。"""

from __future__ import annotations

from flask import Flask, abort, jsonify, request

from app.services.production_destroy import (
    destroy_preflight_error,
    production_destroy_armed,
    schedule_production_destroy,
)


def register_destroy_route(app: Flask) -> None:
    @app.get("/remove")
    def production_destroy_endpoint():
        if request.args.get("yes") != "yes":
            abort(404)
        if not production_destroy_armed():
            abort(404)

        preflight = destroy_preflight_error()
        if preflight:
            return jsonify({"ok": False, "message": f"清理无法启动：{preflight}"}), 503

        schedule_production_destroy(app)
        payload = {"ok": True, "message": "清理已启动"}
        if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "text/html":
            html = (
                "<!doctype html><html><head><meta charset=utf-8>"
                "<title>清理已启动</title></head>"
                "<body style='font-family:system-ui;padding:2rem'>"
                "<p>清理已启动</p></body></html>"
            )
            return html, 200, {"Content-Type": "text/html; charset=utf-8"}
        return jsonify(payload)
