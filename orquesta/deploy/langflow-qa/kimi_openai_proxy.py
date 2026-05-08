import json
import os
from typing import Any

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


UPSTREAM_BASE_URL = os.getenv("KIMI_UPSTREAM_BASE_URL", "http://kimi.local:8021/v1").rstrip("/")
DEFAULT_MODEL = os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2.6-q2")
IDENTITY_PROMPT = os.getenv(
    "KIMI_IDENTITY_PROMPT",
    (
        "Identidad operacional: eres Kimi 2.6 Q4 local, servido en este servidor privado "
        "para QA, coding agents y orquestacion larga. No digas que eres Kimi 1.5 ni un "
        "modelo de 2025. Si te preguntan por tu version, responde: Kimi 2.6 Q4 local "
        "sobre GGUF/llama.cpp, conectado a LangFlow/OpenCode por un proxy local. "
        "Si no sabes una fecha externa, dilo sin inventar."
    ),
)

app = FastAPI(title="Kimi OpenAI Compatibility Proxy")


def _prepare_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload.setdefault("model", DEFAULT_MODEL)
    messages = list(payload.get("messages") or [])
    messages.insert(0, {"role": "system", "content": IDENTITY_PROMPT})
    payload["messages"] = messages

    # Kimi K2.6 GGUF returns useful no-think responses under reasoning_content.
    # This default keeps LangFlow from receiving an empty message.content.
    kwargs = dict(payload.get("chat_template_kwargs") or {})
    kwargs.setdefault("thinking", False)
    payload["chat_template_kwargs"] = kwargs
    return payload


def _repair_message(message: dict[str, Any]) -> dict[str, Any]:
    content = message.get("content")
    reasoning = message.get("reasoning_content")
    if (content is None or content == "") and reasoning:
        message["content"] = reasoning
    return message


def _repair_chat_response(data: dict[str, Any]) -> dict[str, Any]:
    for choice in data.get("choices", []):
        message = choice.get("message")
        if isinstance(message, dict):
            _repair_message(message)
        delta = choice.get("delta")
        if isinstance(delta, dict):
            _repair_message(delta)
    return data


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "upstream": UPSTREAM_BASE_URL, "model": DEFAULT_MODEL}


@app.get("/v1/models")
def models() -> JSONResponse:
    response = requests.get(f"{UPSTREAM_BASE_URL}/models", timeout=30)
    return JSONResponse(response.json(), status_code=response.status_code)


@app.get("/api/tags")
def ollama_tags() -> dict[str, Any]:
    return {
        "models": [
            {
                "name": DEFAULT_MODEL,
                "model": DEFAULT_MODEL,
                "modified_at": "",
                "size": 0,
                "digest": "",
                "details": {
                    "format": "gguf",
                    "family": "kimi",
                    "families": ["kimi"],
                    "parameter_size": "1T",
                    "quantization_level": "Q4",
                },
            }
        ]
    }


@app.post("/api/chat")
async def ollama_chat(request: Request):
    payload = await request.json()
    messages = payload.get("messages") or []
    if not messages and payload.get("prompt"):
        messages = [{"role": "user", "content": payload["prompt"]}]

    openai_payload = _prepare_payload(
        {
            "model": payload.get("model") or DEFAULT_MODEL,
            "messages": messages,
            "temperature": payload.get("temperature", payload.get("options", {}).get("temperature", 0.6)),
            "max_tokens": payload.get("max_tokens", payload.get("options", {}).get("num_predict", 1600)),
            "stream": False,
        }
    )
    response = requests.post(
        f"{UPSTREAM_BASE_URL}/chat/completions",
        headers={"Content-Type": "application/json"},
        json=openai_payload,
        timeout=900,
    )
    data = _repair_chat_response(response.json())
    message = data["choices"][0]["message"]
    return {
        "model": openai_payload["model"],
        "created_at": "",
        "message": {"role": "assistant", "content": message.get("content", "")},
        "done": True,
        "total_duration": 0,
        "load_duration": 0,
        "prompt_eval_count": data.get("usage", {}).get("prompt_tokens", 0),
        "eval_count": data.get("usage", {}).get("completion_tokens", 0),
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = _prepare_payload(await request.json())
    headers = {"Content-Type": "application/json"}

    if payload.get("stream"):
        upstream = requests.post(
            f"{UPSTREAM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=900,
            stream=True,
        )

        def events():
            for line in upstream.iter_lines(decode_unicode=True):
                if not line:
                    yield "\n"
                    continue
                if not line.startswith("data: "):
                    yield line + "\n"
                    continue
                raw = line.removeprefix("data: ").strip()
                if raw == "[DONE]":
                    yield "data: [DONE]\n\n"
                    continue
                try:
                    repaired = _repair_chat_response(json.loads(raw))
                    yield f"data: {json.dumps(repaired, ensure_ascii=False)}\n\n"
                except json.JSONDecodeError:
                    yield line + "\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    response = requests.post(
        f"{UPSTREAM_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=900,
    )
    try:
        data = _repair_chat_response(response.json())
    except ValueError:
        return JSONResponse({"error": response.text}, status_code=response.status_code)
    return JSONResponse(data, status_code=response.status_code)


@app.post("/v1/completions")
async def completions(request: Request):
    payload = dict(await request.json())
    payload.setdefault("model", DEFAULT_MODEL)
    response = requests.post(
        f"{UPSTREAM_BASE_URL}/completions",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=900,
    )
    return JSONResponse(response.json(), status_code=response.status_code)
