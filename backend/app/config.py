import os


def validate_pymysql_database_uri(uri: str | None) -> None:
    """PyMySQL 在连接时对密码做 latin-1 编码；非 Latin-1 字符（如中文）会直接导致 UnicodeEncodeError。

    常见误用：复制 env 示例时未替换中文占位密码。应在 MySQL 使用 ASCII 密码，并在
    DATABASE_URL 中对特殊字符做 URL 编码（如 @ → %40）。
    """
    if not uri or "pymysql" not in uri:
        return
    try:
        from sqlalchemy.engine.url import make_url

        u = make_url(uri)
    except Exception:
        return
    pw = u.password
    if not pw:
        return
    try:
        pw.encode("latin-1")
    except UnicodeEncodeError as e:
        raise RuntimeError(
            "数据库密码含有 PyMySQL 无法按 latin-1 编码的字符（例如中文）。"
            "请将 MySQL 用户密码改为仅含英文、数字与常用符号，并更新 DATABASE_URL；"
            "密码中的 @ : / # 等需在 URL 中做百分号编码（如 @ → %40）。"
            "切勿在连接串中保留中文示例密码。"
        ) from e


def _sqlalchemy_engine_options() -> dict:
    """连接池参数可通过环境变量调整；默认值与 SQLAlchemy 常见生产配置一致。"""
    return {
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
        "pool_pre_ping": False,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_timeout": 30,
        "echo": False,
        "echo_pool": False,
    }


# 管理后台 /auth 发放 JWT 的 exp（小时取整）。仅 @require_auth 的接口；移动端 H5 口令会话由
# app.api.mobile_public.MOBILE_PASSWORD_SESSION_TTL 控制，与此无关。
_DEFAULT_ADMIN_JWT_EXPIRES_HOURS = 10 * 365 * 24  # 约 10 年；需短会话可设环境变量或调小 config.json


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    # 反向代理后信任 X-Forwarded-For / X-Real-IP（生产环境 Nginx/Ingress 建议开启）
    TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() in ("1", "true", "yes", "on")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:password@127.0.0.1:3306/business_mgm?charset=utf8mb4",
    )
    SQLALCHEMY_ENGINE_OPTIONS = _sqlalchemy_engine_options()
    SQLALCHEMY_RECORD_QUERIES = False
    JWT_SECRET = os.getenv("JWT_SECRET", "jwt-dev-change-me")
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", str(_DEFAULT_ADMIN_JWT_EXPIRES_HOURS)))
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIG = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}