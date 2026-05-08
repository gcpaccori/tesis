#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
LOG_DIR="$ROOT/runtime/kimi-k26"
PID_FILE="$LOG_DIR/sglang.pid"

echo "== SGLang PID =="
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  ps -fp "$(cat "$PID_FILE")" || true
else
  echo "No activo"
fi

echo
echo "== Endpoint =="
curl -fsS http://127.0.0.1:8098/v1/models 2>/dev/null || echo "No responde aun"
echo

echo "== GPU =="
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true

echo
echo "== RAM =="
free -h | sed -n '1,2p' || true

echo
echo "== Log =="
tail -80 "$LOG_DIR/sglang.log" 2>/dev/null || echo "Sin log"

