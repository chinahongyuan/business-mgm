"""已有库：创建 cms_bulletin 表（新库 init-db 会随模型创建）。"""

from __future__ import annotations

from sqlalchemy import inspect

from app.extensions import db
from app.models.cms import CmsBulletin


def ensure_cms_bulletin() -> list[str]:
    out: list[str] = []
    insp = inspect(db.engine)
    if insp.has_table("cms_bulletin"):
        out.append("skip: cms_bulletin already exists")
        return out
    CmsBulletin.__table__.create(bind=db.engine)
    out.append("ok: created cms_bulletin")
    return out
