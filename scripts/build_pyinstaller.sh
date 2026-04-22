#!/usr/bin/env bash
# 构建前端 + PyInstaller 打包（Linux/macOS）。输出: backend/dist/business-mgm-server/
# PyInstaller 需在目标系统或同架构容器内执行，不可在 Windows 上打出 Linux 包。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> npm run build (frontend-admin)"
( cd frontend-admin && npm run build )

echo "==> npm run build (frontend-mobile)"
( cd frontend-mobile && npm run build )

test -f backend/app/static/admin/index.html || { echo "缺少 admin index.html"; exit 1; }
test -f backend/app/static/mobile/index.html || { echo "缺少 mobile index.html"; exit 1; }

echo "==> pip install pyinstaller"
cd backend
python3 -m pip install -q -r requirements.txt
python3 -m pip install -q pyinstaller

echo "==> pyinstaller pyinstaller.spec"
python3 -m PyInstaller --noconfirm pyinstaller.spec

echo ""
echo "完成: $ROOT/backend/dist/business-mgm-server/"
echo "运行: ./business-mgm-server  首次建库: ./business-mgm-server init-db"
