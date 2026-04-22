from __future__ import annotations

from flask import g, jsonify, request
from sqlalchemy import func

from app.api import bp
from app.auth_utils import require_auth
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import Product, ProductCategory
from app.services.log_service import write_operation_log


def _serialize(c: ProductCategory) -> dict:
    return {
        "id": c.id,
        "typeCode": c.type_code,
        "name": c.name,
        "createdAt": isoformat_utc(c.created_at),
        "updatedAt": isoformat_utc(c.updated_at),
    }


@bp.get("/merchant/product-categories")
@require_auth
def list_product_categories():
    rows = ProductCategory.query.order_by(ProductCategory.type_code.asc()).all()
    return jsonify({"data": {"items": [_serialize(c) for c in rows]}})


@bp.post("/merchant/product-categories")
@require_auth
def create_product_category():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "名称不能为空"}), 400
    max_code = db.session.query(func.max(ProductCategory.type_code)).scalar()
    next_code = (max_code if max_code is not None else -1) + 1
    c = ProductCategory(type_code=next_code, name=name[:120])
    db.session.add(c)
    db.session.commit()
    db.session.refresh(c)
    write_operation_log(
        g.current_user_id,
        "create",
        "product_category",
        str(c.id),
        f"创建商品分类 {c.name} (type={c.type_code})",
    )
    return jsonify({"data": _serialize(c)})


@bp.delete("/merchant/product-categories/<int:category_id>")
@require_auth
def delete_product_category(category_id: int):
    c = db.session.get(ProductCategory, category_id)
    if not c:
        return jsonify({"message": "分类不存在"}), 404
    linked = Product.query.filter_by(category_id=c.id).filter(Product.deleted_at.is_(None)).count()
    if linked > 0:
        return jsonify({"message": "此分类已有商品，无法删除"}), 400
    name = c.name
    db.session.delete(c)
    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "delete",
        "product_category",
        str(category_id),
        f"删除商品分类 {name}",
    )
    return jsonify({"data": {"ok": True}})


@bp.put("/merchant/product-categories/<int:category_id>")
@require_auth
def update_product_category(category_id: int):
    c = db.session.get(ProductCategory, category_id)
    if not c:
        return jsonify({"message": "分类不存在"}), 404
    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"message": "名称不能为空"}), 400
        c.name = name[:120]
    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "update",
        "product_category",
        str(c.id),
        f"更新商品分类 {c.name}",
    )
    return jsonify({"data": _serialize(c)})
