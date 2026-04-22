"""mer_product 软删除列：已有库需执行一次（init-db 新建表会随模型创建）。"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.extensions import db


def ensure_mer_product_deleted_at() -> list[str]:
    """若不存在 deleted_at 列则 ADD COLUMN 并建索引；返回执行说明。"""
    out: list[str] = []
    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("mer_product")}
    if "deleted_at" in cols:
        out.append("skip: mer_product.deleted_at already exists")
        return out
    db.session.execute(text("ALTER TABLE mer_product ADD COLUMN deleted_at DATETIME NULL"))
    db.session.commit()
    out.append("ok: ADD COLUMN mer_product.deleted_at")
    try:
        db.session.execute(text("CREATE INDEX ix_mer_product_deleted_at ON mer_product (deleted_at)"))
        db.session.commit()
        out.append("ok: CREATE INDEX ix_mer_product_deleted_at")
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        msg = str(e).lower()
        if "duplicate" in msg or "already exists" in msg or "1061" in msg:
            out.append("skip: index ix_mer_product_deleted_at exists")
        else:
            raise
    return out
