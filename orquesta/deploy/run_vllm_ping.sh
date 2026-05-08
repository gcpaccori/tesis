#!/usr/bin/env bash
set -euo pipefail
START=$(date +%s%3N)
curl -sS --max-time 120 http://127.0.0.1:8098/v1/chat/completions \
  -H 'Content-Type: application/json' \
  --data-binary @/tmp/vllm_ping.json > /tmp/vllm_ping.out
END=$(date +%s%3N)
head -c 2000 /tmp/vllm_ping.out
echo
echo elapsed_ms=$((END-START))
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
