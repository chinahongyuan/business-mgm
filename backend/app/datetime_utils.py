"""API 日期时间序列化：库内为 naive UTC，JSON 统一输出带 Z 的 ISO8601，便于前端按 UTC 解析后显示本地时间。"""

from __future__ import annotations

from datetime import datetime, timezone


def isoformat_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    u = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    return u.isoformat().replace("+00:00", "Z")
