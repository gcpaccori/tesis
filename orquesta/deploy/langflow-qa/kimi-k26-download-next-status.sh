#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
LOG_DIR="$ROOT/runtime/kimi-k26"
PID_FILE="$LOG_DIR/download-next-shard.pid"

echo "== Conteo shards =="
find "$MODEL_DIR" -maxdepth 1 -name 'model-*.safetensors' | wc -l

echo
echo "== Ultimos shards =="
find "$MODEL_DIR" -maxdepth 1 -name 'model-*.safetensors' | sort | tail -8

echo
echo "== Proceso manual =="
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  ps -fp "$(cat "$PID_FILE")" || true
else
  echo "Sin proceso manual activo."
fi

echo
echo "== Log manual =="
tail -60 "$LOG_DIR/download-next-shard.log" 2>/dev/null || echo "Sin log manual."

