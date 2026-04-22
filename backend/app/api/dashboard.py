from __future__ import annotations

from datetime import datetime, time

from flask import jsonify
from sqlalchemy import case, func

from app.api import bp
from app.auth_utils import require_auth
from app.extensions import db
from app.models import Product


def _region_group_expr():
    """与商品管理「所属区域」一致：trim 后空值归为「未填写」。"""
    trimmed = func.trim(func.coalesce(Product.district, ""))
    return func.coalesce(func.nullif(trimmed, ""), "未填写")


@bp.get("/dashboard/summary")
@require_auth
def dashboard_summary():
    """工作台：商品经营概览（按区域统计上/下架）。"""
    now = datetime.utcnow()
    today = now.date()

    alive = Product.deleted_at.is_(None)
    total = int(Product.query.filter(alive).count() or 0)
    on_shelf = int(Product.query.filter(alive, Product.status == "on").count() or 0)
    off_shelf = int(Product.query.filter(alive, Product.status == "off").count() or 0)

    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)
    new_today = int(
        Product.query.filter(
            alive, Product.created_at >= today_start, Product.created_at <= today_end
        ).count()
        or 0
    )

    visit_sum_row = db.session.query(func.coalesce(func.sum(Product.visit_count), 0)).filter(alive).scalar()
    visit_sum = int(visit_sum_row or 0)

    region_expr = _region_group_expr()
    on_sum = func.sum(case((Product.status == "on", 1), else_=0))
    off_sum = func.sum(case((Product.status == "off", 1), else_=0))

    rows = (
        db.session.query(
            region_expr.label("region"),
            on_sum.label("on_cnt"),
            off_sum.label("off_cnt"),
        )
        .filter(alive)
        .group_by(region_expr)
        .order_by((on_sum + off_sum).desc())
        .all()
    )

    region_labels = [str(r[0]) for r in rows]
    on_shelf_by_region = [int(r[1] or 0) for r in rows]
    off_shelf_by_region = [int(r[2] or 0) for r in rows]

    return jsonify(
        {
            "data": {
                "kpis": [
                    {"label": "商品总数", "value": total, "suffix": "件"},
                    {"label": "上架中", "value": on_shelf, "suffix": "件"},
                    {"label": "已下架", "value": off_shelf, "suffix": "件"},
                    {"label": "今日新增", "value": new_today, "suffix": "件"},
                    {"label": "累计访问", "value": visit_sum, "suffix": "次"},
                ],
                "regionStats": {
                    "labels": region_labels,
                    "onShelf": on_shelf_by_region,
                    "offShelf": off_shelf_by_region,
                },
            }
        }
    )
