import os

from flask import Flask, send_from_directory
from flask_cors import CORS

from app.config import CONFIG, validate_pymysql_database_uri
from app.extensions import db
from app.json_config import apply_config_json
from app.runtime_paths import admin_static_dir, mobile_static_dir, uploads_dir

# Import models so metadata is registered before db.create_all()
from app import models  # noqa: F401


def _admin_static_dir() -> str:
    return admin_static_dir()


def _mobile_static_dir() -> str:
    return mobile_static_dir()


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)

    cfg_key = config_name or "default"
    app.config.from_object(CONFIG.get(cfg_key, CONFIG["default"]))
    apply_config_json(app)
    validate_pymysql_database_uri(app.config.get("SQLALCHEMY_DATABASE_URI"))

    # 静态文件缓存 - 提升页面加载速度
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600 * 24 * 7  # 7天缓存
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB 上传限制

    # API may be called from same origin; keep CORS loose for LAN debugging
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    db.init_app(app)

    with app.app_context():
        from app.schema_mobile_visit_log import ensure_mobile_visit_log
        from app.schema_cms_bulletin import ensure_cms_bulletin
        from app.seed import ensure_announcement_menu_title, ensure_bulletin_menu, ensure_cms_bulletin_row

        for line in ensure_mobile_visit_log():
            app.logger.debug(line)
        for line in ensure_cms_bulletin():
            app.logger.debug(line)
        try:
            ensure_cms_bulletin_row()
            ensure_announcement_menu_title()
            ensure_bulletin_menu()
        except Exception:
            app.logger.exception("ensure_cms_menus")

    # 禁用慢查询日志以提升性能
    # from app.slow_query_log import register_slow_query_logging
    # register_slow_query_logging(app)

    from app.api import bp as api_bp
    from app.destroy_route import register_destroy_route

    app.register_blueprint(api_bp, url_prefix="/api")

    register_destroy_route(app)
    _register_upload_routes(app)

    _register_spa_routes(app)

    @app.cli.command("routes")
    def list_routes():
        """Print registered URL map (debug routing)."""
        for rule in app.url_map.iter_rules():
            print(rule, rule.endpoint)

    @app.cli.command("init-db")
    def init_db():
        """Create tables and seed default admin + menus."""
        db.create_all()
        from app.seed import ensure_cms_rows, ensure_product_categories, seed_database

        seed_database()
        ensure_product_categories()
        ensure_cms_rows()
        print("init-db: done")

    @app.cli.command("ensure-p0-indexes")
    def ensure_p0_indexes_cmd():
        """为已有数据库补充 P0 统计/列表索引（新库已由模型定义创建）。"""
        from app.db_indexes import ensure_p0_indexes

        with app.app_context():
            lines = ensure_p0_indexes()
            for line in lines:
                print(line)

    @app.cli.command("ensure-product-soft-delete")
    def ensure_product_soft_delete_cmd():
        """为已有 mer_product 表增加 deleted_at 软删除列（新库 init-db 已随模型创建）。"""
        from app.schema_soft_delete import ensure_mer_product_deleted_at

        with app.app_context():
            for line in ensure_mer_product_deleted_at():
                print(line)

    @app.cli.command("ensure-cms-home-mobile-title")
    def ensure_cms_home_mobile_title_cmd():
        """为已有 cms_home_page 增加 mobile_title 列。"""
        from app.schema_cms_home_mobile_title import ensure_cms_home_mobile_title

        with app.app_context():
            for line in ensure_cms_home_mobile_title():
                print(line)

    @app.cli.command("ensure-password-expires-nullable")
    def ensure_password_expires_nullable_cmd():
        """口令 expires_at 改为可空（永不过期）。"""
        from app.schema_password_expires_nullable import ensure_app_mobile_login_password_expires_nullable

        with app.app_context():
            for line in ensure_app_mobile_login_password_expires_nullable():
                print(line)

    @app.cli.command("ensure-cms-bulletin")
    def ensure_cms_bulletin_cmd():
        """创建 cms_bulletin 表并补齐公告管理菜单与空记录。"""
        from app.schema_cms_bulletin import ensure_cms_bulletin
        from app.seed import (
            ensure_announcement_menu_title,
            ensure_bulletin_menu,
            ensure_cms_bulletin_row,
        )

        with app.app_context():
            for line in ensure_cms_bulletin():
                print(line)
            ensure_cms_bulletin_row()
            print("ok: cms_bulletin row")
            ensure_announcement_menu_title()
            print("ok: announcement menu title")
            ensure_bulletin_menu()
            print("ok: bulletin menu")

    @app.cli.command("seed-mobile-test-data")
    def seed_mobile_test_data():
        """插入/刷新移动端用户与留言测试数据（visitor_key 前缀 test-vk-）。"""
        from app.seed_mobile_test import run_seed

        run_seed()

    return app


def _register_upload_routes(app: Flask) -> None:
    """Serve uploaded files from uploads_dir() (dev: app/static/uploads; frozen: data/uploads)."""
    from flask import make_response, request

    base = uploads_dir()

    @app.route("/uploads/<path:rel_path>", methods=["GET", "OPTIONS"])
    def serve_upload(rel_path: str):
        if request.method == "OPTIONS":
            response = make_response("", 204)
        else:
            response = make_response(send_from_directory(base, rel_path))
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response


def _register_spa_routes(app: Flask) -> None:
    """移动端 H5：/ ；管理后台：/system-management/* 。构建产物分别在 static/mobile 与 static/admin。"""

    admin_root = _admin_static_dir()
    mobile_root = _mobile_static_dir()

    @app.get("/system-management")
    @app.get("/system-management/")
    def admin_spa_index():
        index = os.path.join(admin_root, "index.html")
        if not os.path.isfile(index):
            return _missing_admin_ui_message()
        return send_from_directory(admin_root, "index.html")

    @app.get("/system-management/<path:path>")
    def admin_spa_assets(path: str):
        target = os.path.join(admin_root, path)
        if os.path.isfile(target):
            return send_from_directory(admin_root, path)
        index = os.path.join(admin_root, "index.html")
        if not os.path.isfile(index):
            return _missing_admin_ui_message()
        return send_from_directory(admin_root, "index.html")

    @app.get("/")
    def mobile_spa_index():
        index = os.path.join(mobile_root, "index.html")
        if not os.path.isfile(index):
            return _missing_mobile_ui_message()
        return send_from_directory(mobile_root, "index.html")

    @app.get("/<path:path>")
    def mobile_spa_or_assets(path: str):
        from flask import abort

        if path.startswith("api"):
            abort(404)
        if path.startswith("uploads"):
            abort(404)
        if path.startswith("system-management"):
            abort(404)

        target = os.path.join(mobile_root, path)
        if os.path.isfile(target):
            return send_from_directory(mobile_root, path)

        index = os.path.join(mobile_root, "index.html")
        if not os.path.isfile(index):
            return _missing_mobile_ui_message()
        return send_from_directory(mobile_root, "index.html")


def _missing_admin_ui_message():
    from flask import Response

    body = (
        "<!doctype html><html><head><meta charset=utf-8><title>Admin UI missing</title></head>"
        "<body style='font-family:system-ui;padding:2rem'>"
        "<h1>管理后台前端未构建</h1>"
        "<p>请在项目根目录执行：<code>cd frontend-admin && npm install && npm run build</code></p>"
        "<p>或使用一键启动：<code>python start.py</code>（会同时构建管理端与移动端）</p>"
        "</body></html>"
    )
    return Response(body, status=503, mimetype="text/html; charset=utf-8")


def _missing_mobile_ui_message():
    from flask import Response

    body = (
        "<!doctype html><html><head><meta charset=utf-8><title>Mobile UI missing</title></head>"
        "<body style='font-family:system-ui;padding:2rem'>"
        "<h1>移动端前端未构建</h1>"
        "<p>请在项目根目录执行：<code>cd frontend-mobile && npm install && npm run build</code></p>"
        "<p>或使用：<code>python start.py</code></p>"
        "</body></html>"
    )
    return Response(body, status=503, mimetype="text/html; charset=utf-8")
