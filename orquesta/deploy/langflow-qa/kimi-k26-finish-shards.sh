#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
LOG_DIR="$ROOT/runtime/kimi-k26"
LOG_FILE="$LOG_DIR/finish-shards.log"
PID_FILE="$LOG_DIR/finish-shards.pid"
NEXT_PID_FILE="$LOG_DIR/download-next-shard.pid"
STALL_SECONDS="${STALL_SECONDS:-420}"

mkdir -p "$LOG_DIR"

count_shards() {
  find "$MODEL_DIR" -maxdepth 1 -name 'model-*.safetensors' | wc -l
}

model_bytes() {
  du -sb "$MODEL_DIR" | awk '{print $1}'
}

active_next_pid() {
  if [ -f "$NEXT_PID_FILE" ] && kill -0 "$(cat "$NEXT_PID_FILE")" >/dev/null 2>&1; then
    cat "$NEXT_PID_FILE"
    return 0
  fi
  return 1
}

run_supervisor() {
  echo "[$(date -Is)] Supervisor finish-shards iniciado"
  echo "MODEL_DIR=$MODEL_DIR"
  echo "STALL_SECONDS=$STALL_SECONDS"

  while true; do
    shards="$(count_shards)"
    bytes="$(model_bytes)"
    echo "[$(date -Is)] shards=$shards/64 size_bytes=$bytes"

    if [ "$shards" -ge 64 ]; then
      echo "[$(date -Is)] Todos los shards estan completos."
      exit 0
    fi

    if active_next_pid >/dev/null; then
      pid="$(active_next_pid)"
      echo "[$(date -Is)] Descarga activa pid=$pid; vigilando progreso."
    else
      rm -f "$NEXT_PID_FILE"
      "$ROOT/kimi-k26-download-next-shard.sh"
      pid="$(active_next_pid || true)"
      echo "[$(date -Is)] Lanzado siguiente shard pid=${pid:-none}"
    fi

    start_bytes="$(model_bytes)"
    sleep "$STALL_SECONDS"
    end_bytes="$(model_bytes)"
    new_shards="$(count_shards)"
    echo "[$(date -Is)] despues_espera shards=$new_shards/64 bytes=$end_bytes delta=$((end_bytes - start_bytes))"

    if [ "$new_shards" -gt "$shards" ]; then
      echo "[$(date -Is)] Shard cerrado correctamente."
      continue
    fi

    if [ "$end_bytes" -le "$start_bytes" ]; then
      if active_next_pid >/dev/null; then
        pid="$(active_next_pid)"
        echo "[$(date -Is)] Sin crecimiento; matando pid=$pid para reintentar."
        kill "$pid" >/dev/null 2>&1 || true
        sleep 5
        kill -9 "$pid" >/dev/null 2>&1 || true
      fi
      rm -f "$NEXT_PID_FILE"
    fi
  done
}

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "Supervisor ya activo: $(cat "$PID_FILE")"
  ps -fp "$(cat "$PID_FILE")" || true
  exit 0
fi

(
  nohup bash -c "$(declare -f count_shards model_bytes active_next_pid run_supervisor); ROOT='$ROOT' MODEL_DIR='$MODEL_DIR' LOG_DIR='$LOG_DIR' LOG_FILE='$LOG_FILE' PID_FILE='$PID_FILE' NEXT_PID_FILE='$NEXT_PID_FILE' STALL_SECONDS='$STALL_SECONDS' run_supervisor" >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
)

echo "Supervisor iniciado: $(cat "$PID_FILE")"
echo "Log: $LOG_FILE"

