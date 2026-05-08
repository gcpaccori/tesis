#!/usr/bin/env bash
set -euo pipefail

MODEL_ID=${MODEL_ID:-google/gemma-4-26B-A4B-it}
MODEL_DIR=${MODEL_DIR:-/home/u23u/models/Gemma-4-26B-A4B-it}
VENV=${VENV:-/home/u23u/miniconda/envs/orquesta_py311}
HF_HOME=${HF_HOME:-/home/u23u/.cache/huggingface}

export HF_HOME
export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-1}

mkdir -p "$MODEL_DIR"

if [ ! -x "$VENV/bin/hf" ]; then
  echo "hf CLI no existe en $VENV/bin" >&2
  exit 2
fi

echo "Descargando $MODEL_ID en $MODEL_DIR"
"$VENV/bin/hf" download \
  --local-dir "$MODEL_DIR" \
  --include "*" \
  --exclude "*.msgpack" \
  --exclude "*.h5" \
  --exclude "*.ot" \
  --exclude "*.onnx" \
  "$MODEL_ID"

echo "Descarga terminada o reanudada. Archivos principales:"
find "$MODEL_DIR" -maxdepth 1 -type f | sed "s#$MODEL_DIR/##" | sort | head -80
