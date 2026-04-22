"""可选：将执行时间超过阈值的 SQL 打到应用日志（环境变量 SLOW_QUERY_LOG_MS）。"""

from __future__ import annotations

import os
import time

from flask import Flask
from sqlalchemy import event

from app.extensions import db


def register_slow_query_logging(app: Flask) -> None:
    raw = os.getenv("SLOW_QUERY_LOG_MS", "").strip()
    if not raw:
        return
    try:
        threshold_ms = float(raw)
    except ValueError:
        return
    if threshold_ms <= 0:
        return
    threshold_sec = threshold_ms / 1000.0

    with app.app_context():
        engine = db.engine

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        conn.info.setdefault("_bm_qtime_stack", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        stack = conn.info.get("_bm_qtime_stack")
        if not stack:
            return
        t0 = stack.pop()
        elapsed = time.perf_counter() - t0
        if elapsed >= threshold_sec:
            stmt = (statement or "").replace("\n", " ").strip()
            if len(stmt) > 800:
                stmt = stmt[:800] + "…"
            app.logger.warning("slow_query %.0fms: %s", elapsed * 1000, stmt)
