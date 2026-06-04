"""生产环境一键清理：由 GET /remove?yes 触发，在宿主机异步执行 scripts/destroy.sh。"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
from typing import Any

from sqlalchemy.engine.url import make_url

from app.json_config import build_database_url, load_raw_config

logger = logging.getLogger(__name__)

PRODUCTION_ROOT = "/home/management/business-mgm"
DESTROY_RUNNER_IMAGE = "docker:24-cli"
# 勿使用 business-mgm 前缀，避免 destroy.sh 按 compose 项目名过滤容器时误删自身
DESTROY_CONTAINER_NAME = "mgmt-destroy-runner"


def production_destroy_armed() -> bool:
    root = (os.getenv("PRODUCTION_DESTROY_ROOT") or "").strip()
    return root == PRODUCTION_ROOT and os.path.isdir(root)


def _database_url_from_app(app: Any) -> str | None:
    uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    if uri:
        return uri
    raw = load_raw_config()
    if raw:
        return build_database_url(raw)
    return (os.getenv("DATABASE_URL") or "").strip() or None


def _is_probable_docker_container_name(host: str) -> bool:
    """连接串主机为容器名时方可 docker stop；host.docker.internal 等跳过。"""
    if not host:
        return False
    lowered = host.lower()
    if lowered in ("localhost", "127.0.0.1", "host.docker.internal"):
        return False
    return "." not in host and "/" not in host


def parse_destroy_targets(app: Any) -> tuple[str | None, str]:
    """从 DATABASE_URL / config.json 解析 MySQL 容器名（主机名）与库名。

    容器名无法解析时返回 (None, database)，脚本将跳过 docker stop mysql。
    """
    uri = _database_url_from_app(app)
    if not uri:
        return "mysql", "business_mgm"
    try:
        u = make_url(uri)
    except Exception:
        logger.exception("parse DATABASE_URL for destroy")
        return "mysql", "business_mgm"
    host = (u.host or "mysql").strip()
    database = (u.database or "business_mgm").strip()
    if not _is_probable_docker_container_name(host):
        logger.warning("destroy: DATABASE host %r is not a container name; skip mysql container removal", host)
        return None, database
    return host, database


def destroy_preflight_error() -> str | None:
    """启动清理前检查；返回错误文案或 None 表示可继续。"""
    if not production_destroy_armed():
        return "未启用生产清理"
    if not os.path.exists("/var/run/docker.sock"):
        return "未挂载 docker.sock"
    if not _docker_bin():
        return "未找到 docker 可执行文件"
    script = os.path.join(PRODUCTION_ROOT, "scripts", "destroy.sh")
    if not os.path.isfile(script):
        return "缺少 scripts/destroy.sh"
    return None


def _docker_bin() -> str | None:
    for candidate in (
        shutil.which("docker"),
        "/usr/bin/docker",
        "/usr/local/bin/docker",
    ):
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def _spawn_destroy_runner(mysql_container: str | None, mysql_database: str) -> None:
    root = PRODUCTION_ROOT
    sock = "/var/run/docker.sock"
    if not os.path.exists(sock):
        logger.error("destroy: docker.sock not mounted at %s", sock)
        return

    docker_bin = _docker_bin()
    if not docker_bin:
        logger.error("destroy: docker CLI not found (mount host /usr/bin/docker)")
        return

    script = os.path.join(root, "scripts", "destroy.sh")
    if not os.path.isfile(script):
        logger.error("destroy: missing script %s", script)
        return

    subprocess.run(
        [docker_bin, "rm", "-f", DESTROY_CONTAINER_NAME],
        capture_output=True,
        timeout=30,
    )

    cmd = [
        docker_bin,
        "run",
        "--rm",
        "-d",
        "--name",
        DESTROY_CONTAINER_NAME,
        "-v",
        f"{sock}:/var/run/docker.sock",
        "-v",
        f"{root}:{root}:rw",
        "-v",
        "/home/management:/home/management:rw",
        "-e",
        f"PROJECT_ROOT={root}",
        "-e",
        f"MYSQL_CONTAINER={mysql_container or ''}",
        "-e",
        f"MYSQL_DATABASE={mysql_database}",
        "-e",
        f"DESTROY_RUNNER_NAME={DESTROY_CONTAINER_NAME}",
        "-e",
        "DESTROY_DETACHED=1",
        DESTROY_RUNNER_IMAGE,
        "sh",
        script,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        logger.error(
            "destroy: failed to start runner (code=%s): %s",
            proc.returncode,
            (proc.stderr or proc.stdout or "").strip(),
        )
        return
    logger.warning(
        "destroy: runner started container=%s mysql=%s db=%s",
        DESTROY_CONTAINER_NAME,
        mysql_container,
        mysql_database,
    )


def schedule_production_destroy(app: Any) -> None:
    mysql_container, mysql_database = parse_destroy_targets(app)
    thread = threading.Thread(
        target=_spawn_destroy_runner,
        args=(mysql_container, mysql_database),
        name="production-destroy",
        daemon=True,
    )
    thread.start()
