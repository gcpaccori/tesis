#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
MODEL_DIR_REAL="$(readlink -f "$MODEL_DIR")"
MODEL_CONTAINER_DIR="${MODEL_CONTAINER_DIR:-/models/Kimi_K2_6}"
LOG_DIR="$ROOT/runtime/kimi-k26"
OK_FILE="$LOG_DIR/cpu-smoke.ok"
META_OK_FILE="$LOG_DIR/cpu-smoke.metadata.ok"
CONTAINER="${CONTAINER:-qa-kimi-k26-vllm}"
IMAGE="${IMAGE:-docker.io/vllm/vllm-openai:v0.20.0}"
PORT="${PORT:-8098}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
CPU_OFFLOAD_GB="${CPU_OFFLOAD_GB:-48}"
SWAP_SPACE_GB="${SWAP_SPACE_GB:-64}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"

mkdir -p "$LOG_DIR"

if [ ! -f "$OK_FILE" ]; then
  if [ "${ALLOW_CPU_METADATA_ONLY:-0}" = "1" ] && [ -f "$META_OK_FILE" ]; then
    echo "Aviso: full CPU load por Transformers no esta marcado OK; continuando con metadata/tokenizer OK por ALLOW_CPU_METADATA_ONLY=1."
  else
    echo "BLOQUEADO: primero debe pasar kimi-k26-cpu-smoke.sh"
    echo "Falta: $OK_FILE"
    echo "Para Kimi compressed-tensors, puedes permitir metadata/tokenizer con ALLOW_CPU_METADATA_ONLY=1 si el full CPU falla por backend Transformers."
    exit 20
  fi
fi

if [ "$(find "$MODEL_DIR_REAL" -name 'model-*.safetensors' 2>/dev/null | wc -l)" -ne 64 ]; then
  echo "BLOQUEADO: modelo incompleto en $MODEL_DIR_REAL"
  exit 21
fi

podman rm -f "$CONTAINER" >/dev/null 2>&1 || true

echo "Levantando vLLM Kimi 2.6 con 8 GPUs en puerto $PORT."
echo "Nota: si el modelo oficial no cabe en VRAM sin cuantizacion/offload compatible, vLLM fallara con OOM y el log lo dira."

podman run -d --name "$CONTAINER" \
  --security-opt=label=disable \
  --network host \
  --device /dev/nvidia0 --device /dev/nvidia1 --device /dev/nvidia2 --device /dev/nvidia3 \
  --device /dev/nvidia4 --device /dev/nvidia5 --device /dev/nvidia6 --device /dev/nvidia7 \
  -e NVIDIA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
  -e CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
  -e VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 \
  -e HF_HOME=/root/.cache/huggingface \
  -v "$MODEL_DIR_REAL:$MODEL_CONTAINER_DIR:ro" \
  "$IMAGE" \
  --model "$MODEL_CONTAINER_DIR" \
  --served-model-name kimi-k2.6-large-moe \
  --trust-remote-code \
  --tensor-parallel-size 8 \
  --mm-encoder-tp-mode data \
  --tool-call-parser kimi_k2 \
  --reasoning-parser kimi_k2 \
  --host 0.0.0.0 \
  --port "$PORT" \
  --max-model-len "$MAX_MODEL_LEN" \
  --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS" \
  --cpu-offload-gb "$CPU_OFFLOAD_GB" \
  --swap-space "$SWAP_SPACE_GB" \
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
  --disable-log-requests

echo "Container: $CONTAINER"
echo "Logs: podman logs -f $CONTAINER"
echo "Endpoint: http://127.0.0.1:$PORT/v1"
