#!/usr/bin/env bash
# 端到端验证脚本（Git Bash / Linux / macOS 可用）
# 用法：bash scripts/verify.sh
# Windows PowerShell 用户请改用 scripts/verify.ps1

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AI="http://127.0.0.1:5000"
BE="http://127.0.0.1:8080/api"
IMG="$ROOT/ai-service/demo_data/classroom_01.jpg"
ZIP="$ROOT/ai-service/demo_data/classroom_batch.zip"
VIDEO="$ROOT/ai-service/demo_data/classroom_demo.mp4"
TMP="$ROOT/logs/verify"
mkdir -p "$TMP"

PASS=0; FAIL=0
# 本机若配置了 HTTP 代理，访问 127.0.0.1 需绕过，否则会被代理拒绝。
# 注意：'*' 必须加引号，否则会被 shell 作通配符展开而破坏参数。
CURL=(curl -s --noproxy '*')

report() { # name ok detail
  if [ "$2" = "true" ]; then PASS=$((PASS+1)); echo "  [PASS] $1  $3";
  else FAIL=$((FAIL+1)); echo "  [FAIL] $1  $3"; fi
}

json_get() { # 从 JSON 文本中提取 key（字符串值去引号）
  echo "$1" | sed -n "s/.*\"$2\":\([^,}]*\).*/\1/p" | head -1 | tr -d '"'
}

echo "========== 1. AI 服务健康检查 =========="
H=$("${CURL[@]}" --max-time 20 "$AI/health")
[ "$(json_get "$H" status)" = "ok" ] && report "GET /health" true "engine=$(json_get "$H" engine)" \
  || report "GET /health" false "$H"

echo "========== 2. AI 模型状态 =========="
M=$("${CURL[@]}" --max-time 30 "$AI/api/model/status")
[ -n "$(json_get "$M" engine)" ] && report "模型状态" true "engine=$(json_get "$M" engine) weights=$(json_get "$M" weights)" \
  || report "模型状态" false "$M"

echo "========== 3. AI 单图检测 =========="
R=$("${CURL[@]}" --max-time 180 -F "file=@$IMG" "$AI/api/detect/image")
[ "$(json_get "$R" ok)" = "true" ] && report "单图检测" true "count=$(json_get "$R" count) elapsed=$(json_get "$R" elapsedMs)ms" \
  || report "单图检测" false "$R"

echo "========== 4. AI 批量检测 =========="
R=$("${CURL[@]}" --max-time 300 -F "zip=@$ZIP" "$AI/api/detect/batch")
[ "$(json_get "$R" ok)" = "true" ] && report "批量检测" true "images=$(json_get "$R" totalImages) detections=$(json_get "$R" totalDetections)" \
  || report "批量检测" false "$R"

echo "========== 5. 后端系统状态 =========="
S=$("${CURL[@]}" --max-time 30 "$BE/system/status")
[ "$(json_get "$S" backend)" = "ok" ] && report "后端状态" true "aiOnline=$(json_get "$S" aiServiceOnline)" \
  || report "后端状态" false "$S"

echo "========== 6. 经后端做单图检测并落库 =========="
RECORD=""
R=$("${CURL[@]}" --max-time 180 -F "file=@$IMG" "$BE/detect/image")
CODE=$(json_get "$R" code)
RECORD=$(echo "$R" | sed -n 's/.*"recordId":\([0-9]*\).*/\1/p' | head -1)
[ "$CODE" = "0" ] && [ -n "$RECORD" ] && report "后端单图检测" true "recordId=$RECORD count=$(json_get "$R" count)" \
  || report "后端单图检测" false "$R"

echo "========== 7. 记录列表 =========="
L=$("${CURL[@]}" --max-time 30 "$BE/records?page=0&size=5")
TOTAL=$(json_get "$L" total)
[ "${TOTAL:-0}" -ge 1 ] 2>/dev/null && report "记录列表" true "total=$TOTAL" || report "记录列表" false "$L"

echo "========== 8. AI 建议生成 =========="
if [ -n "$RECORD" ]; then
  A=$("${CURL[@]}" --max-time 180 -X POST -H "Content-Type: application/json" -d '{"provider":"deepseek"}' "$BE/records/$RECORD/advice")
  ADV=$(json_get "$A" advice)
  [ "${#ADV}" -gt 10 ] && report "AI 建议" true "provider=$(json_get "$A" provider) fallback=$(json_get "$A" fallback) len=${#ADV}" \
    || report "AI 建议" false "$A"
fi

echo "========== 9. PDF 报告导出 =========="
if [ -n "$RECORD" ]; then
  PDF="$TMP/report-$RECORD.pdf"
  "${CURL[@]}" --max-time 120 -o "$PDF" "$BE/records/$RECORD/report"
  SIZE=$(wc -c < "$PDF" 2>/dev/null | tr -d ' ')
  HEAD=$(head -c 4 "$PDF" 2>/dev/null)
  [ "${SIZE:-0}" -gt 1000 ] && [ "$HEAD" = "%PDF" ] && report "PDF 报告" true "size=$SIZE head=$HEAD" \
    || report "PDF 报告" false "size=$SIZE head=$HEAD"
fi

echo "========== 10. 视频检测全流程 =========="
R=$("${CURL[@]}" --max-time 180 -F "file=@$VIDEO" "$BE/detect/video")
TASK=$(echo "$R" | sed -n 's/.*"taskId":"\([^"]*\)".*/\1/p' | head -1)
[ -n "$TASK" ] && report "视频任务创建" true "taskId=$TASK" || report "视频任务创建" false "$R"

if [ -n "$TASK" ]; then
  ST=""
  for i in $(seq 1 90); do
    sleep 2
    T=$("${CURL[@]}" --max-time 20 "$BE/detect/task/$TASK")
    ST=$(json_get "$T" status)
    [ "$ST" = "finished" ] || [ "$ST" = "error" ] && break
  done
  [ "$ST" = "finished" ] && report "视频处理完成" true "status=$ST frames=$(json_get "$T" processed) output=$(json_get "$T" outputFile)" \
    || report "视频处理完成" false "status=$ST"
  if [ "$ST" = "finished" ]; then
    SR=$("${CURL[@]}" --max-time 60 -X POST "$BE/detect/video/$TASK/save")
    [ "$(json_get "$SR" code)" = "0" ] && report "视频记录保存" true "recordId=$(echo "$SR" | sed -n 's/.*"recordId":\([0-9]*\).*/\1/p' | head -1)" \
      || report "视频记录保存" false "$SR"
  fi
fi

echo ""
echo "验证结果：通过 $PASS 项，失败 $FAIL 项"
