"""app_mobile_login_password.expires_at 改为可空（永不过期）。"""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.extensions import db


def ensure_app_mobile_login_password_expires_nullable() -> list[str]:
    """SQLite：重建表；其他方言：尽量 MODIFY 为 NULL。"""
    out: list[str] = []
    insp = inspect(db.engine)
    cols = {c["name"]: c for c in insp.get_columns("app_mobile_login_password")}
    if "expires_at" not in cols:
        out.append("skip: table app_mobile_login_password missing expires_at")
        return out
    if cols["expires_at"].get("nullable") is True:
        out.append("skip: expires_at already nullable")
        return out

    dialect = db.engine.dialect.name
    if dialect == "sqlite":
        db.session.execute(
            text(
                """
                CREATE TABLE app_mobile_login_password_new (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    password_plain VARCHAR(512) NOT NULL,
                    status VARCHAR(16) NOT NULL,
                    created_at DATETIME NOT NULL,
                    expires_at DATETIME NULL
                )
                """
            )
        )
        db.session.execute(
            text(
                """
                INSERT INTO app_mobile_login_password_new
                    (id, password_plain, status, created_at, expires_at)
                SELECT id, password_plain, status, created_at, expires_at
                FROM app_mobile_login_password
                """
            )
        )
        db.session.execute(text("DROP TABLE app_mobile_login_password"))
        db.session.execute(
            text("ALTER TABLE app_mobile_login_password_new RENAME TO app_mobile_login_password")
        )
        db.session.commit()
        out.append("ok: sqlite rebuild app_mobile_login_password (expires_at nullable)")
        return out

    # MySQL / MariaDB / PostgreSQL
    try:
        if dialect in ("mysql", "mariadb"):
            db.session.execute(
                text(
                    "ALTER TABLE app_mobile_login_password MODIFY expires_at DATETIME NULL"
                )
            )
        elif dialect == "postgresql":
            db.session.execute(
                text(
                    "ALTER TABLE app_mobile_login_password ALTER COLUMN expires_at DROP NOT NULL"
                )
            )
        else:
            out.append(f"skip: dialect {dialect} not handled; set expires_at nullable manually")
            db.session.rollback()
            return out
        db.session.commit()
        out.append(f"ok: {dialect} expires_at nullable")
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        out.append(f"error: {e}")
        raise
    return out
