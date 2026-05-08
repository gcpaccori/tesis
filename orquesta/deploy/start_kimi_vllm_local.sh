#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/u23u/langflow-qa
LOG_DIR=$ROOT/runtime/kimi-vllm-live
mkdir -p "$LOG_DIR"
MODEL_DIR=/home/u23u/models/Kimi-K2.6
VENV=/home/u23u/miniconda/envs/orquesta_py311
PORT=${PORT:-8098}
MODEL_NAME=${MODEL_NAME:-kimi-k2.6-vllm}
MAX_MODEL_LEN=${MAX_MODEL_LEN:-65536}
MAX_BATCHED=${MAX_BATCHED:-32768}
CPU_OFFLOAD_GB=${CPU_OFFLOAD_GB:-48}
GPU_UTIL=${GPU_UTIL:-0.92}
ENFORCE_EAGER=${ENFORCE_EAGER:-1}

if [ ! -x "$VENV/bin/vllm" ]; then
  echo "vLLM no existe en $VENV/bin/vllm" >&2
  exit 2
fi
if [ "$(find "$MODEL_DIR" -name 'model-*.safetensors' | wc -l)" -ne 64 ]; then
  echo "Modelo HF incompleto en $MODEL_DIR" >&2
  exit 3
fi

podman rm -f qa-kimi-q2-gpu >/dev/null 2>&1 || true
pkill -f "vllm serve $MODEL_DIR" >/dev/null 2>&1 || true
sleep 2

cat > "$LOG_DIR/current.env" <<ENV
endpoint=http://127.0.0.1:$PORT/v1
model=$MODEL_NAME
engine=vllm
max_model_len=$MAX_MODEL_LEN
max_num_batched_tokens=$MAX_BATCHED
cpu_offload_gb=$CPU_OFFLOAD_GB
gpu_memory_utilization=$GPU_UTIL
enforce_eager=$ENFORCE_EAGER
ENV

export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export HF_HOME=/home/u23u/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export VLLM_LOGGING_LEVEL=INFO
export CUDA_HOME=${CUDA_HOME:-/home/u23u/cuda-12.6.3}
export PATH="$VENV/bin:$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export NCCL_P2P_DISABLE=${NCCL_P2P_DISABLE:-1}
export NCCL_IB_DISABLE=${NCCL_IB_DISABLE:-1}
export NCCL_SHM_DISABLE=${NCCL_SHM_DISABLE:-0}
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-lo}

nohup "$VENV/bin/vllm" serve "$MODEL_DIR" \
  --served-model-name "$MODEL_NAME" \
  --trust-remote-code \
  --tensor-parallel-size 8 \
  --mm-encoder-tp-mode data \
  --disable-custom-all-reduce \
  --enable-auto-tool-choice \
  --tool-call-parser kimi_k2 \
  --reasoning-parser kimi_k2 \
  --host 0.0.0.0 \
  --port "$PORT" \
  --max-model-len "$MAX_MODEL_LEN" \
  --max-num-batched-tokens "$MAX_BATCHED" \
  --cpu-offload-gb "$CPU_OFFLOAD_GB" \
  --gpu-memory-utilization "$GPU_UTIL" \
  $( [ "$ENFORCE_EAGER" = "1" ] && echo "--enforce-eager" ) \
  > "$LOG_DIR/vllm.log" 2>&1 &

echo $! > "$LOG_DIR/vllm.pid"
echo "vLLM PID $(cat "$LOG_DIR/vllm.pid") puerto $PORT log $LOG_DIR/vllm.log"
