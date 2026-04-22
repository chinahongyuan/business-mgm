from __future__ import annotations

from flask import jsonify, request

from app.api import bp
from app.auth_utils import require_auth
from app.datetime_utils import isoformat_utc
from app.models import LoginLog, OperationLog


@bp.get("/system/login-logs")
@require_auth
def login_logs():
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 200)
    q = LoginLog.query.order_by(LoginLog.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [
                    {
                        "id": r.id,
                        "userId": r.user_id,
                        "username": r.username,
                        "ip": r.ip,
                        "userAgent": r.user_agent,
                        "success": r.success,
                        "message": r.message,
                        "createdAt": isoformat_utc(r.created_at),
                    }
                    for r in rows
                ],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )


@bp.get("/system/operation-logs")
@require_auth
def operation_logs():
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 200)
    q = OperationLog.query.order_by(OperationLog.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [
                    {
                        "id": r.id,
                        "userId": r.user_id,
                        "action": r.action,
                        "resourceType": r.resource_type,
                        "resourceId": r.resource_id,
                        "detail": r.detail,
                        "ip": r.ip,
                        "createdAt": isoformat_utc(r.created_at),
                    }
                    for r in rows
                ],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )
