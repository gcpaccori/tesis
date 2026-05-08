#!/usr/bin/env bash
set -euo pipefail

cd /home/u23u/langflow-qa

export PATH="/home/u23u/.local/bin:/home/u23u/miniconda/bin:/usr/local/bin:/usr/bin:/bin"

MODEL_DIR="/home/u23u/models/deepseek-v4-pro"
SHARDS=$(find "${MODEL_DIR}" -maxdepth 1 -name 'model-*.safetensors' 2>/dev/null | wc -l | awk '{print $1}')
INCOMPLETE=$(find "${MODEL_DIR}" -maxdepth 4 -type f -name '*.incomplete' 2>/dev/null | wc -l | awk '{print $1}')

if [ "${SHARDS}" != "64" ] || [ "${INCOMPLETE}" != "0" ]; then
  echo "DeepSeek V4 Pro no esta completo: ${SHARDS}/64 shards safetensors, incomplete=${INCOMPLETE}."
  echo "Primero ejecuta: ./deepseek-pro-download.sh"
  exit 2
fi

if command -v numactl >/dev/null 2>&1; then
  numactl --interleave=all podman-compose --profile deepseek-pro up -d deepseek-v4-pro
else
  podman-compose --profile deepseek-pro up -d deepseek-v4-pro
fi

echo "DeepSeek V4 Pro arrancando en http://127.0.0.1:8020/v1"
echo "Logs: podman logs -f qa-deepseek-v4-pro"
