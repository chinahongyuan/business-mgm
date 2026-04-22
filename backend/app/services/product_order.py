"""商品列表排序。

- ``product_list_order``：管理后台列表（上架在前，同状态按创建时间、id 降序）。
- ``mobile_product_list_order_default``：移动端「默认」列表专用规则。
"""

from __future__ import annotations

from sqlalchemy import case

from app.models import Product


def product_list_order():
    status_rank = case((Product.status == "on", 0), else_=1)
    return (
        status_rank.asc(),
        Product.created_at.desc(),
        Product.id.desc(),
    )


def mobile_product_list_order_default():
    """移动端默认：上架在前；上架内按热门/推荐/爆款（flag1/2/3）命中个数降序；同个数按 sort_order 降序；再 created_at、id 降序。下架仅参与状态与后两项。"""
    hit_hot = case((Product.flag1.is_(True), 1), else_=0)
    hit_rec = case((Product.flag2.is_(True), 1), else_=0)
    hit_smash = case((Product.flag3.is_(True), 1), else_=0)
    tag_hits = hit_hot + hit_rec + hit_smash
    on_tag_hits = case((Product.status == "on", tag_hits), else_=0)
    status_rank = case((Product.status == "on", 0), else_=1)
    return (
        status_rank.asc(),
        on_tag_hits.desc(),
        Product.sort_order.desc(),
        Product.created_at.desc(),
        Product.id.desc(),
    )
