#!/usr/bin/env bash
set -euo pipefail

export PATH="/home/u23u/.local/bin:/home/u23u/miniconda/bin:/usr/local/bin:/usr/bin:/bin"

echo "== Contenedores QA =="
podman ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | egrep 'qa-|NAMES' || true

echo
echo "== GPUs =="
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits

echo
echo "== Modelo local =="
MODEL_DIR="/home/u23u/models/deepseek-v4-pro"
if [ -d "${MODEL_DIR}" ]; then
  du -sh "${MODEL_DIR}" || true
  find "${MODEL_DIR}" -maxdepth 1 -name 'model-*.safetensors' | wc -l | awk '{print "safetensors shards: "$1"/64"}'
  find "${MODEL_DIR}" -maxdepth 4 -type f \( -name '*.incomplete' -o -name '*.lock' -o -name '*.metadata' \) 2>/dev/null | wc -l | awk '{print "download temp/control files: "$1}'
  find "${MODEL_DIR}" -maxdepth 1 -type f -printf '%f %s\n' 2>/dev/null | sort -V | tail -8
else
  echo "Aun no existe ${MODEL_DIR}"
fi

echo
echo "== Descarga =="
pgrep -af "[d]eepseek-v4-pro-download-loop|[h]f download deepseek-ai/DeepSeek-V4-Pro" || echo "No hay descarga activa."
tail -40 /home/u23u/langflow-qa/runtime/logs/deepseek-v4-pro-download.log 2>/dev/null || true

echo
echo "== Endpoint DeepSeek =="
curl -fsS http://127.0.0.1:8020/v1/models 2>/dev/null || echo "DeepSeek V4 Pro aun no responde en /v1/models"
