#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/logs/orquesta_api.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No existe PID registrado."
  exit 0
fi

pid="$(cat "$PID_FILE")"
if ps -p "$pid" >/dev/null 2>&1; then
  kill "$pid"
  echo "Orquesta detenida ($pid)"
else
  echo "El PID $pid ya no estaba activo."
fi

rm -f "$PID_FILE"
