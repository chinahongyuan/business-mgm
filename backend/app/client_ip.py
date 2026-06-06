"""客户端 IP：可信代理头解析与入库前规范化。

默认不信任 X-Forwarded-For（防直连环境下客户端伪造）。以下情况会读取代理头：
- 环境变量 TRUST_PROXY_HEADERS=1（Nginx/Ingress 反代部署推荐显式开启）
- remote_addr 为内网/回环（含 Docker 网桥 172.18.0.1）且请求带 X-Forwarded-For 或 X-Real-IP
"""

from __future__ import annotations

import ipaddress


def _is_private_or_loopback(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback


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
    remote = request.remote_addr
    xff = request.headers.get("X-Forwarded-For")
    xri = request.headers.get("X-Real-IP")
    # Docker + Nginx/1Panel：应用看到的对端多为网桥网关，真实 IP 在代理头里
    use_proxy_headers = trust or (
        _is_private_or_loopback(remote) and (xff or xri)
    )

    ip_raw: str | None = None
    if use_proxy_headers:
        if xff:
            ip_raw = xff.split(",")[0].strip()
        if not ip_raw and xri:
            ip_raw = xri.strip()
    if not ip_raw:
        ip_raw = remote
    return normalize_client_ip(ip_raw)
