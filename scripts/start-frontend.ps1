# 启动前端（Vite 开发服务器）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1 [-Dev]
#       默认 -Dev：开发模式（5173，含代理）；去掉 -Dev 则先构建再用 preview 托管
param(
    [switch]$Dev = $true,
    [switch]$Build,
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$feDir = Join-Path $root "frontend"

if (-not (Test-Path (Join-Path $feDir "node_modules"))) {
    throw "未安装前端依赖，请先执行：cd frontend; npm install"
}

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if ($Build) {
    Write-Host "[frontend] 构建生产包..."
    $bout = Join-Path $logDir "frontend-build.log"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"npm run build > `"$bout`" 2>&1`"" `
        -WorkingDirectory $feDir -Wait -WindowStyle Minimized
    Write-Host "[frontend] 构建完成，日志：$bout"
    $port = 4173
    $args = @("/c", "npm run preview -- --port $port")
} else {
    $args = @("/c", "npm run dev -- --port $Port")
}

$out = Join-Path $logDir "frontend.out.log"
$err = Join-Path $logDir "frontend.err.log"
$proc = Start-Process -FilePath "cmd.exe" -ArgumentList $args -WorkingDirectory $feDir `
    -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Minimized

$url = if ($Build) { "http://127.0.0.1:4173" } else { "http://127.0.0.1:$Port" }
Write-Host "[frontend] PID=$($proc.Id)  $url"

for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) {
            Write-Host "[frontend] 已就绪：$url" -ForegroundColor Green
            return
        }
    } catch { }
}
Write-Host "[frontend] 60 秒内未就绪，请查看 $err" -ForegroundColor Yellow
