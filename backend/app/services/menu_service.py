from __future__ import annotations

from app.models import AdminUser, Menu


def serialize_menu_tree(menu: Menu, allowed_ids: set[int]) -> dict:
    child_menus = [
        c for c in menu.children if c.id in allowed_ids and c.is_active
    ]
    child_menus.sort(key=lambda x: x.sort_order)
    return {
        "id": menu.id,
        "parentId": menu.parent_id,
        "title": menu.title,
        "path": menu.path,
        "icon": menu.icon,
        "sortOrder": menu.sort_order,
        "isActive": menu.is_active,
        "children": [serialize_menu_tree(c, allowed_ids) for c in child_menus],
    }


def menu_tree_for_user(user: AdminUser) -> list[dict]:
    allowed = {m.id for m in user.menus if m.is_active}
    if not allowed:
        return []
    roots: list[Menu] = []
    for m in user.menus:
        if not m.is_active:
            continue
        if m.parent_id is None or m.parent_id not in allowed:
            roots.append(m)
    roots.sort(key=lambda x: x.sort_order)
    return [serialize_menu_tree(m, allowed) for m in roots]


def serialize_menu_tree_all(menu: Menu) -> dict:
    children = sorted(list(menu.children), key=lambda x: x.sort_order)
    return {
        "id": menu.id,
        "parentId": menu.parent_id,
        "title": menu.title,
        "path": menu.path,
        "icon": menu.icon,
        "sortOrder": menu.sort_order,
        "isActive": menu.is_active,
        "children": [serialize_menu_tree_all(c) for c in children],
    }


def menu_tree_all() -> list[dict]:
    roots = Menu.query.filter_by(parent_id=None).order_by(Menu.sort_order).all()
    return [serialize_menu_tree_all(m) for m in roots]
