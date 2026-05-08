from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from scripts.especialistas_liquidos import EspecialistaLiquido, seleccionar_especialistas
from scripts.motor_grafos import MemoriaGrafo
from scripts.swarm_runtime import SwarmRuntime

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DIRECTOR_MODEL = os.getenv(
    "ORQUESTA_DIRECTOR_MODEL",
    os.getenv("ORQUESTA_MODEL", "Qwen3.5-14B-A2.4B-8bit"),
)
DEFAULT_SUBMANAGER_MODEL = os.getenv(
    "ORQUESTA_SUBMANAGER_MODEL",
    "Qwen3.5-14B-A2.4B-8bit",
)
DEFAULT_SWARM_CODER_MODEL = os.getenv(
    "ORQUESTA_SWARM_CODER_MODEL",
    "Qwen3.5-7B-Coder",
)
DEFAULT_SWARM_MATH_MODEL = os.getenv(
    "ORQUESTA_SWARM_MATH_MODEL",
    "Qwen3.5-7B-Math",
)
DEFAULT_AVATAR_MODEL = os.getenv(
    "ORQUESTA_AVATAR_MODEL",
    "Qwen3.5-7B-1M",
)
DEFAULT_BASE_URL = os.getenv("ORQUESTA_BASE_URL", "http://localhost:8100/v1")
DEFAULT_API_KEY = os.getenv("ORQUESTA_API_KEY", "sk-local")
DEFAULT_MODEL_TIMEOUT = float(os.getenv("ORQUESTA_MODEL_TIMEOUT", "45"))
CHAT_UI_PATH = BASE_DIR / "ui" / "chat.html"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = Field(default="principal", min_length=1)


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    selected_specialists: list[str]
    memory_context: str
    memory_write: Dict[str, Any]


class SwarmBootstrapResponse(BaseModel):
    session_id: str
    backend_mode: str
    director_model: str
    agents: List[Dict[str, Any]]
    architecture: Dict[str, Any]
    messages: List[Dict[str, Any]]
    cell_states: List[Dict[str, Any]]
    tool_events: List[Dict[str, Any]]


class SwarmChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = Field(default="pixel-browser", min_length=1)
    target_agent_id: int | None = None


class SwarmChatResponse(BaseModel):
    session_id: str
    backend_mode: str
    director_model: str
    director_reply: Dict[str, Any]
    messages: List[Dict[str, Any]]
    cell_states: List[Dict[str, Any]]
    tool_events: List[Dict[str, Any]]
    selected_cells: List[str]
    memory_write: Dict[str, Any]


class DirectorOrquesta:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            base_url=DEFAULT_BASE_URL,
            api_key=DEFAULT_API_KEY,
            timeout=DEFAULT_MODEL_TIMEOUT,
        )
        self.model_plan = {
            "director": {
                "name": DEFAULT_DIRECTOR_MODEL,
                "env_var": "ORQUESTA_DIRECTOR_MODEL",
            },
            "submanager": {
                "name": DEFAULT_SUBMANAGER_MODEL,
                "env_var": "ORQUESTA_SUBMANAGER_MODEL",
            },
            "swarm_coder": {
                "name": DEFAULT_SWARM_CODER_MODEL,
                "env_var": "ORQUESTA_SWARM_CODER_MODEL",
            },
            "swarm_math": {
                "name": DEFAULT_SWARM_MATH_MODEL,
                "env_var": "ORQUESTA_SWARM_MATH_MODEL",
            },
            "avatar": {
                "name": DEFAULT_AVATAR_MODEL,
                "env_var": "ORQUESTA_AVATAR_MODEL",
            },
        }
        self.model = DEFAULT_DIRECTOR_MODEL
        self.memoria = MemoriaGrafo()

    async def responder(self, message: str, session_id: str = "principal") -> ChatResponse:
        memoria = self.memoria.buscar(message)
        specialists = seleccionar_especialistas(message)
        specialist_notes = await self._consultar_especialistas(message, memoria.to_prompt_block(), specialists)
        answer = await self._sintetizar_respuesta(message, memoria.to_prompt_block(), specialist_notes)
        memory_payload = await self._extraer_memoria(message, answer, specialist_notes, specialists)
        write_result = self.memoria.registrar_turno(
            session_id=session_id,
            user_message=message,
            assistant_message=answer,
            route=[item.nombre for item in specialists],
            specialist_notes=specialist_notes,
            memory_payload=memory_payload,
        )
        return ChatResponse(
            answer=answer,
            session_id=session_id,
            selected_specialists=[item.nombre for item in specialists],
            memory_context=memoria.to_prompt_block(),
            memory_write=write_result,
        )

    async def _chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 700,
        json_mode: bool = False,
        model: str | None = None,
    ) -> str:
        request_kwargs: Dict[str, Any] = {
            "model": model or self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**request_kwargs)
        return _sanitize_model_output(response.choices[0].message.content or "", json_mode=json_mode)

    async def _consultar_especialistas(
        self,
        message: str,
        memory_context: str,
        specialists: List[EspecialistaLiquido],
    ) -> Dict[str, str]:
        async def run_specialist(especialista: EspecialistaLiquido) -> Tuple[str, str]:
            content = await self._chat(
                [
                    {
                        "role": "system",
                        "content": (
                            f"Eres {especialista.nombre}. {especialista.mision} "
                            f"Trabajas dentro de una orquesta local, privada y cognitiva. "
                            "No ejecutes despliegues, QA real, auditorias activas ni acciones sobre sistemas. "
                            "No muestres razonamiento interno ni etiquetas tipo <think>. "
                            "Devuelve un memo breve en espanol con tres bloques: lectura, criterio y aporte."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Memoria relevante:\n{memory_context}\n\n"
                            f"Mensaje del usuario:\n{message}\n\n"
                            f"Foco del rol: {especialista.foco}"
                        ),
                    },
                ],
                temperature=0.15,
                max_tokens=450,
                model=self.model_plan["swarm_coder"]["name"],
            )
            return especialista.nombre, content

        results = await asyncio.gather(*(run_specialist(item) for item in specialists))
        return {name: note for name, note in results}

    async def _sintetizar_respuesta(
        self,
        message: str,
        memory_context: str,
        specialist_notes: Dict[str, str],
    ) -> str:
        notes_block = "\n\n".join(f"[{name}]\n{note}" for name, note in specialist_notes.items())
        return await self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Eres el Director de una orquesta cognitiva local, privada y extensible. "
                        "Coordina especialistas liquidos y usa la memoria de grafos sin depender de notas fragiles. "
                        "Responde en espanol. Prioriza claridad, direccion arquitectonica y soberania local. "
                        "No propongas acciones operativas sobre IIS, QA real, ataques ni automatizacion ofensiva. "
                        "No muestres razonamiento interno ni etiquetas tipo <think>. "
                        "Cuando uses memoria, integrala naturalmente sin citar bloques internos."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Memoria consultada:\n{memory_context}\n\n"
                        f"Memos de especialistas:\n{notes_block}\n\n"
                        f"Mensaje actual:\n{message}\n\n"
                        "Entrega una respuesta final compacta pero sustantiva. "
                        "Incluye una propuesta concreta para el siguiente paso si aplica."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=700,
            model=self.model_plan["director"]["name"],
        )

    async def _extraer_memoria(
        self,
        message: str,
        answer: str,
        specialist_notes: Dict[str, str],
        specialists: List[EspecialistaLiquido],
    ) -> Dict[str, Any]:
        specialist_block = "\n".join(f"- {name}: {note}" for name, note in specialist_notes.items())
        raw = await self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Extrae memoria estructurada para un grafo persistente. "
                        "Devuelve solo JSON valido con este esquema: "
                        "{\"summary\":str,\"entities\":[{\"name\":str,\"type\":str,\"metadata\":{}}],"
                        "\"relations\":[{\"source\":str,\"target\":str,\"type\":str,\"metadata\":{}}],"
                        "\"decisions\":[str],\"open_loops\":[str]}. "
                        "No incluyas texto fuera del JSON ni razonamiento interno."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Roles activos: {[item.nombre for item in specialists]}\n"
                        f"Mensaje del usuario: {message}\n"
                        f"Respuesta final: {answer}\n"
                        f"Notas especialistas:\n{specialist_block}\n"
                        "Extrae solo lo estable y reutilizable."
                    ),
                },
            ],
            temperature=0.0,
            max_tokens=500,
            json_mode=True,
            model=self.model_plan["avatar"]["name"],
        )
        parsed = _safe_json_load(raw)
        return _merge_memory_payload(parsed, _heuristic_memory_payload(message, answer, specialists))


def _safe_json_load(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {
            "summary": "Interaccion sin resumen estructurado.",
            "entities": [],
            "relations": [],
            "decisions": [],
            "open_loops": [],
        }

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {
        "summary": text[:220],
        "entities": [],
        "relations": [],
        "decisions": [],
        "open_loops": [],
    }


def _sanitize_model_output(raw: str, json_mode: bool = False) -> str:
    text = (raw or "").strip()
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1].strip()
    text = re.sub(r"(?is)<think>.*?</think>", "", text).strip()
    text = re.sub(r"(?is)^```json\s*", "", text)
    text = re.sub(r"(?is)\s*```$", "", text).strip()

    if json_mode:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        return match.group(0).strip() if match else text

    return text


def _heuristic_memory_payload(
    message: str,
    answer: str,
    specialists: List[EspecialistaLiquido],
) -> Dict[str, Any]:
    combined = f"{message}\n{answer}".lower()
    entities = []
    relations = []
    decisions = []
    open_loops = []

    known_entities = {
        "orquesta": ("orquesta cognitiva local", "Sistema"),
        "orquestador": ("nucleo orquestador", "Componente"),
        "memoria": ("memoria de grafos", "Componente"),
        "grafo": ("memoria de grafos", "Componente"),
        "arquitectura": ("arquitectura cognitiva", "Concepto"),
        "especialistas": ("especialistas liquidos", "Componente"),
        "visual": ("especialista visual de sistemas", "Rol"),
        "forense": ("forense cognitivo", "Rol"),
        "qa": ("capa operativa futura", "Frontera"),
        "iis": ("capa operativa futura", "Frontera"),
    }

    for trigger, (name, entity_type) in known_entities.items():
        if trigger in combined:
            entities.append(
                {
                    "name": name,
                    "type": entity_type,
                    "metadata": {"source": "heuristic"},
                }
            )

    for specialist in specialists:
        entities.append(
            {
                "name": specialist.nombre,
                "type": "Rol",
                "metadata": {"source": "route"},
            }
        )
        relations.append(
            {
                "source": "orquesta cognitiva local",
                "target": specialist.nombre,
                "type": "coordina",
                "metadata": {"source": "route"},
            }
        )

    if "proximo paso" in answer.lower() or "siguiente paso" in answer.lower():
        next_step = _extract_next_step(answer)
        if next_step:
            decisions.append(next_step)

    if "todavia no quiero" in message.lower() or "fase posterior" in message.lower():
        open_loops.append("definir la futura capa operativa sin activarla en la fase cognitiva")

    return {
        "summary": _first_meaningful_line(answer),
        "entities": _dedupe_entities(entities),
        "relations": relations,
        "decisions": decisions,
        "open_loops": open_loops,
    }


def _merge_memory_payload(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    primary_summary = primary.get("summary") or ""
    if _looks_like_json_blob(primary_summary):
        primary_summary = ""

    merged = {
        "summary": primary_summary or fallback.get("summary") or "Interaccion registrada.",
        "entities": [],
        "relations": [],
        "decisions": primary.get("decisions") or fallback.get("decisions") or [],
        "open_loops": primary.get("open_loops") or fallback.get("open_loops") or [],
    }

    merged["entities"] = _dedupe_entities(
        list(primary.get("entities") or []) + list(fallback.get("entities") or [])
    )
    merged["relations"] = list(primary.get("relations") or []) + list(fallback.get("relations") or [])
    if not merged["entities"]:
        merged["entities"] = fallback.get("entities") or []
    if not merged["relations"]:
        merged["relations"] = fallback.get("relations") or []
    return merged


def _dedupe_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    clean_entities = []
    for entity in entities:
        name = (entity.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        clean_entities.append(entity)
    return clean_entities


def _first_meaningful_line(answer: str) -> str:
    for line in answer.splitlines():
        clean = line.strip(" -*#:\t")
        if clean:
            return clean[:220]
    return answer[:220]


def _extract_next_step(answer: str) -> str:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if "proximo paso" in line.lower() or "siguiente paso" in line.lower():
            if index + 1 < len(lines):
                return lines[index + 1][:180]
            return line[:180]
    return ""


def _looks_like_json_blob(value: str) -> bool:
    text = (value or "").strip()
    return text.startswith("{") and ":" in text


director = DirectorOrquesta()
swarm = SwarmRuntime(
    chat_callable=director._chat,
    memory=director.memoria,
    director_model=director.model,
    model_base_url=DEFAULT_BASE_URL,
    model_plan=director.model_plan,
)
app = FastAPI(title="Orquesta Cognitiva Local", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    return {"service": "orquesta-cognitiva-local", "status": "ok"}


@app.get("/ui", response_class=HTMLResponse)
async def chat_ui() -> HTMLResponse:
    return HTMLResponse(CHAT_UI_PATH.read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "model": director.model,
        "models": director.model_plan,
        "memory": director.memoria.estadisticas(),
        "swarm_mode": swarm.model_mode,
    }


@app.get("/memory/search")
async def memory_search(q: str) -> Dict[str, Any]:
    result = director.memoria.buscar(q)
    return {
        "query": q,
        "nodes": result.nodes,
        "memories": result.memories,
        "relations": result.relations,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await director.responder(request.message, session_id=request.session_id)


@app.get("/swarm/bootstrap", response_model=SwarmBootstrapResponse)
async def swarm_bootstrap(session_id: str = "pixel-browser") -> SwarmBootstrapResponse:
    return SwarmBootstrapResponse(**swarm.bootstrap(session_id))


@app.post("/swarm/chat", response_model=SwarmChatResponse)
async def swarm_chat(request: SwarmChatRequest) -> SwarmChatResponse:
    payload = await swarm.chat(
        session_id=request.session_id,
        message=request.message,
        target_agent_id=request.target_agent_id,
    )
    return SwarmChatResponse(**payload)


async def _cli_chat(message: str, session_id: str) -> None:
    result = await director.responder(message, session_id=session_id)
    print(result.answer)
    print()
    print("Roles:", ", ".join(result.selected_specialists))
    print("Memoria:", result.memory_write)


def main() -> None:
    parser = argparse.ArgumentParser(description="Orquesta cognitiva local")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Levanta la API HTTP")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8310)

    chat_parser = subparsers.add_parser("chat", help="Envio unico por CLI")
    chat_parser.add_argument("message")
    chat_parser.add_argument("--session-id", default="principal")

    args = parser.parse_args()

    if args.command == "serve":
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return

    if args.command == "chat":
        asyncio.run(_cli_chat(args.message, args.session_id))


if __name__ == "__main__":
    main()
