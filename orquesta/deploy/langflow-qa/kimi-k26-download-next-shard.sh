#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_REPO="${MODEL_REPO:-moonshotai/Kimi-K2.6}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
LOG_DIR="$ROOT/runtime/kimi-k26"
LOG_FILE="$LOG_DIR/download-next-shard.log"
PID_FILE="$LOG_DIR/download-next-shard.pid"

mkdir -p "$MODEL_DIR" "$LOG_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "Ya hay una descarga manual activa."
  ps -fp "$(cat "$PID_FILE")" || true
  exit 0
fi

cat > "$LOG_DIR/download_next_shard.py" <<'PY'
import os
import sys
from huggingface_hub import hf_hub_download

repo = os.environ.get("MODEL_REPO", "moonshotai/Kimi-K2.6")
model_dir = os.environ.get("MODEL_DIR", "/home/u23u/models/Kimi-K2.6")

missing = None
for i in range(1, 65):
    name = f"model-{i:05d}-of-000064.safetensors"
    path = os.path.join(model_dir, name)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        missing = name
        break

if missing is None:
    print("Todos los shards ya existen.", flush=True)
    sys.exit(0)

print(f"Siguiente shard faltante: {missing}", flush=True)
path = hf_hub_download(
    repo_id=repo,
    filename=missing,
    local_dir=model_dir,
    resume_download=True,
    local_dir_use_symlinks=False,
)
print(f"Shard completado: {path}", flush=True)
PY

echo "Iniciando descarga manual del siguiente shard."
echo "Log: $LOG_FILE"
(
  cd "$ROOT"
  MODEL_REPO="$MODEL_REPO" MODEL_DIR="$MODEL_DIR" \
    nohup /home/u23u/.local/bin/uv run --with huggingface_hub \
      python "$LOG_DIR/download_next_shard.py" > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
)
echo "PID: $(cat "$PID_FILE")"

