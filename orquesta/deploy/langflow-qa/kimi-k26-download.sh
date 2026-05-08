#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_REPO="${MODEL_REPO:-moonshotai/Kimi-K2.6}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
LOG_DIR="$ROOT/runtime/kimi-k26"
LOG_FILE="$LOG_DIR/download.log"

mkdir -p "$MODEL_DIR" "$LOG_DIR"

if pgrep -f "snapshot_download.*${MODEL_REPO}" >/dev/null 2>&1; then
  echo "Ya existe una descarga activa para ${MODEL_REPO}."
  pgrep -af "snapshot_download.*${MODEL_REPO}"
  exit 0
fi

cat > "$LOG_DIR/download_model.py" <<'PY'
import os
from huggingface_hub import snapshot_download

repo = os.environ.get("MODEL_REPO", "moonshotai/Kimi-K2.6")
model_dir = os.environ.get("MODEL_DIR", "/home/u23u/models/Kimi-K2.6")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

print(f"Descargando {repo} en {model_dir}", flush=True)
path = snapshot_download(
    repo_id=repo,
    local_dir=model_dir,
    local_dir_use_symlinks=False,
    resume_download=True,
)
print(f"Descarga completa: {path}", flush=True)
PY

echo "Iniciando descarga en background."
echo "Log: $LOG_FILE"
(
  cd "$ROOT"
  MODEL_REPO="$MODEL_REPO" MODEL_DIR="$MODEL_DIR" \
    nohup /home/u23u/.local/bin/uv run --with huggingface_hub --with hf_transfer \
      python "$LOG_DIR/download_model.py" > "$LOG_FILE" 2>&1 &
  echo $! > "$LOG_DIR/download.pid"
)

echo "PID: $(cat "$LOG_DIR/download.pid")"

