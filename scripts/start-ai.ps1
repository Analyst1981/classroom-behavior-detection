# 启动 AI 推理服务（Flask + PyTorch）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\start-ai.ps1
param(
    [string]$PythonExe = "",
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$aiDir = Join-Path $root "ai-service"

# 解释器选择优先级：显式参数 > 托管 venv > 系统 python
if (-not $PythonExe) {
    $candidates = @(
        "C:\Users\ThinkPad\.workbuddy\binaries\python\envs\default\Scripts\python.exe",
        "D:\Users\ThinkPad\anaconda3\python.exe",
        "python"
    )
    foreach ($c in $candidates) {
        if ($c -eq "python") {
            if (Get-Command python -ErrorAction SilentlyContinue) { $PythonExe = "python"; break }
        } elseif (Test-Path $c) { $PythonExe = $c; break }
    }
}

if (-not $PythonExe) { throw "未找到 Python 解释器，请通过 -PythonExe 指定。"

}
Write-Host "[ai-service] Python: $PythonExe"

# 加载 .env（若存在）
$envFile = Join-Path $aiDir ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $k = $Matches[1].Trim(); $v = $Matches[2].Trim()
            if ($k) { [Environment]::SetEnvironmentVariable($k, $v, "Process") }
        }
    }
    Write-Host "[ai-service] 已加载 .env"
}

$env:CBD_AI_PORT = "$Port"
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$out = Join-Path $logDir "ai-service.out.log"
$err = Join-Path $logDir "ai-service.err.log"

Write-Host "[ai-service] 启动中，日志：$out"
$proc = Start-Process -FilePath $PythonExe -ArgumentList "app.py" -WorkingDirectory $aiDir `
    -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Minimized

Write-Host "[ai-service] PID=$($proc.Id)  http://127.0.0.1:$Port/health"

# 等待就绪
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
        Write-Host "[ai-service] 健康检查通过：engine=$($r.engine)" -ForegroundColor Green
        return
    } catch { }
}
Write-Host "[ai-service] 60 秒内未就绪，请查看 $err" -ForegroundColor Yellow
