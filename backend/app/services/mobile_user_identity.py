"""移动端访客去重标识：与统计、后台列表共用同一套逻辑（有 IP 按 IP，否则 vk:+visitor_key/id）。"""

from __future__ import annotations

from sqlalchemy import String, and_, case, cast, func

from app.extensions import db
from app.models import MobileUser


def mobile_user_distinct_key_expr():
    """逻辑访客键：与历史 stats 模块语义一致，供 count(distinct)、group by 使用。"""
    ip_trim = func.trim(func.coalesce(MobileUser.ip, ""))
    return case(
        (and_(MobileUser.ip.isnot(None), ip_trim != ""), ip_trim),
        else_=func.concat(
            "vk:",
            func.coalesce(MobileUser.visitor_key, cast(MobileUser.id, String)),
        ),
    )


def subquery_latest_mobile_user_id_per_key():
    """每个逻辑访客保留 id 最大的一条（通常即最近一条记录）。"""
    k = mobile_user_distinct_key_expr()
    return (
        db.session.query(func.max(MobileUser.id).label("mid"))
        .group_by(k)
        .subquery()
    )
