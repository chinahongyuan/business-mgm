"""客户端 IP：可信代理头解析与入库前规范化。

默认不信任 X-Forwarded-For（防直连环境下客户端伪造）。部署在 Nginx/Ingress 后请设置环境变量
TRUST_PROXY_HEADERS=1，此时优先使用 X-Forwarded-For 链中第一个地址，其次 X-Real-IP。
"""

from __future__ import annotations


def normalize_client_ip(ip: str | None) -> str | None:
    if ip is None:
        return None
    s = str(ip).strip()
    if not s:
        return None
    # IPv4:port（常见于误配或部分代理）
    if s.count(":") == 1 and "." in s:
        host, _, maybe_port = s.partition(":")
        if maybe_port.isdigit():
            s = host.strip()
    low = s.lower()
    if low.startswith("::ffff:"):
        s = s[7:]
    if len(s) > 64:
        s = s[:64]
    return s or None


def get_client_ip() -> str | None:
    from flask import current_app, request

    trust = bool(current_app.config.get("TRUST_PROXY_HEADERS", False))
    ip_raw: str | None = None
    if trust:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            ip_raw = xff.split(",")[0].strip()
        if not ip_raw:
            xri = request.headers.get("X-Real-IP")
            if xri:
                ip_raw = xri.strip()
    if not ip_raw:
        ip_raw = request.remote_addr
    return normalize_client_ip(ip_raw)
