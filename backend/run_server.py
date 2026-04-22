"""
生产环境入口：Waitress + Flask（API + 管理后台 /system-management + 移动端 /）。

PyInstaller 打包时使用本文件作为入口，勿使用 Flask 开发服务器。

用法:
  python run_server.py              # 默认启动 HTTP 服务
  python run_server.py init-db      # 初始化数据库（与 flask init-db 等价）
"""
from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv


def _load_dotenv() -> None:
    if getattr(sys, "frozen", False):
        load_dotenv(os.path.join(os.path.dirname(sys.executable), ".env"))
    else:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(backend_dir, ".env"))
        load_dotenv(os.path.join(os.path.dirname(backend_dir), ".env"))


_load_dotenv()

from app import create_app  # noqa: E402


def _cmd_init_db() -> None:
    from app.extensions import db
    from app.seed import ensure_cms_rows, ensure_product_categories, seed_database

    app = create_app(config_name=os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        db.create_all()
        seed_database()
        ensure_product_categories()
        ensure_cms_rows()
        print("init-db: done")


def _cmd_serve() -> None:
    from waitress import serve

    app = create_app(config_name=os.getenv("FLASK_ENV", "development"))
    host = str(app.config.get("HOST", "0.0.0.0"))
    port = int(app.config.get("PORT", 5000))
    threads = int(os.getenv("WAITRESS_THREADS", "8"))
    print(f"Waitress {host}:{port} threads={threads} FLASK_ENV={os.getenv('FLASK_ENV', 'development')}")
    serve(app, host=host, port=port, threads=threads)


def main() -> None:
    parser = argparse.ArgumentParser(description="business-mgm production server")
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=("serve", "init-db"),
        help="serve: HTTP; init-db: create tables and seed",
    )
    args = parser.parse_args()
    if args.command == "init-db":
        _cmd_init_db()
    else:
        _cmd_serve()


if __name__ == "__main__":
    main()
