#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

source "$ROOT_DIR/entorno/vllm_orquesta/bin/activate"
mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/data"

if [[ -f "$ROOT_DIR/logs/orquesta_api.pid" ]]; then
  existing_pid="$(cat "$ROOT_DIR/logs/orquesta_api.pid")"
  if ps -p "$existing_pid" >/dev/null 2>&1; then
    echo "La orquesta ya esta activa con PID $existing_pid"
    exit 0
  fi
fi

nohup python -m scripts.orquestador_director serve --host 0.0.0.0 --port "${ORQUESTA_PORT:-8310}" \
  > "$ROOT_DIR/logs/orquesta_api.log" 2>&1 &

echo $! > "$ROOT_DIR/logs/orquesta_api.pid"
echo "Orquesta levantada en http://0.0.0.0:${ORQUESTA_PORT:-8310}"
