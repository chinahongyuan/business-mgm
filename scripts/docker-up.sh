#!/bin/bash
# 在项目根目录执行: bash scripts/docker-up.sh
# 首次若无 .env 则从 env.docker.example 复制，再构建并后台启动。
# 脚本须为 LF 换行（见仓库 .gitattributes）。
#
# 需要 Docker Compose：优先使用 `docker compose`（V2 插件），否则 `docker-compose`（独立命令）。
# 若均未安装：CentOS/RHEL 执行 dnf install -y docker-compose-plugin

set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "==> 未找到 .env，从 env.docker.example 复制（请编辑 DATABASE_URL 等）"
  cp env.docker.example .env
fi

mkdir -p data/uploads

run_compose() {
  if docker compose version &>/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose &>/dev/null; then
    docker-compose "$@"
  else
    echo "错误: 未找到「docker compose」或「docker-compose」。"
    echo "请安装 Compose 插件（推荐）:"
    echo "  dnf install -y docker-compose-plugin"
    echo "  或: yum install -y docker-compose-plugin"
    echo "然后重试。验证: docker compose version"
    exit 1
  fi
}

echo "==> docker compose up -d --build"
run_compose up -d --build
echo "==> 完成。日志: docker compose logs -f web   （或 docker-compose logs -f web）"
