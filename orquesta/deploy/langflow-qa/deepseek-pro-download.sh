#!/usr/bin/env bash
set -euo pipefail

export PATH="/home/u23u/miniconda/envs/orquesta_py311/bin:/home/u23u/orquesta/entorno/vllm_orquesta/bin:/home/u23u/miniconda/bin:/home/u23u/.local/bin:/usr/local/bin:/usr/bin:/bin"
export HF_HOME="/home/u23u/.cache/huggingface"
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_XET=1
export HF_HUB_DOWNLOAD_TIMEOUT=120
export HF_TRANSFER_CONCURRENCY=4

MODEL_DIR="/home/u23u/models/deepseek-v4-pro"
LOG_DIR="/home/u23u/langflow-qa/runtime/logs"
LOG_FILE="${LOG_DIR}/deepseek-v4-pro-download.log"

mkdir -p "${MODEL_DIR}" "${LOG_DIR}"

if pgrep -af "[d]eepseek-v4-pro-download-loop" >/dev/null; then
  echo "La descarga de DeepSeek V4 Pro ya esta corriendo."
  echo "Log: ${LOG_FILE}"
  exit 0
fi

cat > "${LOG_DIR}/deepseek-v4-pro-download-loop.sh" <<'LOOP'
#!/usr/bin/env bash
set -u
export PATH="/home/u23u/miniconda/envs/orquesta_py311/bin:/home/u23u/orquesta/entorno/vllm_orquesta/bin:/home/u23u/miniconda/bin:/home/u23u/.local/bin:/usr/local/bin:/usr/bin:/bin"
export HF_HOME="/home/u23u/.cache/huggingface"
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_XET=1
export HF_HUB_DOWNLOAD_TIMEOUT=120
export HF_TRANSFER_CONCURRENCY=4
MODEL_DIR="/home/u23u/models/deepseek-v4-pro"
while true; do
  shards=$(find "${MODEL_DIR}" -maxdepth 1 -name 'model-*.safetensors' 2>/dev/null | wc -l | awk '{print $1}')
  size=$(du -sh "${MODEL_DIR}" 2>/dev/null | awk '{print $1}')
  echo "[$(date -Is)] DeepSeek V4 Pro shards=${shards}/64 size=${size:-0}"
  if [ "${shards}" = "64" ]; then
    echo "[$(date -Is)] DeepSeek V4 Pro completo."
    exit 0
  fi
  hf download deepseek-ai/DeepSeek-V4-Pro --local-dir "${MODEL_DIR}"
  rc=$?
  echo "[$(date -Is)] hf download rc=${rc}"
  sleep 20
done
LOOP
chmod +x "${LOG_DIR}/deepseek-v4-pro-download-loop.sh"

nohup bash "${LOG_DIR}/deepseek-v4-pro-download-loop.sh" > "${LOG_FILE}" 2>&1 &

echo "Descarga iniciada en background."
echo "Modelo: deepseek-ai/DeepSeek-V4-Pro"
echo "Destino: ${MODEL_DIR}"
echo "Log: ${LOG_FILE}"
echo "PID: $!"
