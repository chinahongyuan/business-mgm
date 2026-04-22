"""移动端登录口令（多口令池，支持过期自动禁用）。"""

from __future__ import annotations

from datetime import datetime

from app.extensions import db


class MobileLoginPassword(db.Model):
    __tablename__ = "app_mobile_login_password"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    password_plain = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="normal")  # normal | disabled
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
