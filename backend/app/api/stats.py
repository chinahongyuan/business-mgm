"""统计大屏：活跃度、区域、在线用户、商品关注度（聚合自移动端用户与商品数据）。"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, time
from typing import Any

from flask import jsonify
from sqlalchemy import extract, func

from app.api import bp
from app.auth_utils import require_auth
from app.extensions import db
from app.models import MobileUser, Product, ProductMessage, ProductTag
from app.models.product import mer_product_tag_link
from app.services.mobile_user_identity import mobile_user_distinct_key_expr, subquery_latest_mobile_user_id_per_key
from app.timed_cache import get_or_set

# 统计接口短时缓存（秒）；减轻大屏重复刷新时的 DB 压力。可用环境变量 STATS_CACHE_TTL_SEC 调整。
STATS_CACHE_TTL_SEC = float(os.getenv("STATS_CACHE_TTL_SEC", "60"))


def _region_group_expr():
    trimmed = func.trim(func.coalesce(Product.district, ""))
    return func.coalesce(func.nullif(trimmed, ""), "未填写")


def _ip_region_expr():
    trimmed = func.trim(func.coalesce(MobileUser.ip_region, ""))
    return func.coalesce(func.nullif(trimmed, ""), "未知")


def _user_region_expr():
    trimmed = func.trim(func.coalesce(MobileUser.user_region, ""))
    return func.coalesce(func.nullif(trimmed, ""), "未填写")


def _as_date_key(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def _daily_counts_in_range(
    model: Any,
    col: Any,
    days_ordered: list[date],
) -> list[int]:
    """
    在 [days_ordered[0], days_ordered[-1]] 日历范围内，按 UTC 日期聚合计数，
    与逐日 range 查询语义一致（含首尾整日）。
    """
    if not days_ordered:
        return []
    d0, d1 = days_ordered[0], days_ordered[-1]
    start = datetime.combine(d0, time.min)
    end = datetime.combine(d1 + timedelta(days=1), time.min)

    day_expr = func.date(col)
    rows = (
        db.session.query(day_expr, func.count(model.id))
        .filter(col >= start, col < end)
        .group_by(day_expr)
        .all()
    )
    by_day: dict[date, int] = {}
    for r in rows:
        dk = _as_date_key(r[0])
        if dk is not None:
            by_day[dk] = int(r[1] or 0)
    return [int(by_day.get(d, 0)) for d in days_ordered]


def _daily_distinct_keys_by_last_seen(days_ordered: list[date]) -> list[int]:
    """按自然日统计「有活跃」的去重逻辑访客数（按 IP / vk 去重）。"""
    if not days_ordered:
        return []
    d0, d1 = days_ordered[0], days_ordered[-1]
    start = datetime.combine(d0, time.min)
    end = datetime.combine(d1 + timedelta(days=1), time.min)
    key_expr = mobile_user_distinct_key_expr()
    day_expr = func.date(MobileUser.last_seen_at)
    rows = (
        db.session.query(day_expr, func.count(func.distinct(key_expr)))
        .filter(
            MobileUser.last_seen_at.isnot(None),
            MobileUser.last_seen_at >= start,
            MobileUser.last_seen_at < end,
        )
        .group_by(day_expr)
        .all()
    )
    by_day: dict[date, int] = {}
    for r in rows:
        dk = _as_date_key(r[0])
        if dk is not None:
            by_day[dk] = int(r[1] or 0)
    return [int(by_day.get(d, 0)) for d in days_ordered]


def _daily_new_distinct_keys_by_first_seen(days_ordered: list[date]) -> list[int]:
    """按自然日统计「首次出现」的去重逻辑访客数。"""
    if not days_ordered:
        return []
    d0, d1 = days_ordered[0], days_ordered[-1]
    start = datetime.combine(d0, time.min)
    end = datetime.combine(d1 + timedelta(days=1), time.min)
    key_expr = mobile_user_distinct_key_expr()
    first_sub = (
        db.session.query(
            key_expr.label("k"),
            func.min(MobileUser.created_at).label("first_seen"),
        )
        .group_by(key_expr)
        .subquery()
    )
    rows = (
        db.session.query(func.date(first_sub.c.first_seen), func.count())
        .select_from(first_sub)
        .filter(first_sub.c.first_seen >= start, first_sub.c.first_seen < end)
        .group_by(func.date(first_sub.c.first_seen))
        .all()
    )
    by_day: dict[date, int] = {}
    for r in rows:
        dk = _as_date_key(r[0])
        if dk is not None:
            by_day[dk] = int(r[1] or 0)
    return [int(by_day.get(d, 0)) for d in days_ordered]


ONLINE_MINUTES = 5


def _build_stats_activity_data() -> dict[str, Any]:
    """活跃度：新增用户、日活（按 last_seen 日期）、留言量趋势。移动端用户按 IP（或无 IP 时按 visitorKey/id）去重。"""
    now = datetime.utcnow()
    today = now.date()

    key_expr = mobile_user_distinct_key_expr()
    total_users = int(db.session.query(func.count(func.distinct(key_expr))).scalar() or 0)
    total_messages = int(ProductMessage.query.count() or 0)

    d7 = today - timedelta(days=6)
    d7_start = datetime.combine(d7, time.min)

    first_seen_sub = (
        db.session.query(
            key_expr.label("k"),
            func.min(MobileUser.created_at).label("first_seen"),
        )
        .group_by(key_expr)
        .subquery()
    )
    new_7d = int(
        db.session.query(func.count())
        .select_from(first_seen_sub)
        .filter(first_seen_sub.c.first_seen >= d7_start)
        .scalar()
        or 0
    )
    active_7d = int(
        db.session.query(func.count(func.distinct(key_expr)))
        .filter(MobileUser.last_seen_at >= d7_start)
        .scalar()
        or 0
    )

    days_30 = [today - timedelta(days=i) for i in range(29, -1, -1)]
    labels_30 = [d.strftime("%m-%d") for d in days_30]
    new_users_30 = _daily_new_distinct_keys_by_first_seen(days_30)
    active_users_30 = _daily_distinct_keys_by_last_seen(days_30)
    messages_30 = _daily_counts_in_range(ProductMessage, ProductMessage.created_at, days_30)

    total_visits = db.session.query(func.coalesce(func.sum(MobileUser.visit_count), 0)).scalar()
    distinct_n = int(db.session.query(func.count(func.distinct(key_expr))).scalar() or 0)
    avg_visit_f = round(float(total_visits or 0) / float(distinct_n), 1) if distinct_n else 0.0

    login_sub = (
        db.session.query(
            key_expr.label("k"),
            func.max(MobileUser.last_login_at).label("lst"),
        )
        .filter(MobileUser.last_login_at.isnot(None))
        .group_by(key_expr)
        .subquery()
    )
    hour_expr = extract("hour", login_sub.c.lst)
    hour_rows = db.session.query(hour_expr, func.count()).select_from(login_sub).group_by(hour_expr).all()
    hour_counts: dict[int, int] = {}
    for r in hour_rows:
        h = r[0]
        if h is None:
            continue
        hour_counts[int(h)] = int(r[1] or 0)
    login_hour_labels = [f"{h}时" for h in range(24)]
    login_hour_values = [hour_counts.get(h, 0) for h in range(24)]
    login_hour_meta = {
        "timezoneNote": "UTC",
        "usersWithoutLogin": int(
            db.session.query(func.count(func.distinct(key_expr)))
            .filter(MobileUser.last_login_at.is_(None))
            .scalar()
            or 0
        ),
    }

    return {
        "kpis": [
            {"label": "移动端用户", "value": total_users, "suffix": "人"},
            {"label": "累计留言", "value": total_messages, "suffix": "条"},
            {"label": "近7日新增", "value": new_7d, "suffix": "人"},
            {"label": "近7日活跃", "value": active_7d, "suffix": "人"},
            {"label": "人均访问次数", "value": avg_visit_f, "suffix": "次", "isDecimal": True},
        ],
        "newUsersByDay": {"labels": labels_30, "values": new_users_30},
        "activeUsersByDay": {"labels": labels_30, "values": active_users_30},
        "messagesByDay": {"labels": labels_30, "values": messages_30},
        "loginHourDistribution": {
            "labels": login_hour_labels,
            "values": login_hour_values,
            "meta": login_hour_meta,
        },
    }


@bp.get("/stats/activity")
@require_auth
def stats_activity():
    data = get_or_set("stats:activity:v2", STATS_CACHE_TTL_SEC, _build_stats_activity_data)
    return jsonify({"data": data})


def _build_stats_region_data() -> dict[str, Any]:
    region_expr = _region_group_expr()
    alive = Product.deleted_at.is_(None)
    prod_rows = (
        db.session.query(
            region_expr.label("name"),
            func.count(Product.id).label("cnt"),
        )
        .filter(alive)
        .group_by(region_expr)
        .order_by(func.count(Product.id).desc())
        .limit(14)
        .all()
    )
    product_regions = [{"name": str(r[0]), "value": int(r[1] or 0)} for r in prod_rows]

    latest = subquery_latest_mobile_user_id_per_key()
    ip_expr = _ip_region_expr()
    ip_cnt = func.count().label("cnt")
    ip_rows = (
        db.session.query(ip_expr, ip_cnt)
        .select_from(MobileUser)
        .join(latest, MobileUser.id == latest.c.mid)
        .group_by(ip_expr)
        .order_by(ip_cnt.desc())
        .limit(12)
        .all()
    )
    ip_regions = [{"name": str(r[0]), "value": int(r[1] or 0)} for r in ip_rows]

    ur_expr = _user_region_expr()
    ur_cnt = func.count().label("cnt2")
    ur_rows = (
        db.session.query(ur_expr, ur_cnt)
        .select_from(MobileUser)
        .join(latest, MobileUser.id == latest.c.mid)
        .group_by(ur_expr)
        .order_by(ur_cnt.desc())
        .limit(12)
        .all()
    )
    user_regions = [{"name": str(r[0]), "value": int(r[1] or 0)} for r in ur_rows]

    city_rows = (
        db.session.query(
            Product.city,
            func.count(Product.id).label("cnt"),
        )
        .filter(alive, func.trim(func.coalesce(Product.city, "")) != "")
        .group_by(Product.city)
        .order_by(func.count(Product.id).desc())
        .limit(10)
        .all()
    )
    product_cities = [{"name": str(r[0] or "—"), "value": int(r[1] or 0)} for r in city_rows]

    return {
        "productByDistrict": product_regions,
        "mobileByIpRegion": ip_regions,
        "mobileByUserRegion": user_regions,
        "productByCity": product_cities,
    }


@bp.get("/stats/region")
@require_auth
def stats_region():
    data = get_or_set("stats:region:v2", STATS_CACHE_TTL_SEC, _build_stats_region_data)
    return jsonify({"data": data})


def _build_stats_online_users_data() -> dict[str, Any]:
    now = datetime.utcnow()
    today = now.date()
    window = timedelta(minutes=ONLINE_MINUTES)
    key_expr = mobile_user_distinct_key_expr()

    online_now = int(
        db.session.query(func.count(func.distinct(key_expr)))
        .filter(MobileUser.last_seen_at >= now - window, MobileUser.last_seen_at.isnot(None))
        .scalar()
        or 0
    )
    active_24h = int(
        db.session.query(func.count(func.distinct(key_expr)))
        .filter(MobileUser.last_seen_at >= now - timedelta(hours=24))
        .scalar()
        or 0
    )
    total_mobile_visitors = int(db.session.query(func.count(func.distinct(key_expr))).scalar() or 0)

    latest = subquery_latest_mobile_user_id_per_key()
    normal_cnt = int(
        db.session.query(func.count())
        .select_from(MobileUser)
        .join(latest, MobileUser.id == latest.c.mid)
        .filter(MobileUser.status == "normal")
        .scalar()
        or 0
    )
    disabled_cnt = int(
        db.session.query(func.count())
        .select_from(MobileUser)
        .join(latest, MobileUser.id == latest.c.mid)
        .filter(MobileUser.status == "disabled")
        .scalar()
        or 0
    )

    days_7 = [today - timedelta(days=i) for i in range(6, -1, -1)]
    labels_7 = [d.strftime("%m-%d") for d in days_7]
    dau_7 = _daily_distinct_keys_by_last_seen(days_7)

    return {
        "kpis": [
            {"label": f"当前在线(≈{ONLINE_MINUTES}分钟内)", "value": online_now, "suffix": "人"},
            {"label": "近24小时活跃", "value": active_24h, "suffix": "人"},
            {"label": "用户总数", "value": total_mobile_visitors, "suffix": "人"},
            {"label": "正常账号", "value": normal_cnt, "suffix": "人"},
            {"label": "已禁用", "value": disabled_cnt, "suffix": "人"},
        ],
        "statusPie": [
            {"name": "正常", "value": normal_cnt},
            {"name": "禁用", "value": disabled_cnt},
        ],
        "dauByDay": {"labels": labels_7, "values": dau_7},
    }


@bp.get("/stats/online-users")
@require_auth
def stats_online_users():
    data = get_or_set("stats:online-users:v4", STATS_CACHE_TTL_SEC, _build_stats_online_users_data)
    return jsonify({"data": data})


def _build_stats_product_attention_data() -> dict[str, Any]:
    alive = Product.deleted_at.is_(None)
    total = int(Product.query.filter(alive).count() or 0)
    on_cnt = int(Product.query.filter(alive, Product.status == "on").count() or 0)
    off_cnt = int(Product.query.filter(alive, Product.status == "off").count() or 0)
    hidden_cnt = int(Product.query.filter(alive, Product.flag3.is_(False)).count() or 0)
    visit_sum = int(
        db.session.query(func.coalesce(func.sum(Product.visit_count), 0)).filter(alive).scalar() or 0
    )

    top_rows = Product.query.filter(alive).order_by(Product.visit_count.desc()).limit(15).all()
    top_products = [
        {
            "id": p.id,
            "name": p.name,
            "visitCount": int(p.visit_count or 0),
            "city": p.city or "",
            "district": p.district or "",
            "status": p.status,
        }
        for p in top_rows
    ]

    star_rows = (
        db.session.query(Product.star_rating, func.count(Product.id))
        .filter(alive)
        .group_by(Product.star_rating)
        .order_by(Product.star_rating.asc())
        .all()
    )
    star_dist = [{"name": f"{int(r[0])} 星", "value": int(r[1] or 0)} for r in star_rows]

    tag_rows = (
        db.session.query(ProductTag.name, func.count(mer_product_tag_link.c.product_id).label("cnt"))
        .select_from(ProductTag)
        .join(mer_product_tag_link, ProductTag.id == mer_product_tag_link.c.tag_id)
        .join(Product, Product.id == mer_product_tag_link.c.product_id)
        .filter(alive)
        .group_by(ProductTag.id, ProductTag.name)
        .order_by(func.count(mer_product_tag_link.c.product_id).desc())
        .limit(12)
        .all()
    )
    tag_hot = [{"name": str(r[0]), "value": int(r[1] or 0)} for r in tag_rows]

    return {
        "kpis": [
            {"label": "商品总数", "value": total, "suffix": "件"},
            {"label": "上架中", "value": on_cnt, "suffix": "件"},
            {"label": "已下架", "value": off_cnt, "suffix": "件"},
            {"label": "已隐藏", "value": hidden_cnt, "suffix": "件"},
            {"label": "累计访问量", "value": visit_sum, "suffix": "次"},
        ],
        "shelfPie": [
            {"name": "上架", "value": on_cnt},
            {"name": "下架", "value": off_cnt},
        ],
        "topProducts": top_products,
        "starDistribution": star_dist,
        "tagHot": tag_hot,
    }


@bp.get("/stats/product-attention")
@require_auth
def stats_product_attention():
    data = get_or_set("stats:product-attention:v2", STATS_CACHE_TTL_SEC, _build_stats_product_attention_data)
    return jsonify({"data": data})
