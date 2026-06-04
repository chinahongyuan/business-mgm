"""管理端：娱乐指南、公告、首页（各仅一条，富文本 HTML）。"""

from __future__ import annotations

from flask import g, jsonify, request

from app.api import bp
from app.auth_utils import require_auth
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import CmsAnnouncement, CmsBulletin, CmsHomePage
from app.services.ip2region_service import display_regions_for_user
from app.schema_cms_home_mobile_title import ensure_cms_home_mobile_title
from app.services.log_service import write_operation_log


def _status_from_client(s: str) -> int:
    return 1 if (s or "").strip() == "published" else 0


def _status_to_client(v: object) -> str:
    """与 DB 驱动返回 int / str（如 '1'）均兼容，避免 (v or 0) == 1 在 v=='1' 时为假。"""
    try:
        iv = int(v) if v is not None else 0
    except (TypeError, ValueError):
        iv = 0
    return "published" if iv == 1 else "draft"


def _get_or_create_announcement() -> CmsAnnouncement:
    """单条娱乐指南：按 id 固定顺序，避免多行时 first() 不确定导致读写到不同行。"""
    row = CmsAnnouncement.query.order_by(CmsAnnouncement.id.asc()).first()
    if not row:
        row = CmsAnnouncement()
        db.session.add(row)
        db.session.commit()
    return row


def _get_or_create_bulletin() -> CmsBulletin:
    """单条公告（cms_bulletin）：与娱乐指南表独立。"""
    row = CmsBulletin.query.order_by(CmsBulletin.id.asc()).first()
    if not row:
        row = CmsBulletin()
        db.session.add(row)
        db.session.commit()
    return row


def _get_or_create_home_page() -> CmsHomePage:
    row = CmsHomePage.query.order_by(CmsHomePage.id.asc()).first()
    if not row:
        row = CmsHomePage()
        db.session.add(row)
        db.session.commit()
    return row


def _serialize_cms_viewable_row(row: CmsAnnouncement | CmsBulletin) -> dict:
    last_ip = None
    region = None
    try:
        u = row.last_view_mobile_user
        if u:
            last_ip = u.ip
            region = display_regions_for_user(u.ip, u.ip_region, u.user_region)[0]
    except Exception:  # noqa: BLE001 — 孤立外键等导致懒加载失败时仍可保存/读取正文与状态
        pass
    return {
        "id": row.id,
        "contentHtml": row.content_html or "",
        "status": _status_to_client(row.status),
        "viewCount": row.view_count or 0,
        "lastViewAt": isoformat_utc(row.last_view_at),
        "lastViewUserId": row.last_view_mobile_user_id,
        "lastViewUserIp": last_ip,
        "lastViewIpRegion": region,
    }


def _serialize_announcement(a: CmsAnnouncement) -> dict:
    return _serialize_cms_viewable_row(a)


def _serialize_bulletin(b: CmsBulletin) -> dict:
    return _serialize_cms_viewable_row(b)


def _serialize_home_page(h: CmsHomePage) -> dict:
    return {
        "id": h.id,
        "contentHtml": h.content_html or "",
        "mobileTitle": (getattr(h, "mobile_title", None) or "").strip(),
        "status": _status_to_client(h.status),
    }


@bp.get("/cms/announcement")
@require_auth
def cms_get_announcement():
    a = _get_or_create_announcement()
    return jsonify({"data": _serialize_announcement(a)})


@bp.put("/cms/announcement")
@require_auth
def cms_put_announcement():
    data = request.get_json(silent=True) or {}
    content_html = data.get("contentHtml")
    if content_html is None:
        return jsonify({"message": "缺少 contentHtml"}), 400
    status = (data.get("status") or "").strip()
    if status not in ("published", "draft"):
        return jsonify({"message": "status 须为 published 或 draft"}), 400

    a = _get_or_create_announcement()
    a.content_html = str(content_html)
    a.status = _status_from_client(status)
    db.session.commit()

    write_operation_log(
        g.current_user_id,
        "update",
        "cms_announcement",
        str(a.id),
        "保存娱乐指南",
    )
    return jsonify({"data": _serialize_announcement(a)})


@bp.get("/cms/bulletin")
@require_auth
def cms_get_bulletin():
    b = _get_or_create_bulletin()
    return jsonify({"data": _serialize_bulletin(b)})


@bp.put("/cms/bulletin")
@require_auth
def cms_put_bulletin():
    data = request.get_json(silent=True) or {}
    content_html = data.get("contentHtml")
    if content_html is None:
        return jsonify({"message": "缺少 contentHtml"}), 400
    status = (data.get("status") or "").strip()
    if status not in ("published", "draft"):
        return jsonify({"message": "status 须为 published 或 draft"}), 400

    b = _get_or_create_bulletin()
    b.content_html = str(content_html)
    b.status = _status_from_client(status)
    db.session.commit()

    write_operation_log(
        g.current_user_id,
        "update",
        "cms_bulletin",
        str(b.id),
        "保存公告",
    )
    return jsonify({"data": _serialize_bulletin(b)})


@bp.get("/cms/home-page")
@require_auth
def cms_get_home_page():
    ensure_cms_home_mobile_title()
    h = _get_or_create_home_page()
    return jsonify({"data": _serialize_home_page(h)})


@bp.put("/cms/home-page")
@require_auth
def cms_put_home_page():
    ensure_cms_home_mobile_title()
    data = request.get_json(silent=True) or {}
    content_html = data.get("contentHtml")
    if content_html is None:
        return jsonify({"message": "缺少 contentHtml"}), 400
    status = (data.get("status") or "").strip()
    if status not in ("published", "draft"):
        return jsonify({"message": "status 须为 published 或 draft"}), 400

    h = _get_or_create_home_page()
    h.content_html = str(content_html)
    h.status = _status_from_client(status)
    if "mobileTitle" in data:
        mt = data.get("mobileTitle")
        h.mobile_title = (str(mt).strip()[:255] if mt is not None else None) or None
    db.session.commit()

    write_operation_log(
        g.current_user_id,
        "update",
        "cms_home_page",
        str(h.id),
        "保存首页内容",
    )
    return jsonify({"data": _serialize_home_page(h)})
