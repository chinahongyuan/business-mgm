"""P0 统计/列表相关索引：新库随模型 create_all 创建；已有库可执行 `flask ensure-p0-indexes`。"""

from __future__ import annotations

from sqlalchemy import text

from app.extensions import db

# MySQL 8 / MariaDB 10：名称与模型 __table_args__ 一致，便于排查。
P0_DDL_MYSQL = [
    "CREATE INDEX ix_app_mobile_user_created_at ON app_mobile_user (created_at)",
    "CREATE INDEX ix_app_mobile_user_last_seen_at ON app_mobile_user (last_seen_at)",
    "CREATE INDEX ix_app_mobile_user_last_login_at ON app_mobile_user (last_login_at)",
    "CREATE INDEX ix_app_mobile_user_status ON app_mobile_user (status)",
    "CREATE INDEX ix_mer_product_status ON mer_product (status)",
    "CREATE INDEX ix_mer_product_visit_count ON mer_product (visit_count)",
    "CREATE INDEX ix_mer_product_city ON mer_product (city)",
    "CREATE INDEX ix_mer_product_district ON mer_product (district)",
    "CREATE INDEX ix_mer_product_category_id ON mer_product (category_id)",
    "CREATE INDEX ix_mer_product_deleted_at ON mer_product (deleted_at)",
    "CREATE INDEX ix_mer_product_created_at ON mer_product (created_at)",
]


def ensure_p0_indexes() -> list[str]:
    """
    尝试创建缺失索引；已存在则跳过。
    返回已执行或跳过的说明列表（便于 CLI 打印）。
    """
    out: list[str] = []
    for ddl in P0_DDL_MYSQL:
        try:
            db.session.execute(text(ddl))
            db.session.commit()
            out.append(f"ok: {ddl}")
        except Exception as e:  # noqa: BLE001 — 兼容多驱动错误码
            db.session.rollback()
            msg = str(e).lower()
            if "duplicate" in msg or "already exists" in msg or "1061" in msg:
                idx_name = ddl.split()[2] if ddl.upper().startswith("CREATE INDEX ") else ddl
                out.append(f"skip (exists): {idx_name}")
            else:
                raise
    return out
