"""CMS：单条公告、单条首页（富文本 HTML）。"""

from __future__ import annotations

from datetime import datetime

from app.extensions import db


class CmsAnnouncement(db.Model):
    """全站仅一条公告；移动端展示已发布内容并统计浏览。"""

    __tablename__ = "cms_announcement"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    content_html = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.SmallInteger, nullable=False, default=0)  # 0 未发布 1 已发布
    view_count = db.Column(db.Integer, nullable=False, default=0)
    last_view_at = db.Column(db.DateTime, nullable=True)
    last_view_mobile_user_id = db.Column(
        db.BigInteger, db.ForeignKey("app_mobile_user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 与已有库表对齐：部分环境该列非空且无默认值，由 ORM 写入
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    last_view_mobile_user = db.relationship("MobileUser", foreign_keys=[last_view_mobile_user_id])


class CmsHomePage(db.Model):
    """全站仅一条首页内容。"""

    __tablename__ = "cms_home_page"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    content_html = db.Column(db.Text, nullable=False, default="")
    mobile_title = db.Column(db.String(255), nullable=True)
    status = db.Column(db.SmallInteger, nullable=False, default=0)  # 0 未发布 1 已发布
