#!/bin/sh
# 生产环境一键清理（由 GET /remove?yes 经 Web 容器拉起 docker:24-cli 执行）。
# 要求：挂载 docker.sock、项目根 /home/management/business-mgm。
set -eu

PROJECT_ROOT="${PROJECT_ROOT:-/home/management/business-mgm}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-business_mgm}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-business-mgm}"
IMAGE_NAME="${IMAGE_NAME:-business-mgm:latest}"
DESTROY_RUNNER_NAME="${DESTROY_RUNNER_NAME:-mgmt-destroy-runner}"
HOST_PARENT="/home/management"
LOG="/tmp/business-mgm-destroy.log"

log() {
  echo "[$(date -Iseconds)] $*" | tee -a "$LOG"
}

if [ -z "${DESTROY_DETACHED:-}" ]; then
  export DESTROY_DETACHED=1
  nohup sh "$0" >>"$LOG" 2>&1 &
  exit 0
fi

log "destroy started PROJECT_ROOT=$PROJECT_ROOT MYSQL_CONTAINER=${MYSQL_CONTAINER:-<skip>} MYSQL_DATABASE=$MYSQL_DATABASE"

if [ ! -d "$PROJECT_ROOT" ]; then
  log "project root missing: $PROJECT_ROOT"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  log "docker CLI not found"
  exit 1
fi

if [ ! -S /var/run/docker.sock ]; then
  log "docker.sock not available"
  exit 1
fi

cd "$PROJECT_ROOT" || exit 1

# 1) 停止本 compose 栈（含 web），并删除匿名卷（勿按 business-mgm 子串过滤，会误删本 runner）
log "docker compose down"
if docker compose version >/dev/null 2>&1; then
  docker compose -f "$PROJECT_ROOT/docker-compose.yml" down -v --remove-orphans 2>>"$LOG" || true
else
  log "docker compose plugin missing, stopping containers by compose label"
  docker ps -aq --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" 2>/dev/null | while read -r cid; do
    [ -n "$cid" ] && docker rm -f "$cid" 2>>"$LOG" || true
  done
fi

# 2) 删除 MySQL 容器及其挂载卷（主机名为容器名时由 Python 传入 MYSQL_CONTAINER）
if [ -n "$MYSQL_CONTAINER" ]; then
  log "remove mysql container: $MYSQL_CONTAINER"
  docker stop "$MYSQL_CONTAINER" 2>>"$LOG" || true
  docker rm -f -v "$MYSQL_CONTAINER" 2>>"$LOG" || true
else
  log "skip mysql container removal (no container name)"
fi

# 3) 删除业务镜像
log "remove image: $IMAGE_NAME"
docker rmi -f "$IMAGE_NAME" 2>>"$LOG" || true

# 4) 删除 compose 创建的 bridge 网络（external mysql 网络不删）
log "remove compose networks"
docker network rm "${COMPOSE_PROJECT}_business_mgm_net" 2>>"$LOG" || true
docker network rm "business_mgm_net" 2>>"$LOG" || true

# 5) 未使用卷 + 构建缓存（影响宿主机全部未使用卷/构建缓存）
log "docker volume prune"
docker volume prune -f 2>>"$LOG" || true
log "docker builder prune"
docker builder prune -af 2>>"$LOG" || true

# 6) 删除整个项目目录（须在 runner 自删之前完成；runner 由 --rm 在退出后自动移除）
log "remove project directory: $PROJECT_ROOT"
if [ -d "$HOST_PARENT" ]; then
  docker run --rm -v "${HOST_PARENT}:${HOST_PARENT}:rw" alpine:3.20 \
    sh -c "rm -rf '${PROJECT_ROOT}'" 2>>"$LOG" || true
fi

log "destroy finished"
