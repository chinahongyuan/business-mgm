"""进程内短时缓存（TTL），用于统计类只读接口，避免引入 Redis 依赖。"""

from __future__ import annotations

import threading
import time
from typing import Callable, TypeVar

T = TypeVar("T")

_lock = threading.Lock()
_store: dict[str, tuple[float, T]] = {}


def get_or_set(key: str, ttl_seconds: float, factory: Callable[[], T]) -> T:
    """线程安全：命中未过期缓存则直接返回，否则调用 factory 并写入。"""
    now = time.monotonic()
    with _lock:
        hit = _store.get(key)
        if hit is not None:
            ts, val = hit
            if now - ts < ttl_seconds:
                return val
        val = factory()
        _store[key] = (now, val)
        return val


def invalidate_prefix(prefix: str) -> None:
    """可选：数据变更后按前缀清理（如 app_mobile_user 更新时）。"""
    with _lock:
        keys = [k for k in _store if k.startswith(prefix)]
        for k in keys:
            _store.pop(k, None)
