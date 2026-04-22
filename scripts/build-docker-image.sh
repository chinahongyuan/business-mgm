#!/bin/bash
# 在项目源代码根目录（含 Dockerfile）生成 Docker 镜像。
# Dockerfile 已默认使用 DaoCloud 基础镜像 + 国内 pip/npm，一般无需额外变量。
#
# 若你能直连 Docker Hub，想用官方 node/python 基础镜像:
#   USE_OFFICIAL_HUB=1 bash scripts/build-docker-image.sh
#
# 环境变量（可选）: IMAGE_NAME, TAG, NO_CACHE=1, COMPOSE_TOO=1, USE_OFFICIAL_HUB=1
# 注意: 勿使用 Windows CRLF 换行；仓库已配置 .gitattributes 强制 *.sh 为 LF。

set -eo pipefail

_SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
if [[ "${_SCRIPT_PATH}" != /* ]]; then
  _SCRIPT_PATH="$(pwd)/${_SCRIPT_PATH}"
fi
SCRIPT_DIR="$(cd "$(dirname "${_SCRIPT_PATH}")" && pwd)"
ROOT="$(cd "${1:-${SCRIPT_DIR}/..}" && pwd)"
cd "$ROOT"

IMAGE_NAME="${IMAGE_NAME:-business-mgm}"
TAG="${TAG:-$(date +%Y%m%d-%H%M%S)}"
NO_CACHE="${NO_CACHE:-0}"
COMPOSE_TOO="${COMPOSE_TOO:-0}"
USE_OFFICIAL_HUB="${USE_OFFICIAL_HUB:-0}"

if [[ ! -f "${ROOT}/Dockerfile" ]]; then
  echo "错误: 未找到 ${ROOT}/Dockerfile，请在本项目根目录执行或传入路径: $0 /path/to/BUSINESS-MGM"
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "错误: 未安装 docker 或不在 PATH 中。"
  exit 1
fi

# DOCKER_BUILDKIT=1 依赖 docker buildx；未安装时会报错，此处自动改用传统构建器
if [[ "${DOCKER_BUILDKIT:-}" == "1" ]] && ! docker buildx version &>/dev/null; then
  echo "==> 未检测到 docker buildx，已取消 DOCKER_BUILDKIT（避免 BuildKit 报错）。无需再手动 unset。"
  unset DOCKER_BUILDKIT
fi

if [[ "${USE_OFFICIAL_HUB}" == "1" ]]; then
  echo "==> 使用 Docker Hub 官方基础镜像（需能访问 registry-1.docker.io）"
  if [[ "${NO_CACHE}" == "1" ]]; then
    docker build --no-cache \
      --build-arg "NODE_IMAGE=node:20-alpine" \
      --build-arg "PYTHON_IMAGE=python:3.12-slim-bookworm" \
      --build-arg "PIP_INDEX_URL=https://pypi.org/simple" \
      --build-arg "NPM_REGISTRY=" \
      -t "${IMAGE_NAME}:${TAG}" -t "${IMAGE_NAME}:latest" \
      -f "${ROOT}/Dockerfile" "${ROOT}"
  else
    docker build \
      --build-arg "NODE_IMAGE=node:20-alpine" \
      --build-arg "PYTHON_IMAGE=python:3.12-slim-bookworm" \
      --build-arg "PIP_INDEX_URL=https://pypi.org/simple" \
      --build-arg "NPM_REGISTRY=" \
      -t "${IMAGE_NAME}:${TAG}" -t "${IMAGE_NAME}:latest" \
      -f "${ROOT}/Dockerfile" "${ROOT}"
  fi
else
  echo "==> 使用默认：DaoCloud 基础镜像 + 清华 PyPI + npmmirror（适合国内网络）"
  if [[ "${NO_CACHE}" == "1" ]]; then
    docker build --no-cache \
      -t "${IMAGE_NAME}:${TAG}" -t "${IMAGE_NAME}:latest" \
      -f "${ROOT}/Dockerfile" "${ROOT}"
  else
    docker build \
      -t "${IMAGE_NAME}:${TAG}" -t "${IMAGE_NAME}:latest" \
      -f "${ROOT}/Dockerfile" "${ROOT}"
  fi
fi

echo "==> 镜像已生成: docker images | grep ${IMAGE_NAME}"

if [[ "${COMPOSE_TOO}" == "1" ]]; then
  if [[ -f "${ROOT}/docker-compose.yml" ]]; then
    echo "==> docker compose build"
    (cd "${ROOT}" && docker compose build)
  else
    echo "跳过: 未找到 docker-compose.yml"
  fi
fi

echo "==> 完成。运行示例:"
echo "    docker run --rm -p 5000:5000 -e DATABASE_URL=... ${IMAGE_NAME}:latest"
echo "    或: cd ${ROOT} && docker compose up -d"
