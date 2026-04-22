from __future__ import annotations

from flask import g, jsonify, request

from app.api import bp
from app.auth_utils import require_auth
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import ProductTag
from app.services.log_service import write_operation_log


def _serialize(t: ProductTag) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "createdAt": isoformat_utc(t.created_at),
        "updatedAt": isoformat_utc(t.updated_at),
    }


@bp.get("/merchant/tags")
@require_auth
def list_tags():
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 50), 1), 200)
    kw = (request.args.get("keyword") or "").strip()
    q = ProductTag.query
    if kw:
        q = q.filter(ProductTag.name.contains(kw))
    q = q.order_by(ProductTag.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [_serialize(t) for t in rows],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )


@bp.get("/merchant/tags/all")
@require_auth
def list_all_tags():
    rows = ProductTag.query.order_by(ProductTag.id.asc()).all()
    return jsonify({"data": {"items": [_serialize(t) for t in rows]}})


@bp.post("/merchant/tags")
@require_auth
def create_tag():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "名称不能为空"}), 400
    if ProductTag.query.filter_by(name=name).first():
        return jsonify({"message": "标签名称已存在"}), 400
    t = ProductTag(name=name[:120])
    db.session.add(t)
    db.session.commit()
    write_operation_log(g.current_user_id, "create", "product_tag", str(t.id), f"创建标签 {t.name}")
    return jsonify({"data": _serialize(t)})


@bp.put("/merchant/tags/<int:tag_id>")
@require_auth
def update_tag(tag_id: int):
    t = db.session.get(ProductTag, tag_id)
    if not t:
        return jsonify({"message": "标签不存在"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"message": "名称不能为空"}), 400
        exists = ProductTag.query.filter(ProductTag.name == name, ProductTag.id != t.id).first()
        if exists:
            return jsonify({"message": "标签名称已存在"}), 400
        t.name = name[:120]
    db.session.commit()
    write_operation_log(g.current_user_id, "update", "product_tag", str(t.id), f"更新标签 {t.name}")
    return jsonify({"data": _serialize(t)})


@bp.delete("/merchant/tags/<int:tag_id>")
@require_auth
def delete_tag(tag_id: int):
    t = db.session.get(ProductTag, tag_id)
    if not t:
        return jsonify({"message": "标签不存在"}), 404
    name = t.name
    db.session.delete(t)
    db.session.commit()
    write_operation_log(g.current_user_id, "delete", "product_tag", str(tag_id), f"删除标签 {name}")
    return jsonify({"data": {"ok": True}})
