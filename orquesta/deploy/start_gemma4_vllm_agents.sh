#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/u23u/langflow-qa
LOG_DIR=$ROOT/runtime/gemma4-vllm-live
mkdir -p "$LOG_DIR"

MODEL_ID=${MODEL_ID:-google/gemma-4-26B-A4B-it}
MODEL_DIR=${MODEL_DIR:-/home/u23u/models/Gemma-4-26B-A4B-it}
MODEL_NAME=${MODEL_NAME:-gemma-4-26b-a4b-agents}
VENV=${VENV:-/home/u23u/miniconda/envs/orquesta_py311}
PORT=${PORT:-8098}

# Gemma 4 26B A4B y 31B soportan 256K. El limite real de concurrencia depende
# del KV cache disponible bajo GPU_UTIL. vLLM debe encolar antes de romper VRAM.
MAX_MODEL_LEN=${MAX_MODEL_LEN:-262144}
MAX_NUM_SEQS=${MAX_NUM_SEQS:-6}
MAX_BATCHED=${MAX_BATCHED:-65536}
GPU_UTIL=${GPU_UTIL:-0.65}
TP_SIZE=${TP_SIZE:-8}

if [ ! -x "$VENV/bin/vllm" ]; then
  echo "vLLM no existe en $VENV/bin/vllm" >&2
  exit 2
fi
if [ ! -d "$MODEL_DIR" ]; then
  echo "Modelo no existe en $MODEL_DIR. Ejecuta download_gemma4_agents.sh primero." >&2
  exit 3
fi

podman rm -f qa-kimi-q2-gpu >/dev/null 2>&1 || true
podman rm -f qa-gemma4-vllm >/dev/null 2>&1 || true
pkill -f "vllm serve /home/u23u/models/Kimi-K2.6" >/dev/null 2>&1 || true
pkill -f "vllm serve $MODEL_DIR" >/dev/null 2>&1 || true
sleep 2

cat > "$LOG_DIR/current.env" <<ENV
endpoint=http://127.0.0.1:$PORT/v1
model=$MODEL_NAME
model_id=$MODEL_ID
model_dir=$MODEL_DIR
engine=vllm
tensor_parallel_size=$TP_SIZE
max_model_len=$MAX_MODEL_LEN
max_num_seqs=$MAX_NUM_SEQS
max_num_batched_tokens=$MAX_BATCHED
gpu_memory_utilization=$GPU_UTIL
ENV

export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
export HF_HOME=${HF_HOME:-/home/u23u/.cache/huggingface}
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
export VLLM_LOGGING_LEVEL=${VLLM_LOGGING_LEVEL:-INFO}
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
  --tensor-parallel-size "$TP_SIZE" \
  --mm-encoder-tp-mode data \
  --disable-custom-all-reduce \
  --host 0.0.0.0 \
  --port "$PORT" \
  --max-model-len "$MAX_MODEL_LEN" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  --max-num-batched-tokens "$MAX_BATCHED" \
  --gpu-memory-utilization "$GPU_UTIL" \
  --enforce-eager \
  > "$LOG_DIR/vllm.log" 2>&1 &

echo $! > "$LOG_DIR/vllm.pid"
echo "Gemma vLLM PID $(cat "$LOG_DIR/vllm.pid") puerto $PORT log $LOG_DIR/vllm.log"
