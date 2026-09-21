# 一键启动全部服务（AI 服务 -> 后端 -> 前端）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1 [-H2]
param(
    [switch]$H2,          # MySQL 不可用时加此参数
    [switch]$SkipFrontend # 只启动服务层
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " 课堂行为智能检测系统 —— 一键启动" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1) AI 服务
& (Join-Path $PSScriptRoot "start-ai.ps1")

# 2) 后端
if ($H2) {
    & (Join-Path $PSScriptRoot "start-backend.ps1") -H2
} else {
    & (Join-Path $PSScriptRoot "start-backend.ps1")
}

# 3) 前端
if (-not $SkipFrontend) {
    & (Join-Path $PSScriptRoot "start-frontend.ps1") -Dev
}

Write-Host ""
Write-Host "全部启动完成：" -ForegroundColor Green
Write-Host "  AI 服务  http://127.0.0.1:5000/health"
Write-Host "  后端     http://127.0.0.1:8080/api/system/status"
Write-Host "  前端     http://127.0.0.1:5173"
