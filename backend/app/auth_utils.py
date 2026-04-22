from __future__ import annotations

import functools
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from flask import g, jsonify, request

from app.extensions import db
from app.models import AdminUser


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _jwt_secret() -> str:
    from flask import current_app

    return current_app.config["JWT_SECRET"]


def create_token(user_id: int) -> str:
    from flask import current_app

    hours = int(current_app.config.get("JWT_EXPIRES_HOURS", 24))
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def get_bearer_token() -> str | None:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def get_client_ip() -> str | None:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()[:64]
    return (request.remote_addr or "")[:64] or None


def require_auth(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return jsonify({"message": "未登录或登录已过期"}), 401
        payload = decode_token(token)
        if not payload or "sub" not in payload:
            return jsonify({"message": "未登录或登录已过期"}), 401
        user_id = int(payload["sub"])
        user = db.session.get(AdminUser, user_id)
        if not user or not user.is_active:
            return jsonify({"message": "账号不可用"}), 401
        g.current_user = user
        g.current_user_id = user_id
        return func(*args, **kwargs)

    return wrapper


def require_auth_optional(func):
    """Attach user if token present; otherwise g.current_user is None."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        g.current_user = None
        g.current_user_id = None
        token = get_bearer_token()
        if token:
            payload = decode_token(token)
            if payload and "sub" in payload:
                user_id = int(payload["sub"])
                user = db.session.get(AdminUser, user_id)
                if user and user.is_active:
                    g.current_user = user
                    g.current_user_id = user_id
        return func(*args, **kwargs)

    return wrapper
