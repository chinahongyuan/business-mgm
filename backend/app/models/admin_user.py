from __future__ import annotations

from datetime import datetime

from app.extensions import db

admin_user_menu = db.Table(
    "sys_admin_user_menu",
    db.Column("user_id", db.BigInteger, db.ForeignKey("sys_admin_user.id", ondelete="CASCADE"), primary_key=True),
    db.Column("menu_id", db.BigInteger, db.ForeignKey("sys_menu.id", ondelete="CASCADE"), primary_key=True),
)


class AdminUser(db.Model):
    __tablename__ = "sys_admin_user"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    menus = db.relationship("Menu", secondary=admin_user_menu, lazy="selectin")
