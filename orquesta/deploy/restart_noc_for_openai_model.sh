#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/home/u23u/langgraph-swarm/app}
DATA_DIR=${DATA_DIR:-/home/u23u/langgraph-swarm/runtime/noc}
BASE_URL=${BASE_URL:-http://127.0.0.1:8098/v1}
MODEL=${MODEL:-gemma-4-26b-a4b-agents}
PARALLEL=${PARALLEL:-6}
PHOENIX=${PHOENIX:-http://127.0.0.1:6006/v1/traces}

cd "$APP_DIR"
podman build -t localhost/kimi-langgraph-swarm:latest .
podman rm -f qa-langgraph-swarm >/dev/null 2>&1 || true
podman run -d --name qa-langgraph-swarm --network host \
  -v "$DATA_DIR:/data:Z" \
  -e KIMI_BASE_URL="$BASE_URL" \
  -e KIMI_MODEL="$MODEL" \
  -e KIMI_PARALLEL="$PARALLEL" \
  -e LEARN_PATH=/data/learned.jsonl \
  -e PHOENIX_OTLP_ENDPOINT="$PHOENIX" \
  localhost/kimi-langgraph-swarm:latest

sleep 4
curl -sS http://127.0.0.1:7870/health
