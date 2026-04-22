#!/bin/bash
# 在服务器上检测 Docker 构建相关域名是否可达（超时 10s）。用于排查「拉不到镜像」。
#   bash scripts/docker-network-check.sh
# 脚本须为 LF 换行（见仓库 .gitattributes）。

echo "=== 1) DaoCloud（Dockerfile 默认基础镜像）==="
curl -sI -m 10 "https://docker.m.daocloud.io/v2/" 2>&1 | head -n 5
echo ""
echo "=== 2) Docker Hub（仅在你使用 USE_OFFICIAL_HUB=1 时需要）==="
curl -sI -m 10 "https://registry-1.docker.io/v2/" 2>&1 | head -n 5
echo ""
echo "=== 3) 清华 PyPI（pip 默认）==="
curl -sI -m 10 "https://pypi.tuna.tsinghua.edu.cn/simple/" 2>&1 | head -n 5
echo ""
echo "=== 4) 手动测试拉取 DaoCloud 上的 node ==="
echo "    docker pull docker.m.daocloud.io/library/node:20-alpine"
echo ""
