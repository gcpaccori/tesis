#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_REPO="${MODEL_REPO:-moonshotai/Kimi-K2.6}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
LOG_DIR="$ROOT/runtime/kimi-k26"
LOG_FILE="$LOG_DIR/download-serial.log"

mkdir -p "$MODEL_DIR" "$LOG_DIR"

cat > "$LOG_DIR/download_serial.py" <<'PY'
import os
import time
from huggingface_hub import HfApi, hf_hub_download

repo = os.environ.get("MODEL_REPO", "moonshotai/Kimi-K2.6")
model_dir = os.environ.get("MODEL_DIR", "/home/u23u/models/Kimi-K2.6")
retries = int(os.environ.get("KIMI_DOWNLOAD_RETRIES", "20"))

api = HfApi()
info = api.model_info(repo, files_metadata=True)
files = [s.rfilename for s in info.siblings]

priority = []
priority.extend([
    "config.json",
    "generation_config.json",
    "model.safetensors.index.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "configuration_deepseek.py",
    "configuration_kimi_k25.py",
    "modeling_deepseek.py",
    "modeling_kimi_k25.py",
])
priority.extend([f"model-{i:05d}-of-000064.safetensors" for i in range(1, 65)])

ordered = [f for f in priority if f in files]
ordered.extend(sorted(f for f in files if f not in set(ordered)))

print(f"Descarga serial {repo} -> {model_dir}", flush=True)
print(f"Archivos remotos: {len(files)}; plan: {len(ordered)}", flush=True)

for idx, name in enumerate(ordered, 1):
    target = os.path.join(model_dir, name)
    if os.path.exists(target) and os.path.getsize(target) > 0:
        print(f"[{idx}/{len(ordered)}] OK existe {name} ({os.path.getsize(target)} bytes)", flush=True)
        continue

    for attempt in range(1, retries + 1):
        try:
            print(f"[{idx}/{len(ordered)}] bajando {name} intento {attempt}/{retries}", flush=True)
            path = hf_hub_download(
                repo_id=repo,
                filename=name,
                local_dir=model_dir,
                resume_download=True,
                local_dir_use_symlinks=False,
            )
            print(f"[{idx}/{len(ordered)}] listo {name} -> {path}", flush=True)
            break
        except Exception as exc:
            print(f"[{idx}/{len(ordered)}] ERROR {name}: {type(exc).__name__}: {exc}", flush=True)
            if attempt == retries:
                raise
            time.sleep(min(60, 5 * attempt))

print("Descarga serial completa.", flush=True)
PY

PID_FILE="$LOG_DIR/download-serial.pid"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "Ya existe descarga serial activa."
  ps -fp "$(cat "$PID_FILE")" || true
  exit 0
fi

echo "Iniciando descarga serial en background."
echo "Log: $LOG_FILE"
(
  cd "$ROOT"
  MODEL_REPO="$MODEL_REPO" MODEL_DIR="$MODEL_DIR" \
    nohup /home/u23u/.local/bin/uv run --with huggingface_hub \
      python "$LOG_DIR/download_serial.py" > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
)
echo "PID: $(cat "$PID_FILE")"
