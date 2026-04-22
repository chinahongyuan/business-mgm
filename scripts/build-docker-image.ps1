# 在项目源代码根目录（含 Dockerfile）生成 Docker 镜像（Windows / PowerShell）。
# Dockerfile 默认使用 DaoCloud 基础镜像；若能直连 Docker Hub: $env:USE_OFFICIAL_HUB = "1"
#
# 用法:
#   cd D:\business-mgm
#   .\scripts\build-docker-image.ps1

param(
    [string] $ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if ($ProjectRoot) {
    $Root = (Resolve-Path $ProjectRoot).Path
} else {
    $Root = Split-Path -Parent $PSScriptRoot
}

Set-Location $Root

if (-not (Test-Path (Join-Path $Root "Dockerfile"))) {
    Write-Error "未找到 Dockerfile: $Root"
}

$imageName = if ($env:IMAGE_NAME) { $env:IMAGE_NAME } else { "business-mgm" }
$tag = if ($env:TAG) { $env:TAG } else { Get-Date -Format "yyyyMMdd-HHmmss" }

$extra = @()
if ($env:USE_OFFICIAL_HUB -eq "1") {
    Write-Host "==> 使用 Docker Hub 官方基础镜像"
    $extra = @(
        "--build-arg", "NODE_IMAGE=node:20-alpine",
        "--build-arg", "PYTHON_IMAGE=python:3.12-slim-bookworm",
        "--build-arg", "PIP_INDEX_URL=https://pypi.org/simple",
        "--build-arg", "NPM_REGISTRY="
    )
} else {
    Write-Host "==> 使用默认：DaoCloud + 清华 PyPI + npmmirror"
}

Write-Host "==> 构建目录: $Root"
Write-Host "==> 镜像: ${imageName}:$tag , ${imageName}:latest"

$df = Join-Path $Root "Dockerfile"
$baseArgs = @("-t", "${imageName}:${tag}", "-t", "${imageName}:latest", "-f", $df) + $extra + @($Root)
if ($env:NO_CACHE -eq "1") {
    & docker build --no-cache @baseArgs
} else {
    & docker build @baseArgs
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> 完成。运行: docker images | Select-String $imageName"

if ($env:COMPOSE_TOO -eq "1" -and (Test-Path (Join-Path $Root "docker-compose.yml"))) {
    docker compose build
}
