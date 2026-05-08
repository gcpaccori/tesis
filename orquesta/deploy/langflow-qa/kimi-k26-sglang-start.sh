#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi_K2_6}"
MODEL_DIR_REAL="$(readlink -f "$MODEL_DIR")"
VENV="${VENV:-$ROOT/venvs/kimi-sglang}"
CUDA_HOME_LOCAL="${CUDA_HOME_LOCAL:-/home/u23u/cuda-12.6.3}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8098}"
TP="${TP:-8}"
CPU_THREADS="${CPU_THREADS:-200}"
THREADPOOLS="${THREADPOOLS:-4}"
GPU_EXPERTS="${GPU_EXPERTS:-30}"
MAX_TOTAL_TOKENS="${MAX_TOTAL_TOKENS:-8192}"
CHUNKED_PREFILL_SIZE="${CHUNKED_PREFILL_SIZE:-8192}"
CPU_OFFLOAD_GB="${CPU_OFFLOAD_GB:-64}"
MEM_FRACTION_STATIC="${MEM_FRACTION_STATIC:-0.82}"
DISABLE_CUDA_GRAPH="${DISABLE_CUDA_GRAPH:-1}"
ENABLE_REASONING_PARSER="${ENABLE_REASONING_PARSER:-0}"
LOG_DIR="$ROOT/runtime/kimi-k26"
LOG_FILE="$LOG_DIR/sglang.log"
PID_FILE="$LOG_DIR/sglang.pid"

mkdir -p "$LOG_DIR"

if [ ! -x "$VENV/bin/python" ]; then
  echo "No existe venv SGLang en $VENV"
  exit 10
fi

if [ "$(find "$MODEL_DIR_REAL" -maxdepth 1 -name 'model-*.safetensors' | wc -l)" -ne 64 ]; then
  echo "Modelo incompleto en $MODEL_DIR_REAL"
  exit 11
fi

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "SGLang ya esta activo: $(cat "$PID_FILE")"
  ps -fp "$(cat "$PID_FILE")" || true
  exit 0
fi

rm -f "$PID_FILE"

(
  cd "$ROOT"
  source "$VENV/bin/activate"
  SITE_PACKAGES="$VENV/lib/python3.11/site-packages"
  export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
  if [ -x "$CUDA_HOME_LOCAL/bin/nvcc" ]; then
    export CUDA_HOME="$CUDA_HOME_LOCAL"
    export PATH="$CUDA_HOME_LOCAL/bin:$PATH"
    export CUDACXX="$CUDA_HOME_LOCAL/bin/nvcc"
    export LD_LIBRARY_PATH="$CUDA_HOME_LOCAL/lib64:$SITE_PACKAGES/nvidia/cuda_runtime/lib:$SITE_PACKAGES/nvidia/cuda_nvrtc/lib:$SITE_PACKAGES/nvidia/cublas/lib:$SITE_PACKAGES/nvidia/cudnn/lib:$SITE_PACKAGES/nvidia/cusparse/lib:$SITE_PACKAGES/nvidia/cusparselt/lib:$SITE_PACKAGES/nvidia/cusolver/lib:$SITE_PACKAGES/nvidia/nccl/lib:$SITE_PACKAGES/nvidia/nvjitlink/lib:$SITE_PACKAGES/nvidia/nvshmem/lib:${LD_LIBRARY_PATH:-}"
  else
    export CUDA_HOME="$SITE_PACKAGES/nvidia/cuda_runtime"
    export LD_LIBRARY_PATH="$SITE_PACKAGES/nvidia/cuda_runtime/lib:$SITE_PACKAGES/nvidia/cuda_nvrtc/lib:$SITE_PACKAGES/nvidia/cublas/lib:$SITE_PACKAGES/nvidia/cudnn/lib:$SITE_PACKAGES/nvidia/cusparse/lib:$SITE_PACKAGES/nvidia/cusparselt/lib:$SITE_PACKAGES/nvidia/cusolver/lib:$SITE_PACKAGES/nvidia/nccl/lib:$SITE_PACKAGES/nvidia/nvjitlink/lib:$SITE_PACKAGES/nvidia/nvshmem/lib:${LD_LIBRARY_PATH:-}"
  fi
  export NCCL_P2P_DISABLE="${NCCL_P2P_DISABLE:-1}"
  export NCCL_IB_DISABLE="${NCCL_IB_DISABLE:-1}"
  export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"
  export CUDA_DEVICE_MAX_CONNECTIONS="${CUDA_DEVICE_MAX_CONNECTIONS:-1}"
  export OMP_NUM_THREADS="$CPU_THREADS"
  export MKL_NUM_THREADS="$CPU_THREADS"
  export SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1
  nohup python -m sglang.launch_server \
    --host "$HOST" \
    --port "$PORT" \
    --model-path "$MODEL_DIR_REAL" \
    --served-model-name Kimi-K2.6 \
    --trust-remote-code \
    --tensor-parallel-size "$TP" \
    --tool-call-parser kimi_k2 \
    $([ "$ENABLE_REASONING_PARSER" = "1" ] && printf '%s %s' '--reasoning-parser' 'kimi_k2') \
    $([ "$CPU_OFFLOAD_GB" != "0" ] && printf '%s %s' '--cpu-offload-gb' "$CPU_OFFLOAD_GB") \
    --mem-fraction-static "$MEM_FRACTION_STATIC" \
    --max-total-tokens "$MAX_TOTAL_TOKENS" \
    --chunked-prefill-size "$CHUNKED_PREFILL_SIZE" \
    --enable-mixed-chunk \
    --disable-shared-experts-fusion \
    --attention-backend flashinfer \
    $([ "$DISABLE_CUDA_GRAPH" = "1" ] && printf '%s' '--disable-cuda-graph') \
    > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
)

echo "SGLang Kimi iniciado: $(cat "$PID_FILE")"
echo "Log: $LOG_FILE"
echo "Endpoint: http://127.0.0.1:$PORT/v1"
