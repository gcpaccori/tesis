#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="${ROOT_DIR:-/home/u23u/langflow-qa}"
MODEL_REPO="${MODEL_REPO:-/home/u23u/.cache/huggingface/hub/models--unsloth--Kimi-K2.6-GGUF}"
SNAPSHOT="${SNAPSHOT:-47c7cab1e440dd9fcfc57c469e4737983408a6f2}"
Q4_MODEL="${Q4_MODEL:-/models/kimi-repo/snapshots/${SNAPSHOT}/UD-Q4_K_XL/Kimi-K2.6-UD-Q4_K_XL-00001-of-00014.gguf}"
HOST_Q4_FIRST_SHARD="${HOST_Q4_FIRST_SHARD:-${MODEL_REPO}/snapshots/${SNAPSHOT}/UD-Q4_K_XL/Kimi-K2.6-UD-Q4_K_XL-00001-of-00014.gguf}"
IMAGE="${IMAGE:-ghcr.io/ggml-org/llama.cpp:server-cuda}"
PROXY_IMAGE="${PROXY_IMAGE:-langflowai/langflow:latest}"
NETWORK="${NETWORK:-qa_agent_network}"

CPU_CONTAINER="${CPU_CONTAINER:-qa-kimi-q4-cpu-test}"
GPU_CONTAINER="${GPU_CONTAINER:-qa-kimi-q4-gpu}"
PROXY_CONTAINER="${PROXY_CONTAINER:-qa-kimi-q4-proxy}"

CPU_PORT="${CPU_PORT:-8041}"
GPU_PORT="${GPU_PORT:-8088}"
PROXY_PORT="${PROXY_PORT:-8089}"

CPU_THREADS="${CPU_THREADS:-256}"
PHASE1_CTX="${PHASE1_CTX:-4096}"
FINAL_CTX="${FINAL_CTX:-2000000}"
ROPE_FREQ_SCALE="${ROPE_FREQ_SCALE:-0.125}"
# Q4 at 2M context needs headroom. 28 layers can exceed 46 GB on several L40S.
# 20 is the safe long-agent default; raise to 24 only after a clean fit test.
GPU_LAYERS="${GPU_LAYERS:-20}"
GPU_TENSOR_SPLIT="${GPU_TENSOR_SPLIT:-1,1,1,1,1,1}"
ALIAS="${ALIAS:-kimi-k2.6-q4}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/runtime/kimi-q4/$(date -u +%Y%m%d-%H%M%S)}"
PHASE1_MARKER="${PHASE1_MARKER:-${ROOT_DIR}/runtime/kimi-q4/PHASE1_OK}"

mkdir -p "${LOG_DIR}"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${LOG_DIR}/control.log"
}

fail() {
  log "BLOQUEADO: $*"
  log "Logs: ${LOG_DIR}"
  exit 1
}

run() {
  log "+ $*"
  "$@" 2>&1 | tee -a "${LOG_DIR}/control.log"
}

wait_models() {
  local port="$1"
  local seconds="$2"
  local deadline=$((SECONDS + seconds))
  while (( SECONDS < deadline )); do
    if curl -fsS -m 10 "http://127.0.0.1:${port}/v1/models" > "${LOG_DIR}/models-${port}.json" 2>>"${LOG_DIR}/control.log"; then
      log "Endpoint /v1/models listo en puerto ${port}"
      return 0
    fi
    sleep 10
  done
  return 1
}

validate_inference() {
  local port="$1"
  local expected="$2"
  python3 - "$port" "$ALIAS" "$expected" > "${LOG_DIR}/inference-${port}.log" 2>&1 <<'PY'
import json
import sys
import requests

port, model, expected = sys.argv[1:4]
payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "Responde breve en espanol."},
        {"role": "user", "content": "Responde exactamente: " + expected},
    ],
    "temperature": 0.0,
    "max_tokens": 80,
    "chat_template_kwargs": {"thinking": False},
}
r = requests.post(f"http://127.0.0.1:{port}/v1/chat/completions", json=payload, timeout=900)
print("status", r.status_code)
print(r.text[:4000])
r.raise_for_status()
data = r.json()
msg = data["choices"][0]["message"]
text = (msg.get("content") or msg.get("reasoning_content") or "").strip()
print("usable_text", text)
if not text:
    raise SystemExit("empty model response")
PY
}

validate_files() {
  log "Validando shards Q4"
  [[ -f "${HOST_Q4_FIRST_SHARD}" ]] || fail "No existe primer shard Q4: ${HOST_Q4_FIRST_SHARD}"
  local count
  count="$(find -L "${MODEL_REPO}/snapshots/${SNAPSHOT}/UD-Q4_K_XL" -maxdepth 1 -type f -name '*.gguf' | wc -l)"
  [[ "${count}" -eq 14 ]] || fail "Q4 incompleto: esperaba 14 shards, encontre ${count}"
  du -shL "${MODEL_REPO}/snapshots/${SNAPSHOT}/UD-Q4_K_XL" | tee -a "${LOG_DIR}/control.log"
}

stop_previous_kimi() {
  log "Apagando solo Kimi Q2/Q4 previo para liberar VRAM; LangFlow, Memgraph y Ollama quedan intactos"
  podman rm -f qa-kimi-proxy qa-kimi-k2-6 "${CPU_CONTAINER}" "${GPU_CONTAINER}" "${PROXY_CONTAINER}" >/dev/null 2>&1 || true
}

phase1_cpu_ram() {
  log "FASE 1: CPU/RAM puro, CUDA deshabilitado, Q4 completo en RAM con --no-mmap"
  run free -h
  run podman run -d --name "${CPU_CONTAINER}" \
    --replace \
    --user 0:0 \
    --security-opt label=disable \
    --network "${NETWORK}" \
    -e CUDA_VISIBLE_DEVICES=-1 \
    -e NVIDIA_VISIBLE_DEVICES=none \
    -e LD_LIBRARY_PATH=/usr/lib:/usr/local/cuda/lib64 \
    -p "127.0.0.1:${CPU_PORT}:${CPU_PORT}" \
    -v "${MODEL_REPO}:/models/kimi-repo:ro" \
    "${IMAGE}" \
      --model "${Q4_MODEL}" \
      --alias "${ALIAS}" \
      --host 0.0.0.0 \
      --port "${CPU_PORT}" \
      --ctx-size "${PHASE1_CTX}" \
      --parallel 1 \
      --threads "${CPU_THREADS}" \
      --threads-batch "${CPU_THREADS}" \
      --batch-size 256 \
      --ubatch-size 64 \
      --n-gpu-layers 0 \
      --no-mmap

  wait_models "${CPU_PORT}" 3600 || {
    podman logs "${CPU_CONTAINER}" > "${LOG_DIR}/phase1-container.log" 2>&1 || true
    fail "Fase 1 no expuso /v1/models. Se detiene antes de GPU."
  }
  podman logs "${CPU_CONTAINER}" > "${LOG_DIR}/phase1-container.log" 2>&1 || true
  validate_inference "${CPU_PORT}" "KIMI_Q4_RAM_OK" || fail "Fase 1 cargo pero fallo inferencia basica CPU/RAM. No se procede a GPU."
  log "FASE 1 OK: Q4 carga e infiere en CPU/RAM"
  mkdir -p "$(dirname "${PHASE1_MARKER}")"
  date -u +%Y-%m-%dT%H:%M:%SZ > "${PHASE1_MARKER}"
  podman rm -f "${CPU_CONTAINER}" >/dev/null 2>&1 || true
}

phase2_gpu_ram() {
  log "FASE 2/3: Q4 hibrido RAM+VRAM, GPUs fisicas 0-5, KV en RAM, contexto objetivo ${FINAL_CTX}"
  log "Nota tecnica: llama.cpp hace offload por capas, no expert-offloading fino por experto MoE como ktransformers."
  run numactl --interleave=all podman run -d --name "${GPU_CONTAINER}" \
    --replace \
    --user 0:0 \
    --security-opt label=disable \
    --network "${NETWORK}" \
    --network-alias kimi-q4.local \
    -e CUDA_DEVICE_ORDER=PCI_BUS_ID \
    -e CUDA_VISIBLE_DEVICES=0,1,2,3,4,5 \
    -e NVIDIA_VISIBLE_DEVICES=0,1,2,3,4,5 \
    -e LD_LIBRARY_PATH=/usr/lib:/usr/local/cuda/lib64 \
    -p "127.0.0.1:${GPU_PORT}:${GPU_PORT}" \
    -v "${MODEL_REPO}:/models/kimi-repo:ro" \
    -v /lib64/libcuda.so.1:/usr/lib/libcuda.so.1:ro \
    -v /lib64/libcuda.so:/usr/lib/libcuda.so:ro \
    -v /lib64/libnvidia-ml.so.1:/usr/lib/libnvidia-ml.so.1:ro \
    -v /lib64/libnvidia-ml.so:/usr/lib/libnvidia-ml.so:ro \
    --device /dev/nvidia0 \
    --device /dev/nvidia1 \
    --device /dev/nvidia2 \
    --device /dev/nvidia3 \
    --device /dev/nvidia6 \
    --device /dev/nvidia7 \
    --device /dev/nvidiactl \
    --device /dev/nvidia-modeset \
    --device /dev/nvidia-uvm \
    --device /dev/nvidia-uvm-tools \
    "${IMAGE}" \
      --model "${Q4_MODEL}" \
      --alias "${ALIAS}" \
      --host 0.0.0.0 \
      --port "${GPU_PORT}" \
      --ctx-size "${FINAL_CTX}" \
      --parallel 1 \
      --threads "${CPU_THREADS}" \
      --threads-batch "${CPU_THREADS}" \
      --batch-size 512 \
      --ubatch-size 128 \
      --flash-attn on \
      --split-mode row \
      --tensor-split "${GPU_TENSOR_SPLIT}" \
      --n-gpu-layers "${GPU_LAYERS}" \
      --cache-type-k q8_0 \
      --cache-type-v q8_0 \
      --no-kv-offload \
      --rope-freq-scale "${ROPE_FREQ_SCALE}" \
      --no-mmap

  wait_models "${GPU_PORT}" 3600 || {
    podman logs "${GPU_CONTAINER}" > "${LOG_DIR}/phase2-container.log" 2>&1 || true
    fail "Fase 2/3 no expuso /v1/models. Revisar VRAM/RAM/logs."
  }
  podman logs "${GPU_CONTAINER}" > "${LOG_DIR}/phase2-container.log" 2>&1 || true
  validate_inference "${GPU_PORT}" "KIMI_Q4_GPU_OK" || fail "Fase 2/3 cargo pero fallo inferencia hibrida."
  log "FASE 2/3 OK: Q4 hibrido responde"
}

start_proxy() {
  log "Levantando proxy OpenAI-compatible para LangFlow"
  run podman run -d --name "${PROXY_CONTAINER}" \
    --replace \
    --user 0:0 \
    --security-opt label=disable \
    --network "${NETWORK}" \
    --network-alias kimi-q4-proxy.local \
    -e KIMI_UPSTREAM_BASE_URL="http://kimi-q4.local:${GPU_PORT}/v1" \
    -e KIMI_DEFAULT_MODEL="${ALIAS}" \
    -p "127.0.0.1:${PROXY_PORT}:8031" \
    -v "${ROOT_DIR}/kimi_openai_proxy.py:/app/kimi_openai_proxy.py:ro" \
    -w /app \
    "${PROXY_IMAGE}" \
      python -m uvicorn kimi_openai_proxy:app --host 0.0.0.0 --port 8031
  sleep 3
  curl -fsS "http://127.0.0.1:${PROXY_PORT}/health" | tee -a "${LOG_DIR}/control.log" >/dev/null
  log "Proxy Q4 listo para LangFlow: http://kimi-q4-proxy.local:8031/v1 modelo ${ALIAS}"
}

status() {
  podman ps --format '{{.Names}} {{.Status}} {{.Ports}}' | egrep 'qa-kimi|qa-langflow|qa-ollama|qa-memgraph|qa-runner' || true
  nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true
  free -h || true
}

main() {
  local cmd="${1:-deploy}"
  case "${cmd}" in
    validate-files)
      validate_files
      ;;
    phase1)
      validate_files
      stop_previous_kimi
      phase1_cpu_ram
      ;;
    phase2)
      validate_files
      [[ -f "${PHASE1_MARKER}" ]] || fail "No existe marcador de Fase 1 OK: ${PHASE1_MARKER}"
      stop_previous_kimi
      phase2_gpu_ram
      start_proxy
      status | tee -a "${LOG_DIR}/control.log"
      ;;
    deploy)
      validate_files
      stop_previous_kimi
      phase1_cpu_ram
      phase2_gpu_ram
      start_proxy
      status | tee -a "${LOG_DIR}/control.log"
      log "DESPLIEGUE COMPLETO. LangFlow Base URL: http://kimi-q4-proxy.local:8031/v1 ; Model: ${ALIAS}"
      ;;
    stop)
      podman rm -f "${CPU_CONTAINER}" "${GPU_CONTAINER}" "${PROXY_CONTAINER}" >/dev/null 2>&1 || true
      log "Kimi Q4 detenido"
      ;;
    status)
      status
      ;;
    *)
      echo "Uso: $0 {validate-files|phase1|deploy|stop|status}" >&2
      exit 2
      ;;
  esac
}

main "$@"
