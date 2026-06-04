"""管理端：移动端用户列表、详情、删除、批量启用/禁用。"""

from __future__ import annotations

from datetime import datetime, timedelta

from flask import g, jsonify, request
from sqlalchemy import and_, case, or_

from app.api import bp
from app.auth_utils import require_auth
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import MobileUser, ProductMessage
from app.services.mobile_user_identity import subquery_latest_mobile_user_id_per_key
from app.services.ip2region_service import display_ip_region_only, display_regions_for_user
from app.services.log_service import write_operation_log

ONLINE_WINDOW = timedelta(minutes=5)


def _is_online(u: MobileUser) -> bool:
    if not u.last_seen_at:
        return False
    return datetime.utcnow() - u.last_seen_at < ONLINE_WINDOW


def _serialize_user_list(u: MobileUser) -> dict:
    ip_r, ur = display_regions_for_user(u.ip, u.ip_region, u.user_region)
    return {
        "id": u.id,
        "ip": u.ip,
        "ipRegion": ip_r,
        "status": u.status,
        "userRegion": ur,
        "lastSeenAt": isoformat_utc(u.last_seen_at),
        "isOnline": _is_online(u),
    }


def _serialize_message_short(m: ProductMessage, mobile_user: MobileUser) -> dict:
    ip_disp = display_ip_region_only(mobile_user.ip, mobile_user.ip_region, mobile_user.user_region)
    return {
        "id": m.id,
        "productId": m.product_id,
        "content": m.content or "",
        "auditStatus": m.audit_status,
        "createdAt": isoformat_utc(m.created_at),
        "ipRegion": ip_disp,
    }


def _serialize_user_detail(u: MobileUser) -> dict:
    msgs = (
        ProductMessage.query.filter_by(mobile_user_id=u.id)
        .order_by(ProductMessage.created_at.desc())
        .all()
    )
    ip_r, ur = display_regions_for_user(u.ip, u.ip_region, u.user_region)
    return {
        "id": u.id,
        "visitorKey": u.visitor_key,
        "ip": u.ip,
        "ipRegion": ip_r,
        "status": u.status,
        "userRegion": ur,
        "lastLoginAt": isoformat_utc(u.last_login_at),
        "visitCount": u.visit_count,
        "lastProductId": u.last_product_id,
        "lastMessageId": u.last_message_id,
        "pwdFailCount": u.pwd_fail_count,
        "lastSeenAt": isoformat_utc(u.last_seen_at),
        "isOnline": _is_online(u),
        "createdAt": isoformat_utc(u.created_at),
        "updatedAt": isoformat_utc(u.updated_at),
        "messages": [_serialize_message_short(m, u) for m in msgs],
    }


@bp.get("/app/mobile-users")
@require_auth
def list_mobile_users():
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 200)
    status_f = (request.args.get("status") or "").strip()
    kw = (request.args.get("keyword") or "").strip()
    region = (request.args.get("userRegion") or "").strip()

    latest = subquery_latest_mobile_user_id_per_key()
    q = MobileUser.query.join(latest, MobileUser.id == latest.c.mid)
    if status_f in ("normal", "disabled"):
        q = q.filter(MobileUser.status == status_f)
    if kw:
        q = q.filter(
            or_(
                MobileUser.ip.contains(kw),
                MobileUser.ip_region.contains(kw),
                MobileUser.visitor_key.contains(kw),
            )
        )
    if region:
        q = q.filter(MobileUser.user_region.contains(region))

    # 与 _is_online() 一致：last_seen_at 落在 ONLINE_WINDOW 内视为在线，在线排前
    seen_since = datetime.utcnow() - ONLINE_WINDOW
    online_rank = case(
        (
            and_(
                MobileUser.last_seen_at.isnot(None),
                MobileUser.last_seen_at >= seen_since,
            ),
            0,
        ),
        else_=1,
    )
    q = q.order_by(
        online_rank,
        MobileUser.last_login_at.is_(None),
        MobileUser.last_login_at.desc(),
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [_serialize_user_list(u) for u in rows],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )


@bp.get("/app/mobile-users/<int:uid>")
@require_auth
def get_mobile_user(uid: int):
    u = db.session.get(MobileUser, uid)
    if not u:
        return jsonify({"message": "用户不存在"}), 404
    return jsonify({"data": _serialize_user_detail(u)})


@bp.delete("/app/mobile-users/<int:uid>")
@require_auth
def delete_mobile_user(uid: int):
    u = db.session.get(MobileUser, uid)
    if not u:
        return jsonify({"message": "用户不存在"}), 404
    db.session.delete(u)
    db.session.commit()
    write_operation_log(g.current_user_id, "delete", "mobile_user", str(uid), "删除移动端用户")
    return jsonify({"data": {"ok": True}})


@bp.post("/app/mobile-users/batch-status")
@require_auth
def batch_mobile_user_status():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    status = (data.get("status") or "").strip()
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "请选择用户"}), 400
    if status not in ("normal", "disabled"):
        return jsonify({"message": "状态无效"}), 400
    id_list = [int(x) for x in ids]
    rows = MobileUser.query.filter(MobileUser.id.in_(id_list)).all()
    for u in rows:
        u.status = status
    db.session.commit()
    label = "恢复" if status == "normal" else "禁用"
    write_operation_log(
        g.current_user_id,
        "update",
        "mobile_user",
        ",".join(str(x) for x in id_list),
        f"批量{label} {len(rows)} 人",
    )
    return jsonify({"data": {"ok": True, "count": len(rows)}})
