#!/usr/bin/env bash
set -euo pipefail

cd /home/u23u/langgraph-studio-swarm

if [[ -f langgraph-studio.pid ]]; then
  kill "$(cat langgraph-studio.pid)" 2>/dev/null || true
fi

pgrep -f "langgraph dev.*2024" 2>/dev/null | while read -r pid; do
  if [[ "$pid" != "$$" ]]; then
    kill "$pid" 2>/dev/null || true
  fi
done || true

nohup env \
  LANGSMITH_TRACING=false \
  KIMI_BASE_URL=http://127.0.0.1:8021/v1 \
  KIMI_MODEL=kimi-k2.6-q2 \
  PHOENIX_OTLP_ENDPOINT=http://127.0.0.1:6006/v1/traces \
  E2B_LOCAL_MODE=podman \
  E2B_LOCAL_IMAGE=docker.io/library/python:3.12-slim \
  .venv/bin/langgraph dev \
    --host 127.0.0.1 \
    --port 2024 \
    --no-browser \
    --allow-blocking \
    --no-reload \
  > langgraph-studio.log 2>&1 &

echo "$!" > langgraph-studio.pid
sleep 7
curl -sS --max-time 10 http://127.0.0.1:2024/ok
