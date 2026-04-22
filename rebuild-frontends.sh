#!/usr/bin/env sh
# 将 frontend-admin / frontend-mobile 构建产物写入 backend/app/static/
# （与各 vite.config 中 outDir 一致）。完成后重启 Web 容器即可。
#
# 默认：用 Docker 内的 Node 20 构建（适合 CentOS7 等 glibc 过旧、本机 node 无法运行的宿主机）。
# 本机已有 Node 20+ 时：USE_HOST_NODE=1 ./rebuild-frontends.sh
# 镜像：NODE_IMAGE=docker.m.daocloud.io/library/node:20-bookworm-slim ./rebuild-frontends.sh
# 国内 npm：export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
# 若报 ": No such file or directory"，多为 CRLF：sed -i 's/\r$//' rebuild-frontends.sh
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
NODE_IMAGE="${NODE_IMAGE:-node:20-bookworm-slim}"

docker_build() {
  subdir="$1"
  extra_env=""
  if [ -n "${NPM_CONFIG_REGISTRY:-}" ]; then
    extra_env="-e NPM_CONFIG_REGISTRY=$NPM_CONFIG_REGISTRY"
  fi
  # shellcheck disable=SC2086
  docker run --rm \
    $extra_env \
    -v "$ROOT:/workspace" \
    -w "/workspace/$subdir" \
    "$NODE_IMAGE" \
    bash -c "rm -rf node_modules && npm ci && npm run build"
}

host_build() {
  subdir="$1"
  (cd "$ROOT/$subdir" && npm run build)
}

if [ "${USE_HOST_NODE:-0}" = "1" ]; then
  host_build frontend-admin
  host_build frontend-mobile
else
  docker_build frontend-admin
  docker_build frontend-mobile
fi

echo "Done. Static output: backend/app/static/{admin,mobile}"
echo "Restart: docker compose restart web"
