"""cms_home_page.mobile_title：已有库 ADD COLUMN。"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.extensions import db


def ensure_cms_home_mobile_title() -> list[str]:
    out: list[str] = []
    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("cms_home_page")}
    if "mobile_title" in cols:
        out.append("skip: cms_home_page.mobile_title already exists")
        return out
    db.session.execute(text("ALTER TABLE cms_home_page ADD COLUMN mobile_title VARCHAR(255) NULL"))
    db.session.commit()
    out.append("ok: ADD COLUMN cms_home_page.mobile_title")
    return out
