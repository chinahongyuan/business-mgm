"""移动端用户与商品留言板（审核后展示）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index

from app.extensions import db


class MobileUser(db.Model):
    """移动端访客用户（按 visitor_key 识别设备）。"""

    __tablename__ = "app_mobile_user"
    __table_args__ = (
        Index("ix_app_mobile_user_created_at", "created_at"),
        Index("ix_app_mobile_user_last_seen_at", "last_seen_at"),
        Index("ix_app_mobile_user_last_login_at", "last_login_at"),
        Index("ix_app_mobile_user_status", "status"),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    visitor_key = db.Column(db.String(64), unique=True, nullable=True, index=True)
    ip = db.Column(db.String(64), nullable=True)
    ip_region = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(16), nullable=False, default="normal")  # normal | disabled
    user_region = db.Column(db.String(128), nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    visit_count = db.Column(db.Integer, nullable=False, default=0)
    last_product_id = db.Column(db.BigInteger, db.ForeignKey("mer_product.id", ondelete="SET NULL"), nullable=True)
    last_message_id = db.Column(db.BigInteger, nullable=True)
    pwd_fail_count = db.Column(db.Integer, nullable=False, default=0)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    last_product = db.relationship("Product", foreign_keys=[last_product_id])


class MobileVisitLog(db.Model):
    """移动端访问记录（登录、位置上报、商品打开等），供统计与后台串联。"""

    __tablename__ = "app_mobile_visit_log"
    __table_args__ = (Index("ix_app_mobile_visit_log_created_at", "created_at"),)

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    mobile_user_id = db.Column(
        db.BigInteger, db.ForeignKey("app_mobile_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type = db.Column(db.String(32), nullable=False)  # login | geo | product_view
    ip = db.Column(db.String(64), nullable=True)
    latitude = db.Column(db.Numeric(10, 6), nullable=True)
    longitude = db.Column(db.Numeric(10, 6), nullable=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("mer_product.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    mobile_user = db.relationship("MobileUser", backref=db.backref("visit_logs", lazy="dynamic"))


class ProductMessage(db.Model):
    """商品留言；管理员新增可无 mobile_user，ip_region 固定为「管理后台」且默认已通过。"""

    __tablename__ = "app_product_message"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    mobile_user_id = db.Column(
        db.BigInteger, db.ForeignKey("app_mobile_user.id", ondelete="CASCADE"), nullable=True, index=True
    )
    ip_region = db.Column(db.String(128), nullable=False, default="")
    product_id = db.Column(db.BigInteger, db.ForeignKey("mer_product.id", ondelete="CASCADE"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    audit_status = db.Column(db.String(16), nullable=False, default="pending")  # pending | approved
    created_by_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    mobile_user = db.relationship("MobileUser", backref=db.backref("messages", lazy="dynamic"))
    product = db.relationship("Product", backref=db.backref("product_messages", lazy="dynamic"))
