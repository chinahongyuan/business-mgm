from __future__ import annotations

from datetime import datetime

from app.extensions import db


class Menu(db.Model):
    __tablename__ = "sys_menu"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    parent_id = db.Column(db.BigInteger, db.ForeignKey("sys_menu.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    path = db.Column(db.String(255), nullable=True)
    icon = db.Column(db.String(64), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    children = db.relationship(
        "Menu",
        backref=db.backref("parent", remote_side=[id]),
    )
