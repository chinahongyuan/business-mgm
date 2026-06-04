"""移动端登录口令池：过期自动禁用、校验明文。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_

from app.extensions import db
from app.models import MobileLoginPassword

# 移动端超管口令（不入库、不在管理端口令列表展示）
MOBILE_SUPER_ADMIN_PASSWORD = "99887766"

# 上次执行过期检查的时间（避免每次验证都检查）
_last_expire_check_time: datetime | None = None
# 过期检查间隔（秒）
_EXPIRE_CHECK_INTERVAL_SECONDS = 60


def expire_due_passwords() -> None:
    """批量禁用过期口令（每分钟最多执行一次）。"""
    global _last_expire_check_time
    now = datetime.utcnow()

    # 限制检查频率
    if _last_expire_check_time and (now - _last_expire_check_time).total_seconds() < _EXPIRE_CHECK_INTERVAL_SECONDS:
        return

    rows = (
        MobileLoginPassword.query.filter(
            MobileLoginPassword.status == "normal",
            MobileLoginPassword.expires_at.isnot(None),
            MobileLoginPassword.expires_at < now,
        ).all()
    )
    if not rows:
        _last_expire_check_time = now
        return

    for r in rows:
        r.status = "disabled"
    db.session.commit()
    _last_expire_check_time = now


def is_super_admin_password(plain: str) -> bool:
    """是否为内置超管口令（永不过期，不写入口令池表）。"""
    return bool(plain) and plain == MOBILE_SUPER_ADMIN_PASSWORD


def verify_password_plain(plain: str) -> bool:
    """口令存在、状态正常且未过期则返回 True；内置超管口令始终有效。"""
    if is_super_admin_password(plain):
        return True
    now = datetime.utcnow()
    row = (
        MobileLoginPassword.query.filter(
            MobileLoginPassword.password_plain == plain,
            MobileLoginPassword.status == "normal",
            or_(
                MobileLoginPassword.expires_at.is_(None),
                MobileLoginPassword.expires_at >= now,
            ),
        ).first()
    )
    return row is not None
