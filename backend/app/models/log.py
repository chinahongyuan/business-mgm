from __future__ import annotations

from datetime import datetime

from app.extensions import db


class LoginLog(db.Model):
    __tablename__ = "sys_login_log"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=True, index=True)
    username = db.Column(db.String(64), nullable=False, index=True)
    ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    success = db.Column(db.Boolean, nullable=False, default=False)
    message = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class OperationLog(db.Model):
    __tablename__ = "sys_operation_log"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=True, index=True)
    action = db.Column(db.String(64), nullable=False)
    resource_type = db.Column(db.String(64), nullable=False)
    resource_id = db.Column(db.String(64), nullable=True)
    detail = db.Column(db.Text, nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
