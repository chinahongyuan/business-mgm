from __future__ import annotations

from flask import g, jsonify, request

from app.api import bp
from app.auth_utils import hash_password, require_auth
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import AdminUser, Menu
from app.services.log_service import write_operation_log


def _serialize_user(u: AdminUser) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "isActive": u.is_active,
        "menuIds": [m.id for m in u.menus],
        "createdAt": isoformat_utc(u.created_at),
    }


@bp.get("/system/users")
@require_auth
def list_users():
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 200)
    q = AdminUser.query.order_by(AdminUser.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [_serialize_user(u) for u in rows],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )


@bp.post("/system/users")
@require_auth
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or len(username) < 2:
        return jsonify({"message": "用户名至少 2 个字符"}), 400
    if len(password) < 6:
        return jsonify({"message": "密码至少 6 位"}), 400

    if AdminUser.query.filter_by(username=username).first():
        return jsonify({"message": "用户名已存在"}), 400

    menu_ids = data.get("menuIds") or []
    if not isinstance(menu_ids, list):
        return jsonify({"message": "菜单参数无效"}), 400
    menu_ids = [int(x) for x in menu_ids]
    menus = Menu.query.filter(Menu.id.in_(menu_ids)).all() if menu_ids else []

    u = AdminUser(
        username=username,
        password_hash=hash_password(password),
        is_active=bool(data.get("isActive", True)),
    )
    u.menus = menus
    db.session.add(u)
    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "create",
        "admin_user",
        str(u.id),
        f"创建账号 {username}",
    )
    return jsonify({"data": _serialize_user(u)})


@bp.put("/system/users/<int:user_id>")
@require_auth
def update_user(user_id: int):
    u = db.session.get(AdminUser, user_id)
    if not u:
        return jsonify({"message": "用户不存在"}), 404

    data = request.get_json(silent=True) or {}

    if "username" in data:
        un = (data.get("username") or "").strip()
        if len(un) < 2:
            return jsonify({"message": "用户名至少 2 个字符"}), 400
        exists = AdminUser.query.filter(AdminUser.username == un, AdminUser.id != u.id).first()
        if exists:
            return jsonify({"message": "用户名已存在"}), 400
        u.username = un

    if "password" in data and data.get("password"):
        pwd = data.get("password") or ""
        if len(pwd) < 6:
            return jsonify({"message": "密码至少 6 位"}), 400
        u.password_hash = hash_password(pwd)

    if "isActive" in data:
        u.is_active = bool(data.get("isActive"))

    if "menuIds" in data:
        menu_ids = data.get("menuIds") or []
        if not isinstance(menu_ids, list):
            return jsonify({"message": "菜单参数无效"}), 400
        menu_ids = [int(x) for x in menu_ids]
        u.menus = Menu.query.filter(Menu.id.in_(menu_ids)).all() if menu_ids else []

    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "update",
        "admin_user",
        str(u.id),
        f"更新账号 {u.username}",
    )
    return jsonify({"data": _serialize_user(u)})


@bp.delete("/system/users/<int:user_id>")
@require_auth
def delete_user(user_id: int):
    if user_id == g.current_user_id:
        return jsonify({"message": "不能删除当前登录账号"}), 400
    u = db.session.get(AdminUser, user_id)
    if not u:
        return jsonify({"message": "用户不存在"}), 404
    un = u.username
    db.session.delete(u)
    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "delete",
        "admin_user",
        str(user_id),
        f"删除账号 {un}",
    )
    return jsonify({"data": {"ok": True}})
