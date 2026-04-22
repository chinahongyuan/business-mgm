from __future__ import annotations

from flask import request

from app.extensions import db
from app.models import OperationLog


def write_operation_log(
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
    *,
    commit: bool = True,
) -> None:
    ip = None
    if request:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            ip = xff.split(",")[0].strip()[:64]
        else:
            ip = (request.remote_addr or "")[:64] or None
    db.session.add(
        OperationLog(
            user_id=user_id,
            action=action[:64],
            resource_type=resource_type[:64],
            resource_id=(resource_id[:64] if resource_id else None),
            detail=detail,
            ip=ip,
        )
    )
    if commit:
        db.session.commit()
