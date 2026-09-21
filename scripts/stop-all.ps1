# 停止全部服务（按监听端口定位进程，不影响其他程序）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\stop-all.ps1

$ports = @(5000, 8080, 5173, 4173)
foreach ($p in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "停止端口 $p 上的进程：$($proc.ProcessName) (PID=$($proc.Id))"
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
Write-Host "已停止。" -ForegroundColor Green
