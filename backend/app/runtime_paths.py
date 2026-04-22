"""Paths for dev vs PyInstaller frozen bundle (static files + writable uploads)."""

from __future__ import annotations

import os
import sys


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) and bool(getattr(sys, "_MEIPASS", None))


def app_package_dir() -> str:
    """Directory of the `app` package (contains static/)."""
    return os.path.dirname(os.path.abspath(__file__))


def backend_root_dir() -> str:
    """Parent of `app/` (backend/ in dev, _internal/ in PyInstaller onedir)."""
    return os.path.dirname(app_package_dir())


def exe_dir() -> str:
    """Folder containing the main executable (frozen) or backend root (dev)."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return backend_root_dir()


def admin_static_dir() -> str:
    return os.path.join(app_package_dir(), "static", "admin")


def mobile_static_dir() -> str:
    return os.path.join(app_package_dir(), "static", "mobile")


def ip2region_xdb_path_v4() -> str:
    """ip2region IPv4 xdb（官方 data/ip2region_v4.xdb）；不存在时由 ip2region_service 尝试下载。"""
    d = os.path.join(backend_root_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "ip2region_v4.xdb")


def ip2region_xdb_path_v6() -> str:
    """ip2region IPv6 xdb（官方 data/ip2region_v6.xdb）；按需下载。"""
    d = os.path.join(backend_root_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "ip2region_v6.xdb")


def uploads_dir() -> str:
    """Writable upload root; must match URL prefix /uploads/."""
    override = (os.getenv("UPLOAD_DIR") or "").strip()
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    if is_frozen():
        d = os.path.join(exe_dir(), "data", "uploads")
        os.makedirs(d, exist_ok=True)
        return d
    d = os.path.join(app_package_dir(), "static", "uploads")
    os.makedirs(d, exist_ok=True)
    return d
