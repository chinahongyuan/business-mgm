"""已有库：创建 app_mobile_visit_log 表（新库 init-db 会随模型创建）。"""

from __future__ import annotations

from sqlalchemy import inspect

from app.extensions import db
from app.models.app_mobile import MobileVisitLog


def ensure_mobile_visit_log() -> list[str]:
    out: list[str] = []
    insp = inspect(db.engine)
    if insp.has_table("app_mobile_visit_log"):
        out.append("skip: app_mobile_visit_log already exists")
        return out
    MobileVisitLog.__table__.create(bind=db.engine)
    out.append("ok: created app_mobile_visit_log")
    return out
