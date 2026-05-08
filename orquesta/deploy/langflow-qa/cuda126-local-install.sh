#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u}"
INSTALLERS="$ROOT/installers"
CUDA_HOME_LOCAL="${CUDA_HOME_LOCAL:-$ROOT/cuda-12.6.3}"
FILE="cuda_12.6.3_560.35.05_linux.run"
URL="https://developer.download.nvidia.com/compute/cuda/12.6.3/local_installers/$FILE"
LOG_DIR="${LOG_DIR:-/home/u23u/langflow-qa/runtime/cuda126}"
LOG_FILE="$LOG_DIR/install.log"
PID_FILE="$LOG_DIR/install.pid"
EXPECTED_BYTES=4446722669

mkdir -p "$INSTALLERS" "$LOG_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "CUDA local install/download ya esta corriendo: PID $(cat "$PID_FILE")"
  echo "Log: $LOG_FILE"
  exit 0
fi

(
  set -euo pipefail
  cd "$INSTALLERS"
  echo "[$(date -Is)] Reanudando descarga: $URL"
  curl -fL --continue-at - -o "$FILE" "$URL"
  size="$(stat -c%s "$FILE")"
  echo "[$(date -Is)] Descarga: $size/$EXPECTED_BYTES bytes"
  if [ "$size" -lt "$EXPECTED_BYTES" ]; then
    echo "Descarga incompleta"
    exit 20
  fi
  chmod +x "$FILE"
  mkdir -p "$CUDA_HOME_LOCAL"
  echo "[$(date -Is)] Instalando toolkit local en $CUDA_HOME_LOCAL"
  sh "$FILE" --silent --toolkit --toolkitpath="$CUDA_HOME_LOCAL" --no-man-page --override
  "$CUDA_HOME_LOCAL/bin/nvcc" --version
  echo "[$(date -Is)] CUDA toolkit local listo"
) > "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "CUDA local install/download iniciado: PID $(cat "$PID_FILE")"
echo "Log: $LOG_FILE"
