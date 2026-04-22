from __future__ import annotations

from flask import g, jsonify, request

from app.api import bp
from app.auth_utils import create_token, get_client_ip, require_auth
from app.extensions import db
from app.models import AdminUser, LoginLog
from app.services.menu_service import menu_tree_for_user


def _user_agent() -> str | None:
    ua = request.headers.get("User-Agent") or ""
    return ua[:512] if ua else None


@bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"message": "请输入用户名和密码"}), 400

    ip = get_client_ip()
    ua = _user_agent()

    user = AdminUser.query.filter_by(username=username).first()
    if not user:
        db.session.add(
            LoginLog(
                user_id=None,
                username=username,
                ip=ip,
                user_agent=ua,
                success=False,
                message="用户不存在",
            )
        )
        db.session.commit()
        return jsonify({"message": "用户名或密码错误"}), 401

    from app.auth_utils import verify_password

    if not verify_password(password, user.password_hash):
        db.session.add(
            LoginLog(
                user_id=user.id,
                username=username,
                ip=ip,
                user_agent=ua,
                success=False,
                message="密码错误",
            )
        )
        db.session.commit()
        return jsonify({"message": "用户名或密码错误"}), 401

    if not user.is_active:
        db.session.add(
            LoginLog(
                user_id=user.id,
                username=username,
                ip=ip,
                user_agent=ua,
                success=False,
                message="账号已停用",
            )
        )
        db.session.commit()
        return jsonify({"message": "账号已停用"}), 403

    token = create_token(user.id)
    db.session.add(
        LoginLog(
            user_id=user.id,
            username=username,
            ip=ip,
            user_agent=ua,
            success=True,
            message="登录成功",
        )
    )
    db.session.commit()

    menus = menu_tree_for_user(user)
    return jsonify(
        {
            "data": {
                "token": token,
                "user": {"id": user.id, "username": user.username},
                "menus": menus,
            }
        }
    )


@bp.get("/auth/me")
@require_auth
def me():
    user = g.current_user
    menus = menu_tree_for_user(user)
    return jsonify(
        {
            "data": {
                "user": {"id": user.id, "username": user.username},
                "menus": menus,
            }
        }
    )


@bp.post("/auth/logout")
@require_auth
def logout():
    # 无状态 JWT：客户端丢弃 token 即可；此处可记录操作日志
    return jsonify({"data": {"ok": True}})
