from __future__ import annotations

from flask import g, jsonify, request

from app.api import bp
from app.auth_utils import require_auth
from app.extensions import db
from app.models import Menu
from app.services.log_service import write_operation_log
from app.services.menu_service import menu_tree_all, serialize_menu_tree_all


@bp.get("/system/menus")
@require_auth
def list_menus():
    return jsonify({"data": menu_tree_all()})


@bp.post("/system/menus")
@require_auth
def create_menu():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"message": "名称不能为空"}), 400

    parent_id = data.get("parentId")
    if parent_id is not None:
        parent_id = int(parent_id)
        if not db.session.get(Menu, parent_id):
            return jsonify({"message": "父级菜单不存在"}), 400

    path = data.get("path")
    if path is not None:
        path = str(path).strip() or None
    sort_order = int(data.get("sortOrder") or 0)
    icon = (data.get("icon") or "").strip() or None
    is_active = bool(data.get("isActive", True))

    if path:
        exists = Menu.query.filter(Menu.path == path).first()
        if exists:
            return jsonify({"message": "路由路径已存在"}), 400

    m = Menu(
        parent_id=parent_id,
        title=title,
        path=path,
        icon=icon,
        sort_order=sort_order,
        is_active=is_active,
    )
    db.session.add(m)
    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "create",
        "menu",
        str(m.id),
        f"创建菜单 {title}",
    )
    return jsonify({"data": serialize_menu_tree_all(m)})


@bp.put("/system/menus/<int:menu_id>")
@require_auth
def update_menu(menu_id: int):
    m = db.session.get(Menu, menu_id)
    if not m:
        return jsonify({"message": "菜单不存在"}), 404

    data = request.get_json(silent=True) or {}
    if "title" in data:
        t = (data.get("title") or "").strip()
        if not t:
            return jsonify({"message": "名称不能为空"}), 400
        m.title = t

    if "parentId" in data:
        pid = data.get("parentId")
        if pid is None:
            m.parent_id = None
        else:
            pid = int(pid)
            if pid == m.id:
                return jsonify({"message": "不能将父级设为自身"}), 400
            if not db.session.get(Menu, pid):
                return jsonify({"message": "父级菜单不存在"}), 400
            cur = db.session.get(Menu, pid)
            while cur:
                if cur.id == m.id:
                    return jsonify({"message": "不能将父级设为子节点"}), 400
                cur = db.session.get(Menu, cur.parent_id) if cur.parent_id else None
            m.parent_id = pid

    if "path" in data:
        path = data.get("path")
        path = str(path).strip() if path is not None else None
        path = path or None
        if path:
            exists = Menu.query.filter(Menu.path == path, Menu.id != m.id).first()
            if exists:
                return jsonify({"message": "路由路径已存在"}), 400
        m.path = path

    if "icon" in data:
        icon = data.get("icon")
        m.icon = (str(icon).strip() or None) if icon is not None else None

    if "sortOrder" in data:
        m.sort_order = int(data.get("sortOrder") or 0)

    if "isActive" in data:
        m.is_active = bool(data.get("isActive"))

    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "update",
        "menu",
        str(m.id),
        f"更新菜单 {m.title}",
    )
    return jsonify({"data": serialize_menu_tree_all(m)})


@bp.delete("/system/menus/<int:menu_id>")
@require_auth
def delete_menu(menu_id: int):
    m = db.session.get(Menu, menu_id)
    if not m:
        return jsonify({"message": "菜单不存在"}), 404
    if list(m.children):
        return jsonify({"message": "请先删除子菜单"}), 400

    title = m.title
    db.session.delete(m)
    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "delete",
        "menu",
        str(menu_id),
        f"删除菜单 {title}",
    )
    return jsonify({"data": {"ok": True}})
