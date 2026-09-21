# 启动 Spring Boot 后端
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1           # MySQL
#   powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1 -H2       # H2 兜底
param(
    [switch]$H2,
    [int]$Port = 8080,
    [string]$JdbcUrl,
    [string]$DbUser = "root",
    [string]$DbPass = "root"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$jar = Join-Path $root "backend\target\classroom-backend.jar"
if (-not (Test-Path $jar)) { throw "未找到 $jar ，请先执行 scripts\build.ps1" }

$javaExe = "java"
if ($env:JAVA_HOME) { $javaExe = Join-Path $env:JAVA_HOME "bin\java.exe" }
if (-not (Test-Path $javaExe)) { $javaExe = "java" }

$args = @("-jar", $jar, "--server.port=$Port")
if ($H2) {
    $args += "--spring.profiles.active=h2"
    Write-Host "[backend] 使用 H2 文件数据库（MySQL 不可用时的兜底方案）" -ForegroundColor Yellow
} else {
    if ($JdbcUrl) { $args += "--spring.datasource.url=$JdbcUrl" }
    $args += "--spring.datasource.username=$DbUser"
    $args += "--spring.datasource.password=$DbPass"
}

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$out = Join-Path $logDir "backend.out.log"
$err = Join-Path $logDir "backend.err.log"

Write-Host "[backend] 启动中，日志：$out"
$proc = Start-Process -FilePath $javaExe -ArgumentList $args -WorkingDirectory (Join-Path $root "backend") `
    -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Minimized
Write-Host "[backend] PID=$($proc.Id)  http://127.0.0.1:$Port/api/system/status"

for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/system/status" -TimeoutSec 3
        Write-Host "[backend] 健康检查通过：backend=$($r.data.backend), aiOnline=$($r.data.aiServiceOnline)" -ForegroundColor Green
        return
    } catch { }
}
Write-Host "[backend] 90 秒内未就绪，请查看 $err" -ForegroundColor Yellow
