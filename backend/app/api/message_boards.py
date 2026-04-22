"""管理端：商品留言板（审核、CRUD、一键审核）。"""

from __future__ import annotations

from datetime import datetime

from flask import g, jsonify, request
from sqlalchemy.orm import joinedload
from app.api import bp
from app.auth_utils import require_auth
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import Product, ProductMessage
from app.services.ip2region_service import display_ip_region_only
from app.services.log_service import write_operation_log
from app.services.product_order import product_list_order

ADMIN_REGION_LABEL = "管理后台"


def _parse_dt(val: str | None) -> datetime | None:
    if not val or not str(val).strip():
        return None
    s = str(val).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _message_ip_region_display(m: ProductMessage) -> str:
    if m.created_by_admin:
        return m.ip_region or ADMIN_REGION_LABEL
    mu = m.mobile_user
    if mu is not None:
        return display_ip_region_only(mu.ip, mu.ip_region, mu.user_region)
    return m.ip_region or "未知"


def _serialize_row(m: ProductMessage, include_content_full: bool = False) -> dict:
    p = m.product
    body = {
        "id": m.id,
        "mobileUserId": m.mobile_user_id,
        "ipRegion": _message_ip_region_display(m),
        "productId": m.product_id,
        "productName": p.name if p else "",
        "coverImage": p.cover_image if p else None,
        "auditStatus": m.audit_status,
        "createdByAdmin": m.created_by_admin,
        "createdAt": isoformat_utc(m.created_at),
    }
    if include_content_full:
        body["content"] = m.content or ""
    else:
        body["contentPreview"] = (m.content or "")[:120]
    return body


@bp.get("/message-boards")
@require_auth
def list_message_boards():
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 200)
    audit = (request.args.get("auditStatus") or "").strip()
    start = _parse_dt(request.args.get("startTime"))
    end = _parse_dt(request.args.get("endTime"))
    product_name = (request.args.get("productName") or "").strip()
    ip_region = (request.args.get("ipRegion") or "").strip()

    q = (
        ProductMessage.query.options(joinedload(ProductMessage.mobile_user))
        .join(Product, Product.id == ProductMessage.product_id)
    )
    if audit in ("pending", "approved"):
        q = q.filter(ProductMessage.audit_status == audit)
    if start:
        q = q.filter(ProductMessage.created_at >= start)
    if end:
        q = q.filter(ProductMessage.created_at <= end)
    if product_name:
        q = q.filter(Product.name.contains(product_name))
    if ip_region:
        q = q.filter(ProductMessage.ip_region.contains(ip_region))

    q = q.order_by(ProductMessage.created_at.desc(), ProductMessage.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [_serialize_row(m, include_content_full=False) for m in rows],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )


@bp.get("/message-boards/<int:mid>")
@require_auth
def get_message_board(mid: int):
    m = ProductMessage.query.options(joinedload(ProductMessage.mobile_user)).filter_by(id=mid).first()
    if not m:
        return jsonify({"message": "留言不存在"}), 404
    return jsonify({"data": _serialize_row(m, include_content_full=True)})


@bp.post("/message-boards")
@require_auth
def create_message_board():
    data = request.get_json(silent=True) or {}
    pid = data.get("productId")
    content = (data.get("content") or "").strip()
    if pid is None:
        return jsonify({"message": "请选择商品"}), 400
    if not content:
        return jsonify({"message": "留言内容不能为空"}), 400
    p = db.session.get(Product, int(pid))
    if not p or p.deleted_at is not None:
        return jsonify({"message": "商品不存在"}), 400

    m = ProductMessage(
        mobile_user_id=None,
        ip_region=ADMIN_REGION_LABEL,
        product_id=p.id,
        content=content,
        audit_status="approved",
        created_by_admin=True,
    )
    db.session.add(m)
    db.session.commit()
    db.session.refresh(m)
    write_operation_log(
        g.current_user_id, "create", "message_board", str(m.id), f"管理员新增留言 商品{p.id}"
    )
    return jsonify({"data": _serialize_row(m, include_content_full=True)})


@bp.put("/message-boards/<int:mid>")
@require_auth
def update_message_board(mid: int):
    m = db.session.get(ProductMessage, mid)
    if not m:
        return jsonify({"message": "留言不存在"}), 404
    data = request.get_json(silent=True) or {}
    if "content" in data:
        c = (data.get("content") or "").strip()
        if not c:
            return jsonify({"message": "留言内容不能为空"}), 400
        m.content = c
    if "auditStatus" in data:
        st = (data.get("auditStatus") or "").strip()
        if st not in ("pending", "approved"):
            return jsonify({"message": "审核状态无效"}), 400
        m.audit_status = st
    if "productId" in data:
        pid = data.get("productId")
        p = db.session.get(Product, int(pid))
        if not p or p.deleted_at is not None:
            return jsonify({"message": "商品不存在"}), 400
        m.product_id = p.id

    db.session.commit()
    db.session.refresh(m)
    write_operation_log(g.current_user_id, "update", "message_board", str(m.id), "更新留言")
    return jsonify({"data": _serialize_row(m, include_content_full=True)})


@bp.delete("/message-boards/<int:mid>")
@require_auth
def delete_message_board(mid: int):
    m = db.session.get(ProductMessage, mid)
    if not m:
        return jsonify({"message": "留言不存在"}), 404
    db.session.delete(m)
    db.session.commit()
    write_operation_log(g.current_user_id, "delete", "message_board", str(mid), "删除留言")
    return jsonify({"data": {"ok": True}})


@bp.post("/message-boards/batch-toggle-audit")
@require_auth
def batch_toggle_audit():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "请选择留言"}), 400
    id_list = [int(x) for x in ids]
    rows = ProductMessage.query.filter(ProductMessage.id.in_(id_list)).all()
    for m in rows:
        m.audit_status = "approved" if m.audit_status == "pending" else "pending"
    db.session.commit()
    write_operation_log(
        g.current_user_id,
        "update",
        "message_board",
        ",".join(str(x) for x in id_list),
        f"一键审核切换 {len(rows)} 条",
    )
    return jsonify({"data": {"ok": True, "count": len(rows)}})


@bp.get("/message-boards/products/options")
@require_auth
def product_options_for_messages():
    """新增留言时快捷选择商品（分页简单版）。"""
    kw = (request.args.get("keyword") or "").strip()
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 50), 1), 200)
    q = Product.query.filter(Product.deleted_at.is_(None))
    if kw:
        q = q.filter(Product.name.contains(kw))
    q = q.order_by(*product_list_order())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [
                    {"id": p.id, "name": p.name, "coverImage": p.cover_image} for p in rows
                ],
                "total": total,
            }
        }
    )
