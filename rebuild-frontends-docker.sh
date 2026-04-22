#!/usr/bin/env sh
# 宿主机无 Node 时使用：用临时 Node 容器执行 npm build，产物仍写入 backend/app/static/
# 用法: ./rebuild-frontends-docker.sh
# 国内可设: export NODE_IMAGE=docker.m.daocloud.io/library/node:20-alpine
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
NODE_IMAGE="${NODE_IMAGE:-node:20-alpine}"

run_npm_build() {
  subdir="$1"
  docker run --rm \
    -v "$ROOT:/workspace" \
    -w "/workspace/$subdir" \
    "$NODE_IMAGE" \
    sh -c "npm ci && npm run build"
}

run_npm_build frontend-admin
run_npm_build frontend-mobile
echo "Done. Static output: backend/app/static/{admin,mobile}"
echo "Restart: docker compose restart web"
