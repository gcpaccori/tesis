import asyncio
import base64
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from typing import Any, Literal, TypedDict

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from langgraph.graph import END, StateGraph
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel, Field


KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "http://qa-kimi-q2-gpu:8021/v1").rstrip("/")
KIMI_MODEL = os.getenv("KIMI_MODEL", "kimi-k2.6-q2")
PHOENIX_OTLP_ENDPOINT = os.getenv("PHOENIX_OTLP_ENDPOINT", "http://qa-phoenix:6006/v1/traces")
LEARN_PATH = os.getenv("LEARN_PATH", "/data/learned.jsonl")
KIMI_PARALLEL = int(os.getenv("KIMI_PARALLEL", "2"))
kimi_gate = asyncio.Semaphore(KIMI_PARALLEL)
sandbox_stats = {"created": 0, "destroyed": 0, "active": 0, "execs": 0}

provider = TracerProvider(
    resource=Resource.create(
        {"service.name": "kimi-q2-noc-3d", "deployment.environment": "local-private"}
    )
)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=PHOENIX_OTLP_ENDPOINT)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("kimi-q2-noc-3d")


class ChatRequest(BaseModel):
    message: str
    mode: Literal["chat", "swarm", "qa"] = "swarm"
    max_tokens: int = Field(default=1024, ge=16, le=8192)
    planner_tokens: int = Field(default=4096, ge=300, le=8192)
    swarm_width: int = Field(default=2, ge=0, le=8)
    max_agents: int = Field(default=42, ge=1, le=300)
    run_sandbox_probe: bool = True
    repo_url: str | None = None
    image_url: str | None = None
    image_path: str | None = None


class AgentEvent(BaseModel):
    agent: str
    role: str
    duration_ms: int
    output: str


class ChatResponse(BaseModel):
    run_id: str
    model: str
    answer: str
    events: list[AgentEvent]
    sandbox: dict[str, Any] | None = None
    phoenix_url: str = "http://127.0.0.1:6006"


class SwarmState(TypedDict, total=False):
    run_id: str
    request: dict[str, Any]
    plan: dict[str, Any]
    events: list[dict[str, Any]]
    sandbox: dict[str, Any] | None
    learned: list[dict[str, Any]]
    answer: str


AGENTS: list[tuple[str, str, str, str]] = [
    ("director", "Director", "Jefe divergente", "Coordina, corta ruido y decide la ruta de QA."),
    ("arquitecto", "Arquitecto", "Mapa del sistema", "Relaciona repos, gateway, C#, datos y contratos."),
    ("datos", "Avatar de Datos", "120 bases", "Piensa en esquemas, tablas, llaves, migraciones y drift."),
    ("backend", "Backend C#", "Forjador API", "Evalua endpoints, NuGets, DAL, ruteo y reglas de negocio."),
    ("frontend", "Frontend", "Ojos UI", "Evalua rutas, builds, consumo API, validaciones y regresion visual."),
    ("seguridad", "Seguridad", "Tensionador", "Busca riesgos defensivos en auth, CORS, gateway e inputs."),
]

GRAPH_EDGES = [
    ("planner", "dynamic_swarm"),
    ("dynamic_swarm", "sandbox"),
    ("sandbox", "auditor"),
]


class LiveBus:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.replay: list[dict[str, Any]] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)
        for event in self.replay[-80:]:
            await ws.send_json(event)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def emit(self, event: str, **payload: Any) -> None:
        data = {"event": event, "ts": time.time(), **payload}
        self.replay.append(data)
        self.replay = self.replay[-240:]
        dead: list[WebSocket] = []
        for ws in list(self.clients):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


bus = LiveBus()
app = FastAPI(title="Kimi Q2 NOC 3D", version="0.2.0")


def image_part_from_path(path: str) -> dict[str, Any] | None:
    safe = os.path.abspath(path)
    allowed_roots = ["/data", "/tmp"]
    if not any(safe == root or safe.startswith(root + os.sep) for root in allowed_roots):
        return None
    if not os.path.isfile(safe):
        return None
    mime = mimetypes.guess_type(safe)[0] or "image/png"
    with open(safe, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}


def user_message(state: SwarmState, text: str) -> dict[str, Any]:
    req = state["request"]
    parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
    image_url = req.get("image_url")
    image_path = req.get("image_path")
    if image_url:
        parts.append({"type": "image_url", "image_url": {"url": str(image_url)}})
    elif image_path:
        part = image_part_from_path(str(image_path))
        if part:
            parts.append(part)
        else:
            parts[0]["text"] += f"\n\nImagen no disponible en el contenedor: {image_path}. Usa /data/images/... o image_url."
    return {"role": "user", "content": parts}


async def call_kimi(messages: list[dict[str, Any]], max_tokens: int = 1024) -> str:
    instant = "MODO INSTANTANEO. Responde contenido final directo, sin razonamiento largo, sin prologo y sin repetir la pregunta."
    prepared = [dict(message) for message in messages]
    if prepared and prepared[0].get("role") == "system":
        prepared[0]["content"] = instant + "\n" + str(prepared[0].get("content", ""))
    else:
        prepared.insert(0, {"role": "system", "content": instant})
    payload = {
        "model": KIMI_MODEL,
        "messages": prepared,
        "temperature": 0.2,
        "top_p": 0.92,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {"thinking": False, "preserve_thinking": False},
    }
    async with kimi_gate:
        async with httpx.AsyncClient(timeout=900) as client:
            response = await client.post(f"{KIMI_BASE_URL}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
    message = data["choices"][0]["message"]
    text = (message.get("content") or message.get("reasoning_content") or message.get("reasoning") or "").strip()
    return text.split("</think>", 1)[-1].strip() if "</think>" in text else text


def add_event(state: SwarmState, agent: str, role: str, start: float, output: str) -> None:
    state.setdefault("events", []).append(
        {"agent": agent, "role": role, "duration_ms": int((time.time() - start) * 1000), "output": output}
    )


def base_context(state: SwarmState) -> str:
    req = state["request"]
    repo = f"\nRepo objetivo: {req.get('repo_url')}" if req.get("repo_url") else ""
    recent = state.get("events", [])[-6:]
    failures = [
        f"- {e.get('agent')}: {str(e.get('output', ''))[:700].replace(chr(10), ' ')}"
        for e in state.get("events", [])
        if "console rc=" in str(e.get("output", "")) and "console rc=0" not in str(e.get("output", ""))
    ]
    previous = "\n".join(
        f"- {e.get('role', e.get('agent', 'agente'))}: {str(e.get('output', ''))[:500].replace(chr(10), ' ')}"
        for e in recent
    )
    failure_text = "\n\nFallas de consola obligatorias:\n" + "\n".join(failures) if failures else ""
    return f"Pedido:\n{req['message'][:1200]}{repo}\n\nMesa resumida:\n{previous or 'Sin eventos previos.'}{failure_text}"


async def learn(state: SwarmState, source: str, text: str, kind: str = "finding") -> None:
    item = {
        "ts": time.time(),
        "run_id": state["run_id"],
        "source": source,
        "kind": kind,
        "text": text[:1200],
    }
    state.setdefault("learned", []).append(item)
    os.makedirs(os.path.dirname(LEARN_PATH), exist_ok=True)
    with open(LEARN_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    await bus.emit("learn", **item)


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def role_commands(role: str) -> list[str]:
    role = role.lower()
    if "backend" in role or "c#" in role:
        return [
            "python - <<'PY'\nprint('scan backend: buscar .sln/.csproj, controllers, appsettings y paquetes NuGet')\nprint('warning: repo real no montado en este mini-entorno')\nPY"
        ]
    if "front" in role:
        return [
            "python - <<'PY'\nprint('scan frontend: buscar package.json, rutas, build script y consumo API')\nprint('warning: repo real no montado en este mini-entorno')\nPY"
        ]
    if "dato" in role or "db" in role:
        return [
            "python - <<'PY'\nprint('scan datos: validar columnas, llaves, migraciones y drift de esquema')\nprint('sample column: CodigoSuministro BIGINT NOT NULL')\nPY"
        ]
    if any(token in role for token in ["visual", "image", "imagen", "ocr", "object", "label"]):
        return [
            "python - <<'PY'\nimport pathlib\nimgs=sorted(pathlib.Path('images').glob('*')) if pathlib.Path('images').exists() else []\nprint('visual mini-env online')\nprint('images_detected=' + str(len(imgs)))\nprint('first_image=' + (str(imgs[0]) if imgs else 'none'))\nPY"
        ]
    if "seguridad" in role or "gateway" in role:
        return [
            "python - <<'PY'\nprint('scan seguridad/gateway: revisar CORS, JWT, headers y rutas expuestas')\nprint('no se ejecutan ataques; solo checks defensivos')\nPY"
        ]
    return ["python - <<'PY'\nprint('mini-env online')\nprint('checklist operativo generado')\nPY"]


def safe_commands(commands: Any, role: str) -> list[str]:
    raw = commands if isinstance(commands, list) else []
    deny = ["rm ", "sudo", "mkfs", "dd ", ":(){", "shutdown", "reboot", "curl http", "wget http", "nc ", "ncat", "ssh "]
    safe: list[str] = []
    for cmd in raw[:8]:
        cmd = str(cmd).strip()
        if not cmd or len(cmd) > 5000:
            continue
        low = cmd.lower()
        if any(token in low for token in deny):
            safe.append(f"python - <<'PY'\nprint('comando bloqueado por politica defensiva')\nprint({cmd!r})\nPY")
        else:
            safe.append(cmd)
    return safe or role_commands(role)


def forged_tool_script(agent_id: str, role: str, mission: str) -> str:
    payload = {
        "agent": agent_id,
        "role": role,
        "mission": mission[:1200],
    }
    encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    return f"""python - <<'PY'
import base64, json, pathlib, textwrap
payload = json.loads(base64.b64decode("{encoded}").decode("utf-8"))
tool_dir = pathlib.Path('tools')
tool_dir.mkdir(exist_ok=True)
pathlib.Path('tool_payload.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
tool_path = tool_dir / (payload['agent'] + '_tool.py')
tool_path.write_text(textwrap.dedent('''
    \"\"\"Herramienta efimera forjada por el agente.

    Lee tool_payload.json para evitar inyectar texto del planner dentro del
    codigo ejecutable. Asi la herramienta puede auditar misiones largas sin
    romper el heredoc ni la sintaxis de Python.
    \"\"\"
    import json
    import pathlib

    def run():
        payload = json.loads(pathlib.Path('tool_payload.json').read_text(encoding='utf-8'))
        evidence = {{
            "agent": payload.get("agent"),
            "role": payload.get("role"),
            "mission": payload.get("mission"),
            "checks": [
                "inventario defensivo",
                "extraccion de evidencia",
                "registro reproducible"
            ],
        }}
        pathlib.Path('evidence.json').write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
        print(json.dumps(evidence, ensure_ascii=False))

    if __name__ == "__main__":
        run()
''').strip() + '\\n', encoding='utf-8')
print('tool_forged=' + str(tool_path))
print(tool_path.read_text(encoding='utf-8')[:1200])
print('payload_saved=tool_payload.json')
PY"""


async def run_streaming_console(state: SwarmState, agent_id: str, parent: str | None, commands: list[str]) -> dict[str, Any]:
    env_id = f"mini-env-{agent_id[:14]}-{uuid.uuid4().hex[:5]}"
    root = tempfile.mkdtemp(prefix=f"{env_id}-")
    if os.path.isdir("/data/images"):
        try:
            os.symlink("/data/images", os.path.join(root, "images"))
        except FileExistsError:
            pass
    sandbox_stats["created"] += 1
    sandbox_stats["active"] += 1
    await bus.emit("env", run_id=state["run_id"], action="create", env_id=env_id, path=root, agent=agent_id, stats=dict(sandbox_stats))
    combined_stdout = ""
    combined_stderr = ""
    return_code = 0
    try:
        for idx, command in enumerate(commands, 1):
            script = os.path.join(root, f"cmd_{idx}.sh")
            with open(script, "w", encoding="utf-8") as f:
                f.write("set -e\n" + command + "\n")
            sandbox_stats["execs"] += 1
            await bus.emit(
                "exec",
                run_id=state["run_id"],
                agent=agent_id,
                parent=parent,
                command=f"bash {os.path.basename(script)}",
                text=command,
                env_id=env_id,
                stats=dict(sandbox_stats),
            )
            proc = await asyncio.create_subprocess_exec(
                "bash",
                script,
                cwd=root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            combined_stdout += out
            combined_stderr += err
            return_code = proc.returncode or 0
            await bus.emit("console", run_id=state["run_id"], agent=agent_id, parent=parent, env_id=env_id, stream="stdout", text=out[-3000:], return_code=return_code)
            if err:
                await bus.emit("console", run_id=state["run_id"], agent=agent_id, parent=parent, env_id=env_id, stream="stderr", text=err[-3000:], return_code=return_code)
            if return_code != 0:
                break
        return {"mode": "agent-mini-env", "env_id": env_id, "path": root, "return_code": return_code, "stdout": combined_stdout[-4000:], "stderr": combined_stderr[-4000:]}
    except Exception as exc:
        return {"mode": "agent-mini-env", "env_id": env_id, "path": root, "return_code": 124, "stdout": combined_stdout[-4000:], "stderr": f"{type(exc).__name__}: {exc}"}
    finally:
        shutil.rmtree(root, ignore_errors=True)
        sandbox_stats["destroyed"] += 1
        sandbox_stats["active"] = max(0, sandbox_stats["active"] - 1)
        await bus.emit("env", run_id=state["run_id"], action="destroy", env_id=env_id, path=root, agent=agent_id, stats=dict(sandbox_stats))


def text_plan(text: str, request: dict[str, Any]) -> dict[str, Any]:
    request_text = str(request.get("message", "")).lower()
    if any(token in request_text for token in ["imagen", "image", "etiquet", "label", "ocr", "visual"]):
        roles = ["intake_visual", "ocr_validator", "object_detector", "label_quality", "dataset_consistency", "visual_auditor"]
    else:
        roles = ["arquitectura", "datos", "backend", "frontend", "seguridad", "gateway", "qa_release", "memoria"]
    agents = []
    for i, role in enumerate(roles[: max(4, min(int(request.get("max_agents", 42)), len(roles)))]):
        agents.append(
            {
                "id": role,
                "role": role.replace("_", " ").title(),
                "parent": "planner" if i < 2 else agents[max(0, i - 2)]["id"],
                "wave": 1 + i // 2,
                "mission": f"cubrir el frente {role} con evidencia concreta y comandos seguros",
                "commands": role_commands(role),
            }
        )
    return {"strategy": "plan textual recuperado", "agents": agents}


def fallback_plan(request: dict[str, Any]) -> dict[str, Any]:
    width = max(1, min(int(request.get("swarm_width", 2)), 8))
    request_text = str(request.get("message", "")).lower()
    if any(token in request_text for token in ["imagen", "image", "etiquet", "label", "ocr", "visual"]):
        agents = [
            {"id": "intake_visual", "role": "Intake Visual", "parent": "planner", "wave": 1, "mission": "validar existencia, formato, dimensiones y carga de la imagen", "commands": role_commands("visual")},
            {"id": "ocr_validator", "role": "OCR Validator", "parent": "intake_visual", "wave": 2, "mission": "detectar si hay texto legible y registrar ausencia/presencia", "commands": role_commands("ocr")},
            {"id": "object_detector", "role": "Object Detector", "parent": "intake_visual", "wave": 2, "mission": "describir objetos, regiones y colores dominantes", "commands": role_commands("visual")},
            {"id": "label_quality", "role": "Label Quality", "parent": "object_detector", "wave": 3, "mission": "evaluar calidad, precision y utilidad de etiquetas", "commands": role_commands("qa")},
            {"id": "dataset_consistency", "role": "Dataset Consistency", "parent": "ocr_validator", "wave": 3, "mission": "comparar etiquetas entre agentes y detectar contradicciones", "commands": role_commands("datos")},
            {"id": "visual_auditor", "role": "Visual Auditor", "parent": "label_quality", "wave": 4, "mission": "consolidar resultado final de etiquetado y riesgos", "commands": role_commands("visual")},
        ]
        return {"strategy": "fallback visual multimodal", "agents": agents[: max(1, min(int(request.get("max_agents", 6)), len(agents)))]}
    agents: list[dict[str, Any]] = [
        {"id": "arquitectura", "role": "Arquitectura", "parent": "planner", "wave": 1, "mission": "mapear piezas y dependencias del QA", "commands": role_commands("arquitectura")},
        {"id": "datos", "role": "Datos", "parent": "planner", "wave": 1, "mission": "revisar esquemas, tablas, llaves y drift", "commands": role_commands("datos")},
        {"id": "backend", "role": "Backend C#", "parent": "arquitectura", "wave": 2, "mission": "verificar API, NuGets, DAL y ruteo", "commands": role_commands("backend")},
        {"id": "frontend", "role": "Frontend", "parent": "arquitectura", "wave": 2, "mission": "verificar UI, rutas, contratos visuales y build", "commands": role_commands("frontend")},
        {"id": "seguridad", "role": "Seguridad", "parent": "backend", "wave": 3, "mission": "tensionar gateway, auth, CORS e inputs", "commands": role_commands("seguridad")},
    ]
    for parent in ["backend", "frontend", "datos", "seguridad"]:
        for i in range(width):
            agents.append(
                {
                    "id": f"{parent}-micro-{i+1}",
                    "role": f"Micro {parent}",
                    "parent": parent,
                    "wave": 3 + i % 2,
                    "mission": f"hallar evidencia concreta para {parent}, variante {i+1}",
                    "commands": role_commands(parent),
                }
            )
    return {"strategy": "fallback dinamico local", "agents": agents}


async def planner_node(state: SwarmState) -> SwarmState:
    run_id = state["run_id"]
    req = state["request"]
    max_agents = int(req.get("max_agents", 42))
    await bus.emit(
        "spawn",
        run_id=run_id,
        agent="planner",
        role="Kimi Planner",
        title="cerebro libre",
        specialty="Decide agentes, padres, olas paralelas y misiones",
    )
    await bus.emit("status", run_id=run_id, agent="planner", status="planning")
    await bus.emit(
        "exec",
        run_id=run_id,
        agent="planner",
        command="kimi.plan.json",
        text=f"max_agents={max_agents}; pedido={req['message'][:500]}",
    )
    prompt = (
        f"Devuelve SOLO JSON minificado. Crea hasta {max_agents} agentes QA defensivos. "
        "Formato exacto: {\"strategy\":\"...\",\"agents\":[{\"id\":\"backend\",\"role\":\"Backend QA\","
        "\"parent\":\"planner\",\"wave\":1,\"mission\":\"...\",\"commands\":[\"python - <<'PY'\\nprint('ok')\\nPY\"]}]}. "
        "Reglas: ids ASCII, parent debe existir antes o ser planner, wave 1..8, comandos bash seguros sin red ni destruccion. "
        f"Pedido: {req['message'][:900]}. Repo: {req.get('repo_url') or 'no especificado'}."
    )
    start = time.time()
    with tracer.start_as_current_span("agent.planner") as span:
        try:
            raw = await call_kimi(
                [{"role": "system", "content": "MODO INSTANTANEO. Devuelve solo JSON valido. Sin markdown. Sin explicaciones."}, {"role": "user", "content": prompt}],
                max_tokens=int(req.get("planner_tokens", 4096)),
            )
            try:
                plan = extract_json(raw)
                if not isinstance(plan.get("agents"), list):
                    raise ValueError("plan.agents no es lista")
            except Exception:
                plan = text_plan(raw, req)
        except Exception as exc:
            raw = f"planner fallback por {type(exc).__name__}: {exc}"
            plan = fallback_plan(req)
        agents = plan.get("agents", [])[:max_agents]
        safe_agents: list[dict[str, Any]] = []
        known = {"planner"}
        for i, agent in enumerate(agents):
            agent_id = str(agent.get("id") or f"agent_{i+1}").lower().replace(" ", "_")[:48]
            parent = str(agent.get("parent") or "planner").lower().replace(" ", "_")[:48]
            if parent not in known:
                parent = "planner"
            item = {
                "id": agent_id,
                "role": str(agent.get("role") or agent_id)[:80],
                "parent": parent,
                "wave": max(1, min(int(agent.get("wave") or 1), 8)),
                "mission": str(agent.get("mission") or "analizar QA")[:700],
                "commands": safe_commands(agent.get("commands"), str(agent.get("role") or agent_id)),
            }
            safe_agents.append(item)
            known.add(agent_id)
        plan["agents"] = safe_agents
        state["plan"] = plan
        span.set_attribute("swarm.run_id", run_id)
        span.set_attribute("plan.agent_count", len(safe_agents))
        span.set_attribute("plan.strategy", str(plan.get("strategy", ""))[:500])
    add_event(state, "planner", "Kimi Planner", start, json.dumps(plan, ensure_ascii=False, indent=2))
    await learn(state, "planner", json.dumps(plan, ensure_ascii=False), kind="plan")
    await bus.emit("plan", run_id=run_id, plan=plan)
    await bus.emit("log", run_id=run_id, agent="planner", text=json.dumps(plan, ensure_ascii=False, indent=2), ms=int((time.time() - start) * 1000))
    await bus.emit("status", run_id=run_id, agent="planner", status="done")
    return state


async def dynamic_agent(state: SwarmState, spec: dict[str, Any]) -> dict[str, Any]:
    agent_id = spec["id"]
    role = spec["role"]
    parent = spec.get("parent", "planner")
    mission = spec["mission"]
    start = time.time()
    await bus.emit(
        "spawn",
        run_id=state["run_id"],
        agent=agent_id,
        role=role,
        title=f"wave {spec.get('wave', 1)}",
        specialty=mission,
        parent=parent,
    )
    await bus.emit("status", run_id=state["run_id"], agent=agent_id, status="thinking", parent=parent)
    await bus.emit(
        "exec",
        run_id=state["run_id"],
        agent=agent_id,
        parent=parent,
        command="kimi.agent.invoke",
        text=f"role={role}; parent={parent}; wave={spec.get('wave')}; mission={mission}",
    )
    with tracer.start_as_current_span(f"dynamic_agent.{agent_id}") as span:
        span.set_attribute("agent.id", agent_id)
        span.set_attribute("agent.parent", parent)
        span.set_attribute("agent.wave", int(spec.get("wave", 1)))
        output = await call_kimi(
            [
                {
                    "role": "system",
                    "content": (
                        f"Eres {role}, agente dinamico creado por Kimi. "
                        f"Mision: {mission}. "
                        "Responde en maximo 8 lineas: accion, evidencia, riesgo, comando/check. "
                        "No muestres cadena de pensamiento privada. Se directo."
                    ),
                },
                user_message(state, base_context(state)),
            ],
            max_tokens=int(state["request"].get("max_tokens", 1024)),
        )
        span.set_attribute("output.preview", output[:500])
    ms = int((time.time() - start) * 1000)
    await bus.emit("log", run_id=state["run_id"], agent=agent_id, text=output, ms=ms, parent=parent)
    await bus.emit("status", run_id=state["run_id"], agent=agent_id, status="console", parent=parent)
    agent_commands = [forged_tool_script(agent_id, role, mission)]
    agent_commands.extend(safe_commands(spec.get("commands"), role))
    console_result = await run_streaming_console(state, agent_id, parent, agent_commands)
    console_text = (
        f"console rc={console_result['return_code']} env={console_result.get('env_id')}\n"
        f"{console_result.get('stdout','')}{console_result.get('stderr','')}"
    )
    add_event(state, f"{agent_id}_console", f"{role} Console", start, console_text)
    await learn(state, f"{agent_id}_console", console_text, kind="console_result")
    await bus.emit("status", run_id=state["run_id"], agent=agent_id, status="done", parent=parent)
    await learn(state, agent_id, output, kind="dynamic_agent_finding")
    return {"agent": agent_id, "role": role, "duration_ms": ms, "output": output}


async def execute_dynamic_swarm_node(state: SwarmState) -> SwarmState:
    plan = state.get("plan") or fallback_plan(state["request"])
    agents = list(plan.get("agents", []))
    if not agents:
        return state
    await bus.emit(
        "spawn",
        run_id=state["run_id"],
        agent="dynamic_swarm",
        role="Dynamic Swarm",
        title="fan-out neuronal",
        specialty=f"{len(agents)} agentes planificados por Kimi",
        parent="planner",
    )
    await bus.emit("status", run_id=state["run_id"], agent="dynamic_swarm", status="routing", parent="planner")
    for spec in agents:
        await bus.emit(
            "planned_agent",
            run_id=state["run_id"],
            agent=spec["id"],
            parent=spec.get("parent", "planner"),
            role=spec.get("role", spec["id"]),
            wave=spec.get("wave", 1),
            mission=spec.get("mission", ""),
        )
    for wave in sorted({int(a.get("wave", 1)) for a in agents}):
        batch = [a for a in agents if int(a.get("wave", 1)) == wave]
        await bus.emit("wave", run_id=state["run_id"], wave=wave, count=len(batch), parallel_gate=KIMI_PARALLEL)
        results = await asyncio.gather(*(dynamic_agent(state, spec) for spec in batch))
        state.setdefault("events", []).extend(results)
    await bus.emit("status", run_id=state["run_id"], agent="dynamic_swarm", status="done", parent="planner")
    return state


async def assistant_worker(state: SwarmState, parent: str, role: str, idx: int, mission: str) -> dict[str, Any]:
    worker_id = f"{parent}-w{idx}"
    start = time.time()
    await bus.emit(
        "spawn",
        run_id=state["run_id"],
        agent=worker_id,
        role=f"{role} Â· ayudante {idx}",
        title="micro-especialista",
        specialty=mission,
        parent=parent,
    )
    await bus.emit("status", run_id=state["run_id"], agent=worker_id, status="thinking", parent=parent)
    await bus.emit(
        "exec",
        run_id=state["run_id"],
        agent=worker_id,
        parent=parent,
        command="kimi.chat.completions",
        text=f"prompt=ayudante de {role}; mission={mission}; max_tokens={min(1024, int(state['request'].get('max_tokens', 1024)))}",
    )
    with tracer.start_as_current_span(f"worker.{worker_id}") as span:
        span.set_attribute("worker.parent", parent)
        span.set_attribute("worker.index", idx)
        span.set_attribute("swarm.run_id", state["run_id"])
        output = await call_kimi(
            [
                {
                    "role": "system",
                    "content": (
                        f"Eres ayudante {idx} de {role}. Tu mision puntual: {mission}. "
                        "Responde en 3 bullets cortos: evidencia, riesgo, comando/check concreto."
                    ),
                },
                user_message(state, base_context(state)),
            ],
            max_tokens=min(1024, int(state["request"].get("max_tokens", 1024))),
        )
        span.set_attribute("output.preview", output[:500])
    ms = int((time.time() - start) * 1000)
    await bus.emit("log", run_id=state["run_id"], agent=worker_id, text=output, ms=ms, parent=parent)
    await bus.emit("status", run_id=state["run_id"], agent=worker_id, status="done", parent=parent)
    await learn(state, worker_id, output, kind="worker_finding")
    return {"agent": worker_id, "role": f"{role} ayudante {idx}", "duration_ms": ms, "output": output}


def agent_node(agent_id: str, role: str, title: str, specialty: str):
    async def run(state: SwarmState) -> SwarmState:
        start = time.time()
        run_id = state["run_id"]
        await bus.emit("spawn", run_id=run_id, agent=agent_id, role=role, title=title, specialty=specialty)
        await bus.emit("status", run_id=run_id, agent=agent_id, status="thinking")
        await bus.emit(
            "exec",
            run_id=run_id,
            agent=agent_id,
            command="kimi.chat.completions",
            text=f"role={role}; max_tokens={int(state['request'].get('max_tokens', 1024))}; parallel_gate={KIMI_PARALLEL}",
        )
        with tracer.start_as_current_span(f"agent.{agent_id}") as span:
            span.set_attribute("agent.id", agent_id)
            span.set_attribute("agent.role", role)
            span.set_attribute("swarm.run_id", run_id)
            prompt = (
                f"Eres {role} dentro del enjambre QA privado de Electro Sur.\n"
                f"Especialidad: {specialty}\n"
                "Habla como especialista real: evidencia, riesgo, accion, dependencia. "
                "No repitas estado vacio. Maximo 8 lineas. Si falta dato, pide el dato exacto."
            )
            output = await call_kimi(
                [{"role": "system", "content": prompt}, user_message(state, base_context(state))],
                max_tokens=int(state["request"].get("max_tokens", 1024)),
            )
            span.set_attribute("output.preview", output[:600])
            add_event(state, agent_id, role, start, output)
        await learn(state, agent_id, output, kind="agent_finding")
        await bus.emit("log", run_id=run_id, agent=agent_id, text=output, ms=int((time.time() - start) * 1000))
        width = int(state["request"].get("swarm_width", 2))
        missions = [
            f"buscar evidencia tecnica desde la perspectiva {role}",
            f"detectar riesgo oculto que {role} no debe pasar por alto",
            f"proponer check automatizable para QA Electro Sur",
            f"identificar dependencia bloqueante para continuar",
            f"resumir aprendizaje reutilizable para memoria corporativa",
            f"forjar herramienta minima o comando de verificacion",
            f"definir dato faltante exacto para reducir incertidumbre",
            f"contradecir al especialista si hay una falla en su plan",
        ][:width]
        if missions:
            await bus.emit("status", run_id=run_id, agent=agent_id, status=f"delegating:{width}")
            workers = await asyncio.gather(
                *(assistant_worker(state, agent_id, role, i + 1, mission) for i, mission in enumerate(missions))
            )
            state.setdefault("events", []).extend(workers)
        await bus.emit("status", run_id=run_id, agent=agent_id, status="done")
        return state

    return run


async def run_local_sandbox(command: str, run_id: str) -> dict[str, Any]:
    env_id = f"mini-env-{run_id[:8]}-{uuid.uuid4().hex[:5]}"
    root = tempfile.mkdtemp(prefix=f"{env_id}-")
    sandbox_stats["created"] += 1
    sandbox_stats["active"] += 1
    await bus.emit("env", run_id=run_id, action="create", env_id=env_id, path=root, stats=dict(sandbox_stats))
    try:
        script = os.path.join(root, "run.sh")
        with open(script, "w", encoding="utf-8") as f:
            f.write(command)
        sandbox_stats["execs"] += 1
        await bus.emit(
            "exec",
            run_id=run_id,
            agent="sandbox",
            command=f"bash {script}",
            text=command,
            env_id=env_id,
            stats=dict(sandbox_stats),
        )
        completed = subprocess.run(["bash", script], cwd=root, text=True, capture_output=True, timeout=120)
        return {
            "mode": "local-mini-env",
            "env_id": env_id,
            "path": root,
            "return_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)
        sandbox_stats["destroyed"] += 1
        sandbox_stats["active"] = max(0, sandbox_stats["active"] - 1)
        await bus.emit("env", run_id=run_id, action="destroy", env_id=env_id, path=root, stats=dict(sandbox_stats))


async def sandbox_node(state: SwarmState) -> SwarmState:
    if not state["request"].get("run_sandbox_probe", True):
        state["sandbox"] = None
        return state
    run_id = state["run_id"]
    start = time.time()
    await bus.emit("spawn", run_id=run_id, agent="sandbox", role="Sandbox", title="E2B local", specialty="Contenedor efimero sin red")
    await bus.emit("status", run_id=run_id, agent="sandbox", status="create")
    await asyncio.sleep(0.05)
    await bus.emit("status", run_id=run_id, agent="sandbox", status="exec")
    with tracer.start_as_current_span("tool.local_sandbox") as span:
        result = await run_local_sandbox("python - <<'PY'\nprint('sandbox-ok')\nprint(2 + 2)\nPY", run_id)
        span.set_attribute("swarm.run_id", run_id)
        span.set_attribute("sandbox.return_code", int(result.get("return_code", -1)))
    state["sandbox"] = result
    text = f"Sandbox {result['mode']} rc={result['return_code']}\\n{result.get('stdout','')}{result.get('stderr','')}"
    add_event(state, "sandbox", "Sandbox", start, text)
    await learn(state, "sandbox", text, kind="tool_result")
    await bus.emit("log", run_id=run_id, agent="sandbox", text=text, ms=int((time.time() - start) * 1000))
    await bus.emit("status", run_id=run_id, agent="sandbox", status="cleanup")
    await asyncio.sleep(0.05)
    await bus.emit("status", run_id=run_id, agent="sandbox", status="done")
    return state


async def auditor_node(state: SwarmState) -> SwarmState:
    start = time.time()
    run_id = state["run_id"]
    await bus.emit("spawn", run_id=run_id, agent="auditor", role="Auditor Final", title="Consolidacion", specialty="Cierra la mesa con hallazgos y proxima accion")
    await bus.emit("status", run_id=run_id, agent="auditor", status="thinking")
    with tracer.start_as_current_span("agent.auditor_final") as span:
        output = await call_kimi(
            [
                {"role": "system", "content": "Eres el Auditor/Jefe final. MODO INSTANTANEO. Consolida en menos de 18 lineas: estado, hallazgos, riesgos y siguiente paso."},
                user_message(state, base_context(state)),
            ],
            max_tokens=int(state["request"].get("max_tokens", 1024)),
        )
        span.set_attribute("swarm.run_id", run_id)
        span.set_attribute("output.preview", output[:600])
    state["answer"] = output
    add_event(state, "auditor", "Auditor Final", start, output)
    await learn(state, "auditor", output, kind="summary")
    await bus.emit("log", run_id=run_id, agent="auditor", text=output, ms=int((time.time() - start) * 1000))
    await bus.emit("status", run_id=run_id, agent="auditor", status="done")
    await bus.emit("complete", run_id=run_id, answer=output)
    return state


def build_graph():
    graph = StateGraph(SwarmState)
    graph.add_node("planner", planner_node)
    graph.add_node("dynamic_swarm", execute_dynamic_swarm_node)
    graph.add_node("sandbox_probe", sandbox_node)
    graph.add_node("auditor", auditor_node)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "dynamic_swarm")
    graph.add_edge("dynamic_swarm", "sandbox_probe")
    graph.add_edge("sandbox_probe", "auditor")
    graph.add_edge("auditor", END)
    return graph.compile()


compiled_graph = build_graph()


@app.websocket("/ws")
async def ws(ws: WebSocket) -> None:
    await bus.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        bus.disconnect(ws)


@app.get("/", response_class=HTMLResponse)
async def ui() -> str:
    return NOC_HTML


@app.get("/health")
async def health() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        kimi = await client.get(f"{KIMI_BASE_URL}/models")
    return {"ok": True, "model": KIMI_MODEL, "kimi_status": kimi.status_code, "phoenix": PHOENIX_OTLP_ENDPOINT}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    run_id = str(uuid.uuid4())
    await bus.emit("run", run_id=run_id, message=request.message, model=KIMI_MODEL)
    with tracer.start_as_current_span("swarm.request") as span:
        span.set_attribute("swarm.run_id", run_id)
        span.set_attribute("swarm.mode", request.mode)
        initial: SwarmState = {"run_id": run_id, "request": request.model_dump(), "events": [], "sandbox": None, "learned": [], "plan": {}}
        if request.mode == "chat":
            answer = await call_kimi([user_message(initial, request.message)], max_tokens=request.max_tokens)
            initial["answer"] = answer
            await bus.emit("complete", run_id=run_id, answer=answer)
        else:
            initial = await compiled_graph.ainvoke(initial)
        return ChatResponse(
            run_id=run_id,
            model=KIMI_MODEL,
            answer=initial.get("answer", ""),
            events=[AgentEvent(**event) for event in initial.get("events", [])],
            sandbox=initial.get("sandbox"),
        )


@app.get("/agents")
async def agents() -> dict[str, Any]:
    return {"capabilities": [{"id": a, "role": r, "title": t, "specialty": s} for a, r, t, s in AGENTS]}


@app.get("/graph")
async def graph() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "planner", "role": "Kimi Planner", "title": "cerebro libre", "specialty": "Genera plan dinamico JSON"},
            {"id": "dynamic_swarm", "role": "Dynamic Swarm", "title": "fan-out", "specialty": "Ejecuta olas paralelas decididas por Kimi"},
            {"id": "sandbox", "role": "Sandbox", "title": "Mini-entorno", "specialty": "Crea, ejecuta y destruye entornos efimeros"},
            {"id": "auditor", "role": "Auditor Final", "title": "Cierre", "specialty": "Consolida evidencia"},
        ],
        "edges": [{"source": s, "target": t} for s, t in GRAPH_EDGES],
        "capabilities": [{"id": a, "role": r, "title": t, "specialty": s} for a, r, t, s in AGENTS],
        "kimi_parallel_gate": KIMI_PARALLEL,
        "sandbox_stats": sandbox_stats,
    }


@app.get("/memory")
async def memory(limit: int = 80) -> dict[str, Any]:
    if not os.path.exists(LEARN_PATH):
        return {"items": []}
    with open(LEARN_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]
    return {"items": [json.loads(line) for line in lines if line.strip()]}


NOC_HTML = r"""
<!doctype html><html lang="es"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Kimi NOC 3D</title>
<style>
:root{--bg:#06100d;--ink:#eafff5;--muted:#86a396;--line:#24453a;--ok:#77ff9d;--run:#ffd36a;--bad:#ff6b7a;--cyan:#74e6ff}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:radial-gradient(circle at 20% 10%,#173e34,transparent 32rem),radial-gradient(circle at 80% 70%,#1b2845,transparent 36rem),#040807;font-family:Verdana,system-ui,sans-serif;overflow:hidden;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}
button,textarea,input,select{font:inherit}#app{height:100vh;display:grid;grid-template-columns:360px 1fr 390px;gap:14px;padding:14px}
.panel{border:1px solid #31564a;background:linear-gradient(180deg,rgba(15,32,28,.92),rgba(5,12,11,.86));backdrop-filter:blur(5px);border-radius:24px;box-shadow:0 30px 90px #0008;overflow:hidden}
.left,.right{padding:16px;display:flex;flex-direction:column;min-height:0}h1{font-size:25px;line-height:1;margin:0 0 8px;letter-spacing:-1px}.sub{color:var(--muted);font-size:13px;line-height:1.45}
textarea{width:100%;height:180px;margin:16px 0 10px;padding:13px;border:1px solid var(--line);border-radius:16px;color:var(--ink);background:#020706cc;resize:none;outline:none}
input,select{width:100%;padding:10px;margin:6px 0 10px;border:1px solid var(--line);border-radius:12px;color:var(--ink);background:#020706cc}
button{width:100%;padding:13px;border:0;border-radius:16px;color:#00140a;font-weight:900;background:linear-gradient(135deg,#8cffb1,#4ee1ff);cursor:pointer}button:disabled{opacity:.45;cursor:wait}
.pill{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:999px;padding:7px 10px;margin:6px 6px 6px 0;background:#06130fcc;color:var(--muted);font-size:12px}.dot{width:9px;height:9px;border-radius:9px;background:var(--ok);box-shadow:0 0 18px var(--ok)}
.stage{position:relative;perspective:900px;overflow:hidden}.grid{position:absolute;inset:auto -20% -12% -20%;height:58%;background:linear-gradient(#2df0aa22 1px,transparent 1px),linear-gradient(90deg,#2df0aa22 1px,transparent 1px);background-size:42px 42px;transform:rotateX(62deg);filter:drop-shadow(0 0 18px #3cffb155)}
#links{position:absolute;inset:0;width:100%;height:100%;opacity:.65}.node{position:absolute;width:130px;height:130px;margin:-65px;border-radius:50%;display:grid;place-items:center;transform-style:preserve-3d;transition:left .8s,top .8s,filter .25s,opacity .25s;filter:drop-shadow(0 0 13px #74e6ff88)}
.node{cursor:pointer}.node.selected{filter:drop-shadow(0 0 34px #fff)}.node.selected .tag{border-color:#9dffe2;box-shadow:0 0 25px #74e6ff66}
.orb{width:58px;height:58px;border-radius:50%;background:radial-gradient(circle at 30% 25%,#fff,#93ffe0 18%,#0bcf95 43%,#06392e 72%);box-shadow:0 0 26px #5dffd2, inset -12px -18px 24px #001b;animation:float 3.2s ease-in-out infinite}
.node.thinking .orb{background:radial-gradient(circle at 30% 25%,#fff,#ffe7a1 18%,#ffae34 48%,#422300 75%);box-shadow:0 0 36px #ffd36a;animation:pulse .75s infinite}
.node.done .orb{background:radial-gradient(circle at 30% 25%,#fff,#a8ffbf 20%,#23d45d 52%,#073715 78%);box-shadow:0 0 20px #77ff9d88}.node.helper.done{opacity:.46;filter:none}.node.helper.done .orb{background:radial-gradient(circle at 30% 25%,#dce8e2,#7f988f 35%,#263832 75%);box-shadow:none;animation:none}.node.error .orb{background:radial-gradient(circle at 30% 25%,#fff,#ffb0b8 18%,#ff3f56 52%,#3b050c 78%)}
.tag{position:absolute;top:84px;left:50%;transform:translateX(-50%);min-width:155px;text-align:center;border:1px solid #8cffb144;border-radius:13px;background:#06130ff2;padding:7px 9px;font-size:12px;box-shadow:0 10px 24px #000b}.tag b{display:block;color:#fff}.tag span{color:#b4d9ca;font-size:11px}
.agentStats{position:absolute;top:53px;left:50%;transform:translateX(-50%);display:flex;gap:4px;align-items:center;justify-content:center;min-width:148px;font:10px/1 Consolas,monospace;color:#eafff5;text-shadow:0 1px 2px #000}.agentStats span{padding:4px 6px;border:1px solid #ffffff24;border-radius:999px;background:#020907e8}.agentStats .ok{color:#7dff9b;border-color:#7dff9b88}.agentStats .fail{color:#ff6b7a;border-color:#ff6b7a88}.agentStats .open{color:#ffd36a;border-color:#ffd36a88}
.miniTerm{position:absolute;left:92px;top:-4px;width:210px;max-height:88px;overflow:hidden;margin:0;padding:9px;border:1px solid #76ffd566;border-radius:12px;background:#03100df2;color:#d7ffe8;font:10.5px/1.3 Consolas,monospace;opacity:.96;box-shadow:0 12px 26px #000b;white-space:pre-wrap}
.node.helper .miniTerm{display:none}.node.thinking .miniTerm{display:block}
.consoleBadge{position:absolute;right:9px;top:9px;width:28px;height:22px;border-radius:7px;border:1px solid #ffffff33;background:#020907;display:none;place-items:center;font:15px/1 Consolas,monospace;box-shadow:0 0 18px #000}.consoleBadge.ok{display:grid;color:#7dff9b;border-color:#7dff9b99;box-shadow:0 0 24px #7dff9b55}.consoleBadge.fail{display:grid;color:#ff6b7a;border-color:#ff6b7a99;box-shadow:0 0 24px #ff6b7a55}
.inspector{position:absolute;left:18px;right:18px;bottom:18px;min-height:180px;max-height:38%;display:grid;grid-template-columns:260px 1fr;gap:12px;padding:14px;border:1px solid #7dffd84a;border-radius:22px;background:linear-gradient(180deg,rgba(3,12,10,.94),rgba(4,24,20,.9));backdrop-filter:blur(4px);box-shadow:0 25px 80px #000a;z-index:4}
.inspector h3{margin:0 0 8px;color:#8cffb1;font-size:15px}.inspector .kv{font:12px/1.6 Consolas,monospace;color:#bfe8d8}.inspector pre{margin:0;max-height:230px;overflow:auto;white-space:pre-wrap;color:#d9fff1;font:12px/1.42 Consolas,monospace;background:#020907cc;border:1px solid #31564a;border-radius:14px;padding:12px}
.finalFlash{position:absolute;top:18px;left:50%;transform:translateX(-50%);z-index:5;max-width:70%;padding:10px 14px;border:1px solid #8cffb155;border-radius:999px;background:#04120ee8;color:#cbffe1;font:12px Consolas,monospace;box-shadow:0 0 32px #77ff9d55;display:none}
@keyframes float{50%{transform:translateY(-10px) rotateY(18deg)}}@keyframes pulse{50%{transform:scale(1.12);filter:brightness(1.25)}}
.right h2{font-size:13px;color:#8cffb1;margin:0 0 10px}.feed{min-height:0;overflow:auto;display:flex;flex-direction:column;gap:10px}.card{border:1px solid #31564a;border-radius:18px;background:#06130fc9;padding:12px;box-shadow:0 12px 35px #0005;cursor:pointer}.card .meta{color:var(--cyan);font-size:12px;margin-bottom:8px}.card pre{margin:0;white-space:pre-wrap;color:#daf8ec;font:12px/1.42 Consolas,monospace;max-height:190px;overflow:auto}.card.collapsed pre{max-height:48px;mask-image:linear-gradient(#000 55%,transparent)}
.answer{margin-top:12px;min-height:120px;max-height:220px;overflow:auto}.timeline{margin-top:12px;padding-top:12px;border-top:1px solid var(--line);font:12px/1.5 Consolas,monospace;color:#b7d9ca;overflow:auto;max-height:180px}
a{color:#86f7ff}.tiny{font-size:11px;color:var(--muted)}@media(max-width:1050px){#app{grid-template-columns:1fr}.stage{height:55vh}.right{min-height:40vh}}
</style></head><body><div id="app">
<aside class="panel left"><h1>Kimi NOC 3D</h1><div class="sub">Visor local del enjambre: agentes, consola viva, sandbox y auditor. Sin CDN, sin cloud UI obligatoria.</div>
<div><span class="pill"><i class="dot"></i><span id="health">verificando...</span></span><span class="pill" id="runid">sin corrida</span><span class="pill" id="envstats">envs 0/0</span><span class="pill" id="parallel">parallel ?</span></div>
<textarea id="message">Activa el enjambre QA para Electro Sur: revisa backend C#, frontend, gateway, datos y seguridad. Muestra que hizo cada especialista.</textarea>
<label class="tiny">Modo</label><select id="mode"><option value="swarm">swarm</option><option value="qa">qa</option><option value="chat">chat directo</option></select>
<label class="tiny">Tokens por agente</label><input id="max_tokens" type="number" min="16" max="8192" value="1024"/>
<label class="tiny">Tokens para que Kimi planifique el enjambre</label><input id="planner_tokens" type="number" min="300" max="8192" value="4096"/>
<label class="tiny">Fallback width si Kimi no devuelve plan</label><input id="swarm_width" type="number" min="0" max="8" value="2"/>
<label class="tiny">Max agentes que Kimi puede crear</label><input id="max_agents" type="number" min="1" max="300" value="42"/>
<label class="tiny">Repo opcional</label><input id="repo_url" placeholder="https://github.com/empresa/repo.git"/>
<label class="tiny">Imagen URL opcional</label><input id="image_url" placeholder="https://.../imagen.jpg"/>
<label class="tiny">Imagen path remoto opcional</label><input id="image_path" placeholder="/data/images/medidor_001.jpg"/>
<button id="run">Lanzar enjambre</button>
<div class="timeline" id="timeline"></div>
</aside>
<main class="panel stage"><svg id="links"></svg><div class="grid"></div><div id="space"></div><div class="finalFlash" id="finalFlash"></div><div class="inspector" id="inspector"><div><h3 id="insTitle">Selecciona un agente</h3><div class="kv" id="insMeta">click en una pelota para ver estado, comandos y mini-entornos.</div></div><pre id="insLog">Sin agente seleccionado.</pre></div></main>
<aside class="panel right"><h2>Consolas vivas</h2><div class="feed" id="feed"></div><div class="card answer"><div class="meta">Auditor final</div><pre id="answer">Esperando corrida.</pre></div><div class="card answer"><div class="meta">Memoria aprendida</div><pre id="memory">Sin aprendizajes todavia.</pre></div><div class="tiny">Phoenix: <a href="http://127.0.0.1:6006" target="_blank">http://127.0.0.1:6006</a> Â· Studio: <a href="https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024" target="_blank">LangGraph Studio</a></div></aside>
</div><script>
const $=id=>document.getElementById(id), agents={}, feed=$('feed'), space=$('space'), links=$('links'), timeline=$('timeline');
let graphEdges=[], typingQueues={};
const palette=['#72ffd4','#ffd36a','#8aa7ff','#ff8fb1','#91ff78','#74e6ff','#f7ff7a','#c99cff'];
function line(s){const d=document.createElement('div');d.textContent=new Date().toLocaleTimeString()+'  '+s;timeline.prepend(d)}
function pos(i,n){const w=space.parentElement.clientWidth,h=space.parentElement.clientHeight,cx=w/2,cy=h/2,r=Math.min(w,h)*.34,a=(i/n)*Math.PI*2-Math.PI/2;return{x:cx+Math.cos(a)*r,y:cy+Math.sin(a)*r*.72}}
function place(){const roots=Object.keys(agents).filter(id=>!agents[id].parent), n=Math.max(roots.length,1);roots.forEach((id,i)=>{const p=id==='director'?{x:space.parentElement.clientWidth/2,y:space.parentElement.clientHeight*.24}:pos(i,n);agents[id].el.style.left=p.x+'px';agents[id].el.style.top=p.y+'px';agents[id].p=p});Object.keys(agents).filter(id=>agents[id].parent).forEach((id,i)=>{const par=agents[agents[id].parent], kids=Object.keys(agents).filter(k=>agents[k].parent===agents[id].parent), idx=kids.indexOf(id), a=(idx/kids.length)*Math.PI*2, p=par?.p||pos(i,1), r=82;agents[id].el.style.left=(p.x+Math.cos(a)*r)+'px';agents[id].el.style.top=(p.y+Math.sin(a)*r*.72)+'px';agents[id].p={x:p.x+Math.cos(a)*r,y:p.y+Math.sin(a)*r*.72};agents[id].el.style.transform='scale(.66)'});drawLinks()}
function drawOne(a,b,color,dash='7 8',width='1.5'){if(!a||!b)return;const l=document.createElementNS('http://www.w3.org/2000/svg','line');l.setAttribute('x1',a.x);l.setAttribute('y1',a.y);l.setAttribute('x2',b.x);l.setAttribute('y2',b.y);l.setAttribute('stroke',color);l.setAttribute('stroke-width',width);l.setAttribute('stroke-dasharray',dash);links.appendChild(l)}
function drawLinks(){links.innerHTML='';graphEdges.forEach(e=>{if(agents[e.source]&&agents[e.target])drawOne(agents[e.source].p,agents[e.target].p,agents[e.target].color)});Object.keys(agents).filter(id=>agents[id].parent).forEach(id=>{const p=agents[id].parent;if(agents[p])drawOne(agents[p].p,agents[id].p,agents[id].color,'2 6','1')})}
function card(id,role){let c=document.getElementById('card-'+id);if(c)return c.querySelector('pre');c=document.createElement('div');c.className='card collapsed';c.id='card-'+id;c.innerHTML=`<div class="meta">${role} Â· ${id} Â· click para expandir</div><pre></pre>`;c.onclick=()=>c.classList.toggle('collapsed');feed.prepend(c);return c.querySelector('pre')}
function spawn(e){if(agents[e.agent])return;const color=palette[Object.keys(agents).length%palette.length],el=document.createElement('div');el.className='node thinking'+(e.parent?' helper':'');el.innerHTML=`<div class="orb"></div><div class="tag"><b>${e.role}</b><span>${e.title||e.specialty||e.agent}</span></div>`;space.appendChild(el);agents[e.agent]={el,color,role:e.role,logs:'',parent:e.parent};card(e.agent,e.role).textContent=`nace: ${e.specialty||'online'}\\n`;line('spawn '+e.agent+(e.parent?' bajo '+e.parent:''));place()}
function status(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:e.status});const el=agents[e.agent].el;el.classList.remove('thinking','done','error');el.classList.add(e.status==='done'?'done':e.status==='error'?'error':'thinking');line(e.agent+' -> '+e.status)}
function typeAppend(id,txt){const a=agents[id],pre=card(id,a?.role||id);typingQueues[id]=(typingQueues[id]||Promise.resolve()).then(()=>new Promise(res=>{let i=0;const tick=()=>{pre.textContent+=txt.slice(i,i+12);i+=12;pre.scrollTop=pre.scrollHeight;if(i<txt.length)setTimeout(tick,12);else res()};tick()}))}
function log(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:'evento'});line('log '+e.agent);typeAppend(e.agent,`\\n[${e.ms||0}ms] ${e.text}\\n`)}
function exec(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:'exec',parent:e.parent});line('exec '+e.agent+' $ '+e.command);typeAppend(e.agent,`\\n$ ${e.command}\\n${e.text||''}\\n`);if(e.stats)envstats(e.stats)}
function consoleEvent(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:'console',parent:e.parent});const label=e.stream==='stderr'?'STDERR':'STDOUT';line(label.toLowerCase()+' '+e.agent+' rc '+e.return_code);typeAppend(e.agent,`\\n[${label} env=${e.env_id} rc=${e.return_code}]\\n${e.text||''}\\n`)}
function envstats(s){$('envstats').textContent=`envs ${s.active} vivos Â· ${s.created} creados Â· ${s.destroyed} destruidos Â· ${s.execs} exec`}
function complete(e){$('answer').textContent=e.answer||'(sin respuesta)';$('runid').textContent=e.run_id;line('complete '+e.run_id)}
function learn(e){const m=$('memory');m.textContent=(`[${e.kind}] ${e.source}\\n${e.text}\\n\\n`+m.textContent).slice(0,5000);line('learn '+e.source)}
function plan(e){line('plan '+(e.plan?.agents?.length||0)+' agentes');typeAppend('planner','\\nPLAN JSON\\n'+JSON.stringify(e.plan,null,2)+'\\n')}
function planned(e){line('planned '+e.agent+' wave '+e.wave); if(!agents[e.agent])spawn({agent:e.agent,role:e.role,title:'planificado wave '+e.wave,specialty:e.mission,parent:e.parent})}
function wave(e){line('wave '+e.wave+' Â· '+e.count+' agentes Â· gate '+e.parallel_gate)}
function handle(e){if(e.event==='run'){$('runid').textContent=e.run_id;line('run '+e.run_id)} if(e.event==='spawn')spawn(e); if(e.event==='status')status(e); if(e.event==='exec')exec(e); if(e.event==='console')consoleEvent(e); if(e.event==='env'){envstats(e.stats);line('env '+e.action+' '+e.env_id)} if(e.event==='plan')plan(e); if(e.event==='planned_agent')planned(e); if(e.event==='wave')wave(e); if(e.event==='log')log(e); if(e.event==='learn')learn(e); if(e.event==='complete')complete(e)}
function ws(){const proto=location.protocol==='https:'?'wss':'ws',s=new WebSocket(`${proto}://${location.host}/ws`);s.onmessage=m=>handle(JSON.parse(m.data));s.onclose=()=>setTimeout(ws,1200)} ws(); addEventListener('resize',place);
async function health(){try{const j=await(await fetch('/health')).json();$('health').textContent=`${j.model} Â· kimi ${j.kimi_status}`}catch{$('health').textContent='sin conexion'}} health();
async function graph(){try{const j=await(await fetch('/graph')).json();graphEdges=j.edges||[];$('parallel').textContent=`Kimi gate ${j.kimi_parallel_gate}`;envstats(j.sandbox_stats||{active:0,created:0,destroyed:0,execs:0});place()}catch{}} graph();
async function loadMemory(){try{const j=await(await fetch('/memory?limit=12')).json();$('memory').textContent=(j.items||[]).reverse().map(x=>`[${x.kind}] ${x.source}\\n${x.text}`).join('\\n\\n')||'Sin aprendizajes todavia.'}catch{}}
$('run').onclick=async()=>{Object.values(agents).forEach(a=>a.el.remove());Object.keys(agents).forEach(k=>delete agents[k]);feed.innerHTML='';timeline.innerHTML='';$('answer').textContent='Kimi esta planificando el enjambre libre...';$('run').disabled=true;try{const body={message:$('message').value,mode:$('mode').value,max_tokens:+$('max_tokens').value||1024,planner_tokens:+$('planner_tokens').value||4096,swarm_width:+$('swarm_width').value||0,max_agents:+$('max_agents').value||42,run_sandbox_probe:true,repo_url:$('repo_url').value||null,image_url:$('image_url').value||null,image_path:$('image_path').value||null};const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw Error(JSON.stringify(j));$('answer').textContent=j.answer||'(sin respuesta)';loadMemory()}catch(e){$('answer').textContent='ERROR '+e.message}finally{$('run').disabled=false}};
loadMemory();
// Visual override: inspector, wave layout, per-agent terminals and clickable nodes.
var selected = null;
function levelOf(id){if(id==='planner')return 0;if(id==='dynamic_swarm')return 1;if(id==='sandbox')return 6;if(id==='auditor')return 7;return Number(agents[id]?.wave||3)}
function place(){const w=space.parentElement.clientWidth,h=space.parentElement.clientHeight,ids=Object.keys(agents),groups={};ids.forEach(id=>{const l=levelOf(id);(groups[l]=groups[l]||[]).push(id)});Object.keys(groups).sort((a,b)=>a-b).forEach(l=>{const group=groups[l],y=Math.min(h-250,Math.max(82,h*(.12+Number(l)*.1)));group.forEach((id,i)=>{const gap=w/(group.length+1),x=gap*(i+1);agents[id].el.style.left=x+'px';agents[id].el.style.top=y+'px';agents[id].p={x,y};agents[id].el.style.transform=agents[id].parent?'scale(.72)':'scale(1)'})});drawLinks();updateInspector()}
function card(id,role){let c=document.getElementById('card-'+id);if(c)return c.querySelector('pre');c=document.createElement('div');c.className='card collapsed';c.id='card-'+id;c.innerHTML=`<div class="meta">${role} Â· ${id} Â· click para expandir</div><pre></pre>`;c.onclick=()=>{c.classList.toggle('collapsed');selectAgent(id)};feed.prepend(c);return c.querySelector('pre')}
function hideInspector(){$('inspector').style.display='none';Object.values(agents).forEach(a=>a.el.classList.remove('selected'));selected=null}
function selectAgent(id){if(!agents[id])return;if(selected===id){hideInspector();return}selected=id;$('inspector').style.display='grid';Object.values(agents).forEach(a=>a.el.classList.remove('selected'));agents[id].el.classList.add('selected');updateInspector()}
function updateInspector(){if(!selected||!agents[selected])return;const a=agents[selected];$('insTitle').textContent=`${a.role} Â· ${selected}`;$('insMeta').innerHTML=`estado=${a.status||'n/a'}<br>parent=${a.parent||'root'}<br>wave=${a.wave||'-'}<br>envs=${(a.envs||[]).join(', ')||'-'}<br>tools=${(a.tools||[]).join(', ')||'-'}`;$('insLog').textContent=(a.logs||'Sin logs aun.').slice(-14000)}
function spawn(e){if(agents[e.agent]){Object.assign(agents[e.agent],{parent:e.parent??agents[e.agent].parent,wave:e.wave??agents[e.agent].wave});place();return}const color=palette[Object.keys(agents).length%palette.length],el=document.createElement('div');el.className='node thinking'+(e.parent?' helper':'');el.innerHTML=`<div class="orb"></div><div class="consoleBadge">â–¡</div><pre class="miniTerm"></pre><div class="tag"><b>${e.role}</b><span>${e.title||e.specialty||e.agent}</span></div>`;el.onclick=(ev)=>{ev.stopPropagation();selectAgent(e.agent)};space.appendChild(el);agents[e.agent]={el,color,role:e.role,logs:`nace: ${e.specialty||'online'}\n`,parent:e.parent,wave:e.wave,status:'spawn',tools:[],envs:[],console:'none'};card(e.agent,e.role).textContent=agents[e.agent].logs;line('spawn '+e.agent+(e.parent?' bajo '+e.parent:''));if(!selected)selectAgent(e.agent);place()}
function status(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:e.status});const a=agents[e.agent],el=a.el;a.status=e.status;el.classList.remove('thinking','done','error');el.classList.add(e.status==='done'?'done':e.status==='error'?'error':'thinking');line(e.agent+' -> '+e.status);updateInspector()}
function typeAppend(id,txt){const a=agents[id],pre=card(id,a?.role||id);if(a){a.logs=(a.logs||'')+txt;const mini=a.el.querySelector('.miniTerm');if(mini)mini.textContent=a.logs.slice(-280);updateInspector()}typingQueues[id]=(typingQueues[id]||Promise.resolve()).then(()=>new Promise(res=>{let i=0;const tick=()=>{pre.textContent+=txt.slice(i,i+18);i+=18;pre.scrollTop=pre.scrollHeight;if(i<txt.length)setTimeout(tick,10);else res()};tick()}))}
function exec(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:'exec',parent:e.parent});agents[e.agent].tools.push(e.command);line('exec '+e.agent+' $ '+e.command);typeAppend(e.agent,`\\n$ ${e.command}\\n${e.text||''}\\n`);if(e.stats)envstats(e.stats)}
function consoleEvent(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:'console',parent:e.parent});const label=e.stream==='stderr'?'STDERR':'STDOUT';const a=agents[e.agent],b=a.el.querySelector('.consoleBadge');a.console=e.return_code===0?'ok':'fail';b.classList.remove('ok','fail');b.classList.add(a.console);b.textContent=e.return_code===0?'âœ“':'Ã—';line(label.toLowerCase()+' '+e.agent+' rc '+e.return_code);typeAppend(e.agent,`\\n[${label} env=${e.env_id} rc=${e.return_code}]\\n${e.text||''}\\n`)}
function complete(e){$('answer').textContent=e.answer||'(sin respuesta)';$('runid').textContent=e.run_id;$('finalFlash').style.display='block';$('finalFlash').textContent='Resultado final listo Â· click Auditor Final o panel derecho';setTimeout(()=>$('finalFlash').style.display='none',9000);line('complete '+e.run_id);if(agents.auditor)selectAgent('auditor')}
function planned(e){line('planned '+e.agent+' wave '+e.wave);if(!agents[e.agent])spawn({agent:e.agent,role:e.role,title:'planificado wave '+e.wave,specialty:e.mission,parent:e.parent,wave:e.wave});else agents[e.agent].wave=e.wave;place()}
function handle(e){if(e.event==='run'){$('runid').textContent=e.run_id;line('run '+e.run_id)} if(e.event==='spawn')spawn(e); if(e.event==='status')status(e); if(e.event==='exec')exec(e); if(e.event==='console')consoleEvent(e); if(e.event==='env'){envstats(e.stats);if(e.agent&&agents[e.agent]&&e.env_id&&!agents[e.agent].envs.includes(e.env_id))agents[e.agent].envs.push(e.env_id);line('env '+e.action+' '+e.env_id);updateInspector()} if(e.event==='plan')plan(e); if(e.event==='planned_agent')planned(e); if(e.event==='wave')wave(e); if(e.event==='log')log(e); if(e.event==='learn')learn(e); if(e.event==='complete')complete(e)}
// Crisp telemetry override: every node shows terminal status, tools executed and mini-envs.
function updateInspector(){if(!selected||!agents[selected])return;const a=agents[selected];$('insTitle').textContent=`${a.role} Â· ${selected}`;$('insMeta').innerHTML=`estado=${a.status||'n/a'}<br>parent=${a.parent||'root'}<br>wave=${a.wave||'-'}<br>terminal=${a.console||'none'}<br>envs=${(a.envs||[]).join(', ')||'-'}<br>tools=${(a.tools||[]).join('<br>')||'-'}`;$('insLog').textContent=(a.logs||'Sin logs aun.').slice(-18000)}
function refreshNodeStats(id){const a=agents[id];if(!a)return;const stats=a.el.querySelector('.agentStats');if(!stats)return;const term=a.console==='ok'?'term OK':a.console==='fail'?'term X':a.status==='console'?'term ...':'term -';const cls=a.console==='ok'?'ok':a.console==='fail'?'fail':a.status==='console'?'open':'';stats.innerHTML=`<span class="${cls}">${term}</span><span>${(a.tools||[]).length} tools</span><span>${(a.envs||[]).length} env</span>`}
function spawn(e){if(agents[e.agent]){Object.assign(agents[e.agent],{parent:e.parent??agents[e.agent].parent,wave:e.wave??agents[e.agent].wave});refreshNodeStats(e.agent);place();return}const color=palette[Object.keys(agents).length%palette.length],el=document.createElement('div');el.className='node thinking'+(e.parent?' helper':'');el.innerHTML=`<div class="orb"></div><div class="consoleBadge">â–¡</div><div class="agentStats"><span>term -</span><span>0 tools</span><span>0 env</span></div><pre class="miniTerm"></pre><div class="tag"><b>${e.role}</b><span>${e.title||e.specialty||e.agent}</span></div>`;el.onclick=(ev)=>{ev.stopPropagation();selectAgent(e.agent)};space.appendChild(el);agents[e.agent]={el,color,role:e.role,logs:`nace: ${e.specialty||'online'}\n`,parent:e.parent,wave:e.wave,status:'spawn',tools:[],envs:[],console:'none'};card(e.agent,e.role).textContent=agents[e.agent].logs;refreshNodeStats(e.agent);line('spawn '+e.agent+(e.parent?' bajo '+e.parent:''));if(!selected)selectAgent(e.agent);place()}
function status(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:e.status});const a=agents[e.agent],el=a.el;a.status=e.status;el.classList.remove('thinking','done','error');el.classList.add(e.status==='done'?'done':e.status==='error'?'error':'thinking');refreshNodeStats(e.agent);line(e.agent+' -> '+e.status);updateInspector()}
function typeAppend(id,txt){const a=agents[id],pre=card(id,a?.role||id);if(a){a.logs=(a.logs||'')+txt;const mini=a.el.querySelector('.miniTerm');if(mini)mini.textContent=a.logs.slice(-360);refreshNodeStats(id);updateInspector()}typingQueues[id]=(typingQueues[id]||Promise.resolve()).then(()=>new Promise(res=>{let i=0;const tick=()=>{pre.textContent+=txt.slice(i,i+28);i+=28;pre.scrollTop=pre.scrollHeight;if(i<txt.length)setTimeout(tick,6);else res()};tick()}))}
function exec(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:'exec',parent:e.parent});agents[e.agent].tools.push(e.command);refreshNodeStats(e.agent);line('exec '+e.agent+' $ '+e.command);typeAppend(e.agent,`\\n$ ${e.command}\\n${e.text||''}\\n`);if(e.stats)envstats(e.stats)}
function consoleEvent(e){if(!agents[e.agent])spawn({...e,role:e.agent,title:'console',parent:e.parent});const label=e.stream==='stderr'?'STDERR':'STDOUT';const a=agents[e.agent],b=a.el.querySelector('.consoleBadge');a.console=e.return_code===0?'ok':'fail';b.classList.remove('ok','fail');b.classList.add(a.console);b.textContent=e.return_code===0?'âœ“':'Ã—';refreshNodeStats(e.agent);line(label.toLowerCase()+' '+e.agent+' rc '+e.return_code);typeAppend(e.agent,`\\n[${label} env=${e.env_id} rc=${e.return_code}]\\n${e.text||''}\\n`)}
function complete(e){$('answer').textContent=e.answer||'(sin respuesta)';$('runid').textContent=e.run_id;$('finalFlash').style.display='block';$('finalFlash').textContent='Resultado final listo Â· click Auditor Final o panel derecho';setTimeout(()=>$('finalFlash').style.display='none',9000);line('complete '+e.run_id);if(agents.auditor)selectAgent('auditor')}
function planned(e){line('planned '+e.agent+' wave '+e.wave);if(!agents[e.agent])spawn({agent:e.agent,role:e.role,title:'planificado wave '+e.wave,specialty:e.mission,parent:e.parent,wave:e.wave});else{agents[e.agent].wave=e.wave;refreshNodeStats(e.agent)}place()}
function handle(e){if(e.event==='run'){$('runid').textContent=e.run_id;line('run '+e.run_id)} if(e.event==='spawn')spawn(e); if(e.event==='status')status(e); if(e.event==='exec')exec(e); if(e.event==='console')consoleEvent(e); if(e.event==='env'){envstats(e.stats);if(e.agent&&agents[e.agent]&&e.env_id&&!agents[e.agent].envs.includes(e.env_id))agents[e.agent].envs.push(e.env_id);if(e.agent)refreshNodeStats(e.agent);line('env '+e.action+' '+e.env_id);updateInspector()} if(e.event==='plan')plan(e); if(e.event==='planned_agent')planned(e); if(e.event==='wave')wave(e); if(e.event==='log')log(e); if(e.event==='learn')learn(e); if(e.event==='complete')complete(e)}
$('run').onclick=async()=>{Object.values(agents).forEach(a=>a.el.remove());Object.keys(agents).forEach(k=>delete agents[k]);selected=null;feed.innerHTML='';timeline.innerHTML='';$('inspector').style.display='grid';$('insTitle').textContent='Selecciona un agente';$('insMeta').textContent='click en una pelota para ver estado, comandos y mini-entornos.';$('insLog').textContent='Sin agente seleccionado.';$('answer').textContent='Kimi esta planificando el enjambre libre...';$('run').disabled=true;try{const body={message:$('message').value,mode:$('mode').value,max_tokens:+$('max_tokens').value||1024,planner_tokens:+$('planner_tokens').value||4096,swarm_width:+$('swarm_width').value||0,max_agents:+$('max_agents').value||42,run_sandbox_probe:true,repo_url:$('repo_url').value||null,image_url:$('image_url').value||null,image_path:$('image_path').value||null};const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw Error(JSON.stringify(j));$('answer').textContent=j.answer||'(sin respuesta)';loadMemory()}catch(e){$('answer').textContent='ERROR '+e.message}finally{$('run').disabled=false}};
</script></body></html>
"""
