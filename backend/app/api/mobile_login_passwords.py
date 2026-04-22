"""管理端：移动端登录口令 CRUD、批量状态、一键生成五条随机口令。"""

from __future__ import annotations

import random
import string
from datetime import datetime

from flask import current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.api import bp
from app.auth_utils import require_auth
from app.datetime_utils import isoformat_utc
from app.extensions import db
from app.models import MobileLoginPassword
from app.services.log_service import write_operation_log
from app.services.mobile_password_pool import expire_due_passwords


def _parse_dt(val) -> datetime | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _serialize(p: MobileLoginPassword) -> dict:
    return {
        "id": p.id,
        "passwordPlain": p.password_plain,
        "status": p.status,
        "createdAt": isoformat_utc(p.created_at),
        "expiresAt": isoformat_utc(p.expires_at),
    }


def _random_digits(n: int = 6) -> str:
    return "".join(random.choice(string.digits) for _ in range(n))


@bp.get("/app/mobile-login-passwords")
@require_auth
def list_mobile_login_passwords():
    expire_due_passwords()
    page = max(int(request.args.get("page") or 1), 1)
    page_size = min(max(int(request.args.get("pageSize") or 20), 1), 200)

    q = MobileLoginPassword.query.order_by(MobileLoginPassword.id.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(
        {
            "data": {
                "items": [_serialize(p) for p in rows],
                "total": total,
                "page": page,
                "pageSize": page_size,
            }
        }
    )


@bp.post("/app/mobile-login-passwords")
@require_auth
def create_mobile_login_password():
    data = request.get_json(silent=True) or {}
    plain = (data.get("passwordPlain") or "").strip()
    if not plain:
        return jsonify({"message": "请输入密码内容"}), 400
    if len(plain) > 500:
        return jsonify({"message": "密码过长"}), 400

    now = datetime.utcnow()
    exp = _parse_dt(data.get("expiresAt"))

    try:
        p = MobileLoginPassword(
            password_plain=plain,
            status="normal",
            created_at=now,
            expires_at=exp,
        )
        db.session.add(p)
        db.session.flush()
        write_operation_log(
            g.current_user_id,
            "create",
            "mobile_login_password",
            str(p.id),
            "新增登录口令",
            commit=False,
        )
        db.session.commit()
        return jsonify({"data": _serialize(p)})
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("create mobile_login_password")
        return jsonify({"message": "数据库保存失败，请检查连接后重试"}), 500


@bp.put("/app/mobile-login-passwords/<int:pid>")
@require_auth
def update_mobile_login_password(pid: int):
    p = db.session.get(MobileLoginPassword, pid)
    if not p:
        return jsonify({"message": "记录不存在"}), 404
    expire_due_passwords()

    data = request.get_json(silent=True) or {}
    if "passwordPlain" in data:
        plain = (data.get("passwordPlain") or "").strip()
        if not plain:
            return jsonify({"message": "密码内容不能为空"}), 400
        if len(plain) > 500:
            return jsonify({"message": "密码过长"}), 400
        p.password_plain = plain
    if "status" in data:
        st = (data.get("status") or "").strip()
        if st not in ("normal", "disabled"):
            return jsonify({"message": "状态无效"}), 400
        p.status = st
    if "expiresAt" in data:
        raw = data.get("expiresAt")
        if raw is None or (isinstance(raw, str) and not str(raw).strip()):
            p.expires_at = None
        else:
            exp = _parse_dt(raw)
            if not exp:
                return jsonify({"message": "过期时间无效"}), 400
            p.expires_at = exp

    write_operation_log(
        g.current_user_id,
        "update",
        "mobile_login_password",
        str(pid),
        "修改登录口令",
        commit=False,
    )
    db.session.commit()
    return jsonify({"data": _serialize(p)})


@bp.delete("/app/mobile-login-passwords/<int:pid>")
@require_auth
def delete_mobile_login_password(pid: int):
    p = db.session.get(MobileLoginPassword, pid)
    if not p:
        return jsonify({"message": "记录不存在"}), 404
    rid = str(pid)
    db.session.delete(p)
    write_operation_log(
        g.current_user_id,
        "delete",
        "mobile_login_password",
        rid,
        "删除登录口令",
        commit=False,
    )
    db.session.commit()
    return jsonify({"data": {"ok": True}})


@bp.post("/app/mobile-login-passwords/batch-status")
@require_auth
def batch_mobile_login_password_status():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    status = (data.get("status") or "").strip()
    if not isinstance(ids, list) or not ids:
        return jsonify({"message": "请选择口令"}), 400
    if status not in ("normal", "disabled"):
        return jsonify({"message": "状态无效"}), 400
    expire_due_passwords()
    id_list = [int(x) for x in ids]
    rows = MobileLoginPassword.query.filter(MobileLoginPassword.id.in_(id_list)).all()
    for r in rows:
        r.status = status
    label = "恢复" if status == "normal" else "禁用"
    write_operation_log(
        g.current_user_id,
        "update",
        "mobile_login_password",
        ",".join(str(x) for x in id_list),
        f"批量{label} {len(rows)} 条口令",
        commit=False,
    )
    db.session.commit()
    return jsonify({"data": {"ok": True, "count": len(rows)}})


@bp.post("/app/mobile-login-passwords/batch-generate")
@require_auth
def batch_generate_mobile_login_passwords():
    """一键创建 5 条 6 位随机数字口令，永不过期（expires_at 为空）。"""
    now = datetime.utcnow()
    created = []
    for _ in range(5):
        p = MobileLoginPassword(
            password_plain=_random_digits(6),
            status="normal",
            created_at=now,
            expires_at=None,
        )
        db.session.add(p)
        created.append(p)
    write_operation_log(
        g.current_user_id,
        "create",
        "mobile_login_password",
        "batch",
        "一键创建 5 条随机口令",
        commit=False,
    )
    db.session.commit()
    return jsonify({"data": {"items": [_serialize(p) for p in created]}})
