# 构建前端 + PyInstaller 打包（Windows）。输出: backend/dist/business-mgm-server/
# 依赖: Node.js、npm、Python 3.11+（与服务器架构一致；PyInstaller 不能跨系统交叉打包）
# 用法: 在项目根目录执行  .\scripts\build_pyinstaller.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> npm run build (frontend-admin)" -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend-admin")
npm run build
Pop-Location

Write-Host "==> npm run build (frontend-mobile)" -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend-mobile")
npm run build
Pop-Location

$adminIndex = Join-Path $Root "backend\app\static\admin\index.html"
$mobileIndex = Join-Path $Root "backend\app\static\mobile\index.html"
if (-not (Test-Path $adminIndex)) { throw "缺少管理端构建产物: $adminIndex" }
if (-not (Test-Path $mobileIndex)) { throw "缺少移动端构建产物: $mobileIndex" }

Write-Host "==> pip install pyinstaller" -ForegroundColor Cyan
Write-Host "（建议在 venv 中仅安装 backend/requirements.txt，可显著加快打包、减小体积）" -ForegroundColor DarkGray
Push-Location (Join-Path $Root "backend")
python -m pip install -q -r requirements.txt
python -m pip install -q pyinstaller

Write-Host "==> pyinstaller pyinstaller.spec" -ForegroundColor Cyan
python -m PyInstaller --noconfirm pyinstaller.spec
Pop-Location

Write-Host ""
Write-Host "完成。将以下目录复制到服务器（保持子目录结构）:" -ForegroundColor Green
Write-Host "  $Root\backend\dist\business-mgm-server\"
Write-Host ""
Write-Host "服务器上在同目录放置 .env（或 config.json），然后运行:" -ForegroundColor Green
Write-Host "  business-mgm-server.exe"
Write-Host "首次建库（可选）: business-mgm-server.exe init-db"
Write-Host "访问: http://服务器IP:端口/  （移动端）  http://服务器IP:端口/system-management （管理后台）"
