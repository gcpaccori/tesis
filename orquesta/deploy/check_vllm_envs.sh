#!/usr/bin/env bash
set -euo pipefail
for v in /home/u23u/langflow-qa/venvs/kimi-vllm311 /home/u23u/langflow-qa/venvs/kimi-vllm /home/u23u/orquesta/entorno/vllm_orquesta /home/u23u/miniconda/envs/orquesta_py311; do
  echo "--- $v"
  if [ -x "$v/bin/python" ]; then
    "$v/bin/python" - <<'PY'
try:
 import torch
 print('torch', torch.__version__, 'cuda', torch.version.cuda, 'avail', torch.cuda.is_available(), 'count', torch.cuda.device_count())
except Exception as e:
 print('torch err', repr(e))
try:
 import vllm
 print('vllm', getattr(vllm,'__version__', '?'))
except Exception as e:
 print('vllm err', repr(e))
PY
  fi
done
