from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index

from app.extensions import db

mer_product_tag_link = db.Table(
    "mer_product_tag_link",
    db.Column("product_id", db.BigInteger, db.ForeignKey("mer_product.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.BigInteger, db.ForeignKey("mer_tag.id", ondelete="CASCADE"), primary_key=True),
)


class ProductCategory(db.Model):
    """商品分类：固定三种 type_code 0/1/2，名称可维护。"""

    __tablename__ = "mer_product_category"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    type_code = db.Column(db.SmallInteger, nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ProductTag(db.Model):
    """商品标签字典。"""

    __tablename__ = "mer_tag"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Product(db.Model):
    __tablename__ = "mer_product"
    __table_args__ = (
        Index("ix_mer_product_status", "status"),
        Index("ix_mer_product_visit_count", "visit_count"),
        Index("ix_mer_product_deleted_at", "deleted_at"),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    cover_image = db.Column(db.String(512), nullable=True)
    category_id = db.Column(db.BigInteger, db.ForeignKey("mer_product_category.id"), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="on")  # on | off
    star_rating = db.Column(db.SmallInteger, nullable=False, default=0)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    province = db.Column(db.String(64), nullable=True)
    city = db.Column(db.String(64), nullable=True)
    district = db.Column(db.String(128), nullable=True)
    longitude = db.Column(db.Numeric(10, 6), nullable=True)
    latitude = db.Column(db.Numeric(10, 6), nullable=True)
    address = db.Column(db.String(512), nullable=True)
    detail_html = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    visit_count = db.Column(db.Integer, nullable=False, default=0)
    flag1 = db.Column(db.Boolean, nullable=False, default=False)
    flag2 = db.Column(db.Boolean, nullable=False, default=False)
    flag3 = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    # 软删除：非空表示已进回收站；列表与移动端仅展示 deleted_at IS NULL
    deleted_at = db.Column(db.DateTime, nullable=True)

    category = db.relationship("ProductCategory", backref="products")
    tags = db.relationship("ProductTag", secondary=mer_product_tag_link, backref="products")
