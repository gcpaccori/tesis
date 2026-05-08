#!/usr/bin/env bash
set -euo pipefail
podman run --rm --entrypoint python3 \
  --security-opt=label=disable \
  --device /dev/nvidiactl --device /dev/nvidia-uvm --device /dev/nvidia-uvm-tools \
  --device /dev/nvidia0 --device /dev/nvidia1 --device /dev/nvidia2 --device /dev/nvidia3 \
  --device /dev/nvidia4 --device /dev/nvidia5 --device /dev/nvidia6 --device /dev/nvidia7 \
  -v /usr/lib64/libcuda.so.1:/usr/lib/x86_64-linux-gnu/libcuda.so.1:ro \
  -v /usr/lib64/libcuda.so:/usr/lib/x86_64-linux-gnu/libcuda.so:ro \
  -v /usr/lib64/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:ro \
  -v /usr/lib64/libnvidia-ml.so:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so:ro \
  docker.io/vllm/vllm-openai:v0.20.0 \
  -c "import torch; print('cuda', torch.cuda.is_available(), torch.cuda.device_count()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no-gpu')"
