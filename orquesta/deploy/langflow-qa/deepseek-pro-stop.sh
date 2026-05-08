#!/usr/bin/env bash
set -euo pipefail

export PATH="/home/u23u/.local/bin:/home/u23u/miniconda/bin:/usr/local/bin:/usr/bin:/bin"

podman stop qa-deepseek-v4-pro >/dev/null 2>&1 || true
podman rm qa-deepseek-v4-pro >/dev/null 2>&1 || true

echo "DeepSeek V4 Pro detenido. LangFlow, Memgraph, QA runner y Ollama no se tocaron."
