#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
LOG_DIR="$ROOT/runtime/kimi-k26"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
PIPELINE_LOG="$LOG_DIR/gated-pipeline.log"

mkdir -p "$LOG_DIR"

exec > >(tee -a "$PIPELINE_LOG") 2>&1

echo "[$(date -Is)] Inicio pipeline Kimi 2.6 gated"
echo "ROOT=$ROOT"
echo "MODEL_DIR=$MODEL_DIR"

if ! pgrep -f "download_model.py" >/dev/null 2>&1; then
  echo "No hay descarga activa; iniciando descarga."
  "$ROOT/kimi-k26-download.sh"
fi

echo "Esperando descarga completa: 64 shards safetensors + model index."
while true; do
  shards="$(find "$MODEL_DIR" -name 'model-*.safetensors' 2>/dev/null | wc -l)"
  files="$(find "$MODEL_DIR" -type f 2>/dev/null | wc -l)"
  size="$(du -sh "$MODEL_DIR" 2>/dev/null | awk '{print $1}')"
  echo "[$(date -Is)] descarga: shards=$shards/64 files=$files size=$size"

  if [ "$shards" -eq 64 ] && [ -f "$MODEL_DIR/model.safetensors.index.json" ]; then
    if ! pgrep -f "download_model.py" >/dev/null 2>&1; then
      echo "Descarga completa detectada."
      break
    fi
  fi

  if ! pgrep -f "download_model.py" >/dev/null 2>&1; then
    echo "ERROR: la descarga termino antes de completar los 64 shards."
    tail -80 "$LOG_DIR/download.log" || true
    exit 30
  fi

  sleep 60
done

echo "[$(date -Is)] FASE 1: CPU/RAM completa bloqueante"
KIMI_FULL_CPU_LOAD=1 "$ROOT/kimi-k26-cpu-smoke.sh"

echo "[$(date -Is)] FASE 2: vLLM 8 GPUs"
"$ROOT/kimi-k26-vllm-8gpu.sh"

echo "[$(date -Is)] Pipeline finalizado. Esperando endpoint."
for i in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:8098/v1/models >/tmp/kimi-k26-models.json 2>/dev/null; then
    cat /tmp/kimi-k26-models.json
    echo
    echo "Kimi 2.6 listo en http://127.0.0.1:8098/v1"
    exit 0
  fi
  sleep 10
done

echo "vLLM no respondio a tiempo. Revisar: podman logs qa-kimi-k26-vllm"
exit 40

