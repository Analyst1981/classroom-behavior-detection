# 构建后端（Maven 打包）+ 构建前端（Vite）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\build.ps1 [-SkipFrontend]
param([switch]$SkipFrontend)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$mvn = "D:\Program Files\apache-maven-3.9.15\bin\mvn.cmd"
if (-not (Test-Path $mvn)) { $mvn = "mvn" }
$env:JAVA_HOME = "D:\Program Files\Java\jdk-25.0.2"

Write-Host "[build] 后端打包..."
& $mvn -f (Join-Path $root "backend\pom.xml") -s (Join-Path $root "mvn\settings.xml") -B package -DskipTests
if ($LASTEXITCODE -ne 0) { throw "后端打包失败" }
Write-Host "[build] 后端完成：backend\target\classroom-backend.jar" -ForegroundColor Green

if (-not $SkipFrontend) {
    Write-Host "[build] 前端构建..."
    Push-Location (Join-Path $root "frontend")
    if (-not (Test-Path "node_modules")) {
        Write-Host "[build] 安装前端依赖..."
        & npm install --registry=https://registry.npmmirror.com --no-audit --no-fund
    }
    & npm run build
    Pop-Location
    if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
    Write-Host "[build] 前端完成：frontend\dist" -ForegroundColor Green
}
