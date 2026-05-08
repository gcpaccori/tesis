#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://127.0.0.1:8020/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "deepseek-v4-pro",
    "messages": [
      {
        "role": "system",
        "content": "Eres DeepSeek V4 Pro local para QA corporativo C#, frontend, gateway y datos. Responde breve, tecnico y accionable."
      },
      {
        "role": "user",
        "content": "Confirma que estas local y propone un gate QA de 5 pasos para Electro Sur."
      }
    ],
    "temperature": 1.0,
    "top_p": 1.0,
    "max_tokens": 768
  }'
