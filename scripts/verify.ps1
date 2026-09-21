# 端到端验证脚本（Windows PowerShell 5.1+）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
# Linux/macOS/Git Bash 用户请改用 scripts\verify.sh
param(
    [int]$AiPort = 5000,
    [int]$BackendPort = 8080
)

$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot
$ai = 'http://127.0.0.1:' + $AiPort
$be = 'http://127.0.0.1:' + $BackendPort + '/api'
$img = Join-Path $root 'ai-service\demo_data\classroom_01.jpg'
$zip = Join-Path $root 'ai-service\demo_data\classroom_batch.zip'
$video = Join-Path $root 'ai-service\demo_data\classroom_demo.mp4'
$tmp = Join-Path $root 'logs\verify'
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

$passed = 0
$failed = 0

function Write-Result {
    param($Name, $Ok, $Detail)
    if ($Ok) {
        $script:passed = $script:passed + 1
        Write-Host ('  [PASS] ' + $Name + '  ' + $Detail) -ForegroundColor Green
    } else {
        $script:failed = $script:failed + 1
        Write-Host ('  [FAIL] ' + $Name + '  ' + $Detail) -ForegroundColor Red
    }
}

Write-Host '========== 1. AI 服务健康检查 =========='
$h = Invoke-RestMethod ($ai + '/health') -TimeoutSec 10
if ($null -ne $h -and $h.status -eq 'ok') {
    Write-Result 'GET /health' $true ('engine=' + $h.engine)
} else {
    Write-Result 'GET /health' $false 'AI 服务未响应，请先启动 ai-service'
}

Write-Host '========== 2. AI 模型状态 =========='
$m = Invoke-RestMethod ($ai + '/api/model/status') -TimeoutSec 20
if ($null -ne $m -and $null -ne $m.engine) {
    Write-Result '模型状态' $true ('engine=' + $m.engine + ' weights=' + $m.weights)
} else {
    Write-Result '模型状态' $false '未获取到模型状态'
}

Write-Host '========== 3. AI 单图检测 =========='
if (Test-Path $img) {
    $raw = curl.exe -s -F "file=@$img" ($ai + '/api/detect/image')
    $j = $raw | ConvertFrom-Json
    Write-Result '单图检测' ($j.ok -eq $true) ('count=' + $j.count + ' elapsed=' + $j.elapsedMs + 'ms')
} else {
    Write-Result '单图检测' $false ('缺少演示图片 ' + $img)
}

Write-Host '========== 4. AI 批量检测 =========='
if (Test-Path $zip) {
    $raw = curl.exe -s -F "zip=@$zip" ($ai + '/api/detect/batch')
    $j = $raw | ConvertFrom-Json
    Write-Result '批量检测' ($j.ok -eq $true) ('images=' + $j.totalImages + ' detections=' + $j.totalDetections)
} else {
    Write-Result '批量检测' $false '缺少演示压缩包'
}

Write-Host '========== 5. 后端系统状态 =========='
$s = Invoke-RestMethod ($be + '/system/status') -TimeoutSec 20
if ($null -ne $s -and $s.data.backend -eq 'ok') {
    Write-Result '后端状态' $true ('aiOnline=' + $s.data.aiServiceOnline)
} else {
    Write-Result '后端状态' $false '后端未响应，请先启动 backend'
}

Write-Host '========== 6. 经后端做单图检测并落库 =========='
$recordId = $null
if (Test-Path $img) {
    $raw = curl.exe -s -F "file=@$img" ($be + '/detect/image')
    $j = $raw | ConvertFrom-Json
    if ($j.code -eq 0) { $recordId = $j.data.recordId }
    Write-Result '后端单图检测' ($j.code -eq 0 -and $null -ne $recordId) ('recordId=' + $recordId + ' count=' + $j.data.count)
}

Write-Host '========== 7. 记录列表 =========='
$q = '/records?page=0' + [char]38 + 'size=5'
$l = Invoke-RestMethod ($be + $q) -TimeoutSec 20
if ($null -ne $l -and $l.data.total -ge 1) {
    Write-Result '记录列表' $true ('total=' + $l.data.total)
} else {
    Write-Result '记录列表' $false '未查询到记录'
}

Write-Host '========== 8. AI 建议生成 =========='
if ($null -ne $recordId) {
    $payload = ConvertTo-Json @{ provider = 'deepseek' }
    $a = Invoke-RestMethod ($be + '/records/' + $recordId + '/advice') -Method Post -Body $payload -ContentType 'application/json' -TimeoutSec 120
    if ($null -ne $a -and $a.data.advice.Length -gt 10) {
        Write-Result 'AI 建议' $true ('provider=' + $a.data.provider + ' fallback=' + $a.data.fallback + ' len=' + $a.data.advice.Length)
    } else {
        Write-Result 'AI 建议' $false '建议生成失败'
    }
}

Write-Host '========== 9. PDF 报告导出 =========='
if ($null -ne $recordId) {
    $pdf = Join-Path $tmp ('report-' + $recordId + '.pdf')
    curl.exe -s -o $pdf ($be + '/records/' + $recordId + '/report')
    $size = 0
    $head = ''
    if (Test-Path $pdf) {
        $size = (Get-Item $pdf).Length
        $bytes = Get-Content $pdf -Encoding Byte -TotalCount 4
        $head = [System.Text.Encoding]::ASCII.GetString($bytes)
    }
    Write-Result 'PDF 报告' ($size -gt 1000 -and $head -eq '%PDF') ('size=' + $size + ' head=' + $head)
}

Write-Host '========== 10. 视频检测全流程 =========='
if (Test-Path $video) {
    $raw = curl.exe -s -F "file=@$video" ($be + '/detect/video')
    $j = $raw | ConvertFrom-Json
    $taskId = $null
    if ($j.code -eq 0) { $taskId = $j.data.taskId }
    Write-Result '视频任务创建' ($null -ne $taskId) ('taskId=' + $taskId)

    if ($null -ne $taskId) {
        $t = $null
        for ($i = 0; $i -lt 90; $i++) {
            Start-Sleep -Seconds 2
            $t = Invoke-RestMethod ($be + '/detect/task/' + $taskId) -TimeoutSec 20
            if ($t.data.status -eq 'finished') { break }
            if ($t.data.status -eq 'error') { break }
        }
        Write-Result '视频处理完成' ($t.data.status -eq 'finished') ('status=' + $t.data.status + ' frames=' + $t.data.processed + ' output=' + $t.data.outputFile)

        if ($t.data.status -eq 'finished') {
            $sr = Invoke-RestMethod ($be + '/detect/video/' + $taskId + '/save') -Method Post -TimeoutSec 30
            Write-Result '视频记录保存' ($sr.code -eq 0) ('recordId=' + $sr.data.recordId)
        }
    }
} else {
    Write-Result '视频任务创建' $false '缺少演示视频'
}

Write-Host '---'
$summary = '验证结果：通过 ' + $passed + ' 项，失败 ' + $failed + ' 项'
Write-Host $summary
