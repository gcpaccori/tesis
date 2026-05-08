#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
LOG_DIR="$ROOT/runtime/kimi-k26"

echo "== Procesos Kimi 2.6 =="
pgrep -af "Kimi-K2.6|kimi-k26|vllm.*kimi|download_model.py" || true

echo
echo "== Modelo =="
if [ -d "$MODEL_DIR" ]; then
  du -sh "$MODEL_DIR" || true
  echo "safetensors: $(find "$MODEL_DIR" -name '*.safetensors' 2>/dev/null | wc -l)"
  echo "archivos: $(find "$MODEL_DIR" -type f 2>/dev/null | wc -l)"
else
  echo "No existe $MODEL_DIR"
fi

echo
echo "== Ultimas lineas descarga =="
tail -40 "$LOG_DIR/download.log" 2>/dev/null || echo "Sin log de descarga."

echo
echo "== GPU =="
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true

echo
echo "== RAM =="
free -h || true

echo
echo "== Endpoint vLLM =="
curl -fsS http://127.0.0.1:8098/v1/models 2>/dev/null || echo "vLLM Kimi 2.6 no responde en 127.0.0.1:8098"
echo

