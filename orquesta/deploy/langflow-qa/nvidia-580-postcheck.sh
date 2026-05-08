#!/usr/bin/env bash
set -euo pipefail

echo "== NVIDIA driver/runtime postcheck =="
nvidia-smi --query-gpu=index,name,driver_version,memory.used,memory.total,utilization.gpu --format=csv,noheader
echo
cat /proc/driver/nvidia/version 2>/dev/null || true
echo
echo "== CUDA 13 smoke in Kimi venv =="
cd /home/u23u/langflow-qa
source venvs/kimi-sglang/bin/activate
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda, "available", torch.cuda.is_available(), "gpus", torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    x = torch.zeros(1, device=f"cuda:{i}")
    print(i, torch.cuda.get_device_name(i), x.item())
PY
