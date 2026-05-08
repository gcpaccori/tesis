#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "--- PROCESOS ---"
ps -eo pid,ppid,etime,%cpu,%mem,cmd \
  | grep -E 'descarga_modelos_v4.py|vllm.entrypoints.openai.api_server|scripts.orquestador_director' \
  | grep -v grep || true

echo
echo "--- GPU ---"
nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu,temperature.gpu \
  --format=csv,noheader,nounits

echo
echo "--- MODELOS ---"
du -sh modelos/* 2>/dev/null | sort -h || true

echo
echo "--- TARGETS V4 ---"
for target in modelos/Mistral-NeMo-12B modelos/Llama-3.2-3B modelos/Qwen-VL-7B; do
  echo "[$target]"
  ls -lah "$target" 2>/dev/null | sed -n '1,20p' || echo "no existe"
  echo
done
