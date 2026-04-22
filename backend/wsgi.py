"""WSGI entry: single process serves API + built Vue admin static files."""
import os
import sys

from dotenv import load_dotenv

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    load_dotenv(os.path.join(os.path.dirname(sys.executable), ".env"))
else:
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
    load_dotenv(os.path.join(os.path.dirname(_BACKEND_DIR), ".env"))

from app import create_app

app = create_app(
    config_name=os.getenv("FLASK_ENV", "development"),
)

if __name__ == "__main__":
    host = app.config.get("HOST", "0.0.0.0")
    port = int(app.config.get("PORT", 5000))
    debug = bool(app.config.get("DEBUG", os.getenv("FLASK_DEBUG", "1") == "1"))
    
    if debug:
        # 开发模式使用 Flask 内置服务器（支持热重载）
        app.run(host=host, port=port, debug=debug, threaded=True)
    else:
        # 生产模式使用 waitress，大幅提升并发性能
        from waitress import serve
        serve(app, host=host, port=port, threads=8)
