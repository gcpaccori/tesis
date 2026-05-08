#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/u23u/langflow-qa}"
MODEL_DIR="${MODEL_DIR:-/home/u23u/models/Kimi-K2.6}"
LOG_DIR="$ROOT/runtime/kimi-k26"
LOG_FILE="$LOG_DIR/cpu-smoke.log"
OK_FILE="$LOG_DIR/cpu-smoke.ok"
META_OK_FILE="$LOG_DIR/cpu-smoke.metadata.ok"

mkdir -p "$LOG_DIR"
rm -f "$OK_FILE"
rm -f "$META_OK_FILE"

cat > "$LOG_DIR/cpu_smoke.py" <<'PY'
import json
import os
import pathlib
import sys
import time

model_dir = pathlib.Path(os.environ.get("MODEL_DIR", "/home/u23u/models/Kimi-K2.6"))
print(f"CPU/RAM smoke para {model_dir}", flush=True)

if not model_dir.exists():
    raise SystemExit(f"No existe MODEL_DIR={model_dir}")

config_path = model_dir / "config.json"
index_path = model_dir / "model.safetensors.index.json"
if not config_path.exists():
    raise SystemExit("Falta config.json")
if not index_path.exists():
    raise SystemExit("Falta model.safetensors.index.json; descarga incompleta")

shards = sorted(model_dir.glob("model-*.safetensors"))
print(f"shards detectados: {len(shards)}", flush=True)
if len(shards) != 64:
    raise SystemExit(f"Descarga incompleta: se esperaban 64 shards, hay {len(shards)}")

with config_path.open("r", encoding="utf-8") as f:
    config = json.load(f)
print("model_type:", config.get("model_type"), flush=True)
print("architectures:", config.get("architectures"), flush=True)

with index_path.open("r", encoding="utf-8") as f:
    index = json.load(f)
total_size = index.get("metadata", {}).get("total_size")
print("total_size_index:", total_size, flush=True)

print("validando tokenizer/config en CPU sin CUDA...", flush=True)
os.environ["CUDA_VISIBLE_DEVICES"] = ""
from transformers import AutoConfig, AutoTokenizer

t0 = time.time()
cfg = AutoConfig.from_pretrained(str(model_dir), trust_remote_code=True)
tok = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True)
sample = tok("hola, prueba cpu de Kimi 2.6", return_tensors=None)
print("config_class:", type(cfg).__name__, flush=True)
print("tokenizer_class:", type(tok).__name__, flush=True)
print("sample_tokens:", len(sample.get("input_ids", [])), flush=True)
print(f"smoke_metadata_ok_seconds={time.time() - t0:.2f}", flush=True)
pathlib.Path(os.environ["KIMI_META_OK_FILE"]).touch()

full = os.environ.get("KIMI_FULL_CPU_LOAD", "0") == "1"
if not full:
    print("FULL_CPU_LOAD omitido. Para carga completa en RAM: KIMI_FULL_CPU_LOAD=1", flush=True)
    sys.exit(0)

print("Intentando carga completa CPU/RAM. Esto puede tardar mucho y consumir cientos de GB.", flush=True)
import transformers.utils.import_utils as import_utils
if not hasattr(import_utils, "is_torch_fx_available"):
    import_utils.is_torch_fx_available = lambda: False
from transformers import AutoModelForCausalLM
import torch

cfg._attn_implementation = "eager"
cfg._attn_implementation_internal = "eager"
if hasattr(cfg, "vision_config"):
    cfg.vision_config._attn_implementation = "eager"
    cfg.vision_config._attn_implementation_internal = "eager"

t1 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    str(model_dir),
    config=cfg,
    trust_remote_code=True,
    device_map={"": "cpu"},
    torch_dtype="auto",
    low_cpu_mem_usage=True,
    attn_implementation="eager",
)
inputs = tok("Responde solo OK.", return_tensors="pt")
with torch.inference_mode():
    out = model.generate(**inputs, max_new_tokens=8)
print(tok.decode(out[0], skip_special_tokens=True), flush=True)
print(f"full_cpu_load_ok_seconds={time.time() - t1:.2f}", flush=True)
PY

echo "Ejecutando compuerta CPU/RAM. Log: $LOG_FILE"
(
  cd "$ROOT"
  CUDA_VISIBLE_DEVICES="" MODEL_DIR="$MODEL_DIR" KIMI_META_OK_FILE="$META_OK_FILE" \
    numactl --interleave=all /home/u23u/.local/bin/uv run --python 3.11 \
      --with "transformers==4.56.2" --with torch --with accelerate --with safetensors --with tiktoken --with compressed-tensors \
      python "$LOG_DIR/cpu_smoke.py"
) 2>&1 | tee "$LOG_FILE"

touch "$OK_FILE"
echo "OK CPU/RAM: $OK_FILE"
