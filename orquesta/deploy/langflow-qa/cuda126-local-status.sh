#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-/home/u23u/langflow-qa/runtime/cuda126}"
PID_FILE="$LOG_DIR/install.pid"
LOG_FILE="$LOG_DIR/install.log"
FILE="/home/u23u/installers/cuda_12.6.3_560.35.05_linux.run"
EXPECTED_BYTES=4446722669

echo "== CUDA 12.6 local status =="
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "Proceso vivo: $(cat "$PID_FILE")"
else
  echo "Proceso vivo: no"
fi

if [ -f "$FILE" ]; then
  size="$(stat -c%s "$FILE")"
  python3 - <<PY
size=$size
expected=$EXPECTED_BYTES
print(f"Descarga: {size/1024/1024/1024:.2f} GiB / {expected/1024/1024/1024:.2f} GiB ({size/expected*100:.1f}%)")
PY
else
  echo "Descarga: no existe"
fi

if [ -x /home/u23u/cuda-12.6.3/bin/nvcc ]; then
  /home/u23u/cuda-12.6.3/bin/nvcc --version | tail -4
else
  echo "nvcc local: no instalado aun"
fi

echo
echo "== Log tail =="
tail -40 "$LOG_FILE" 2>/dev/null || true
