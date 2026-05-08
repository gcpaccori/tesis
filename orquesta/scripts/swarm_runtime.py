from __future__ import annotations

import json
import re
import socket
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
BLUEPRINT_PATH = BASE_DIR / "data" / "enjambre" / "enjambre_blueprint.json"

ANGLE_FRAMES = [
    "operativo",
    "arquitectonico",
    "de riesgos",
    "de coordinacion",
    "de dependencias",
    "de rendimiento",
]

PHASE_FRAMES = ["triage", "flujo", "destilando", "auditoria", "reencuadre"]

GREETING_PATTERNS = (
    "hola",
    "holi",
    "buenas",
    "buenos dias",
    "buen dia",
    "buenas tardes",
    "buenas noches",
    "hey",
    "que tal",
    "q tal",
    "hi",
    "hello",
)

CELL_TRIGGER_MAP = {
    "backend": ("backend", "api", "endpoint", "contrato", "auth", "csharp"),
    "frontend": ("frontend", "ui", "vista", "render", "pantalla", "xss"),
    "gateway": ("gateway", "jwt", "cors", "token", "ocelot", "nginx"),
    "conectividad": (
        "conexion",
        "dal",
        "pool",
        "dapper",
        "entity",
        "nuget",
        "integracion",
    ),
    "datos": ("datos", "sql", "tabla", "esquema", "base", "foreign key", "migration"),
    "qa_release": ("qa", "deploy", "rollback", "release", "slot"),
    "suministros": ("github", "repo", "pull request", "rama", "artefacto", "commit"),
    "tension": ("carga", "estres", "stress", "k6", "jmeter", "latencia"),
    "memoria": ("memoria", "conocimiento", "biblioteca", "empresa", "aprendizaje"),
    "grafos": ("grafo", "dependencia", "relacion", "poda", "graph"),
}

TARGET_CELL_MAP = {
    "github-cosechador": "suministros",
    "qa-despliegue": "qa_release",
    "backend-verificador": "backend",
    "frontend-verificador": "frontend",
    "bibliotecario": "memoria",
    "grafo-herramientas": "grafos",
    "base-datos-custodio": "datos",
    "guardian-gateway": "gateway",
    "fontanero-integracion": "conectividad",
    "tensionador-cognitivo": "tension",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: str, max_len: int = 220) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = re.sub(r"\s+", " ", ascii_only.lower()).strip()
    return ascii_only


def safe_json_load(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw or "", flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def stable_pick(options: List[str], *parts: Any) -> str:
    if not options:
        return ""
    seed = abs(hash(tuple(parts)))
    return options[seed % len(options)]


def is_simple_greeting(message: str) -> bool:
    normalized = re.sub(r"[!?.,;:]+", " ", (message or "").strip().lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return False
    if len(normalized.split()) > 4:
        return False
    return normalized in GREETING_PATTERNS


class SwarmRuntime:
    def __init__(
        self,
        chat_callable: Callable[..., Awaitable[str]],
        memory: Any,
        director_model: str,
        model_base_url: str = "",
        model_plan: Optional[Dict[str, Any]] = None,
        blueprint_path: Optional[Path] = None,
    ) -> None:
        self._chat = chat_callable
        self.memory = memory
        self.director_model = director_model
        self.model_base_url = model_base_url
        self.blueprint_path = blueprint_path or BLUEPRINT_PATH
        self.blueprint = self._load_blueprint()
        self.model_plan = model_plan or self.blueprint.get("architecture", {}).get("model_plan", {})
        self.agent_by_id = {item["id"]: item for item in self.blueprint["agents"]}
        self.agent_by_session = {item["session_id"]: item for item in self.blueprint["agents"]}
        self.cells = self.blueprint.get("architecture", {}).get("cells", [])
        self.cell_by_id = {item["id"]: item for item in self.cells}
        self.cell_by_supervisor_session = {
            item["supervisor_session_id"]: item for item in self.cells if item.get("supervisor_session_id")
        }
        self.children_by_leader: Dict[str, List[Dict[str, Any]]] = {}
        for item in self.blueprint["agents"]:
            leader = item.get("leader_session_id")
            if leader:
                self.children_by_leader.setdefault(leader, []).append(item)
        self.submanagers = [
            item for item in self.blueprint["agents"] if item.get("role_family") == "submanager"
        ]
        self.avatars = [
            item for item in self.blueprint["agents"] if item.get("role_family") == "avatar"
        ]
        self.session_state: Dict[str, Dict[str, Any]] = {}
        self.model_mode = "unknown"
        self._probed_model = False

    def _load_blueprint(self) -> Dict[str, Any]:
        if self.blueprint_path.exists():
            return json.loads(self.blueprint_path.read_text(encoding="utf-8"))
        return {
            "team_name": "ORQUESTA LIQUIDA",
            "mission_prompt": "Coordina una mesa cognitiva privada con Director y celdas.",
            "agents": [],
            "architecture": {"cells": [], "model_plan": {}},
        }

    def _state_for(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.session_state:
            self.session_state[session_id] = {
                "turn": 0,
                "recent_director_replies": [],
                "recent_manager_replies": [],
                "cell_states": {},
            }
        return self.session_state[session_id]

    def _agent(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.agent_by_session.get(session_id)

    def _target_agent(self, target_agent_id: Optional[int]) -> Dict[str, Any]:
        if target_agent_id and target_agent_id in self.agent_by_id:
            return self.agent_by_id[target_agent_id]
        return self._agent("director-liquido") or {"session_id": "director-liquido", "display_name": "Director Liquido"}

    def _direct_reports_for(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self.children_by_leader.get(session_id, []))

    def _descendants_for(self, session_id: str) -> List[Dict[str, Any]]:
        descendants: List[Dict[str, Any]] = []
        pending = list(self._direct_reports_for(session_id))
        while pending:
            current = pending.pop(0)
            descendants.append(current)
            pending.extend(self._direct_reports_for(current["session_id"]))
        return descendants

    def _count_reports_for(self, session_id: str) -> Dict[str, int]:
        direct = self._direct_reports_for(session_id)
        descendants = self._descendants_for(session_id)
        return {
            "direct": len(direct),
            "indirect": max(0, len(descendants) - len(direct)),
            "total": len(descendants),
        }

    def _role_label_for(self, agent: Dict[str, Any]) -> str:
        family = agent.get("role_family")
        if family == "director":
            return "Jefe General"
        if family == "submanager":
            return "Subgerente"
        if family == "avatar":
            return "Avatar"
        if agent.get("session_id") in self.cell_by_supervisor_session:
            return "Supervisor"
        return "Agente"

    def _detect_intent(self, message: str, target_agent_id: Optional[int]) -> str:
        normalized = normalize_text(message)
        subject = self._target_agent(target_agent_id)
        is_director_scope = subject.get("role_family") == "director"

        if is_simple_greeting(message):
            return "greeting"

        model_markers = (
            "que modelo",
            "que llm",
            "que mml",
            "de que modelo",
            "cual modelo",
            "que motor",
        )
        if any(marker in normalized for marker in model_markers):
            return "identity"

        hierarchy_markers = (
            "bajo tu mando",
            "bajo tu cargo",
            "a tu cargo",
            "directa e indirect",
            "directos e indirect",
            "reportes directos",
            "reportes indirectos",
        )
        if any(marker in normalized for marker in hierarchy_markers) and any(
            token in normalized for token in ("cuantos", "cuanta gente", "a cuantos", "cantidad")
        ):
            return "hierarchy_count"

        if is_director_scope and any(
            marker in normalized
            for marker in (
                "reunion",
                "reunion general",
                "presentense",
                "presentate",
                "presentense todos",
                "pasen lista",
                "quiero conocerlos",
            )
        ):
            return "meeting_introduction"

        if is_director_scope and any(
            marker in normalized
            for marker in (
                "te hacen caso",
                "te obedecen",
                "te escuchan",
                "siguen tus ordenes",
                "siguen tus instrucciones",
                "responden al director",
            )
        ):
            return "obedience_check"

        return "default"

    def _identity_reply(self, subject: Dict[str, Any]) -> str:
        tier_name = subject.get("model_tier") or "director"
        runtime_model = self._tier_model(tier_name, self.director_model)
        blueprint_model = subject.get("model_name") or runtime_model
        if runtime_model == blueprint_model:
            return (
                f"Ahora mismo te responde {subject['display_name']} desde {runtime_model} "
                f"en modo {self.model_mode}."
            )
        return (
            f"{subject['display_name']} esta planificado sobre {blueprint_model}, "
            f"pero el runtime vivo hoy esta saliendo por {runtime_model} en modo {self.model_mode}."
        )

    def _hierarchy_reply(self, subject: Dict[str, Any]) -> str:
        counts = self._count_reports_for(subject["session_id"])
        if subject.get("role_family") == "director":
            return (
                f"Tengo {counts['direct']} reportes directos y {counts['indirect']} indirectos. "
                f"En total responden {counts['total']} agentes bajo mi cadena de mando."
            )
        return (
            f"{subject['display_name']} tiene {counts['direct']} reportes directos y "
            f"{counts['indirect']} indirectos; en total coordina {counts['total']} agentes."
        )

    def _ordered_supervisors(self) -> List[Dict[str, Any]]:
        agents: List[Dict[str, Any]] = []
        for cell in self.cells:
            supervisor = self._agent(cell.get("supervisor_session_id", ""))
            if supervisor:
                agents.append(supervisor)
        return agents

    def _intro_line(self, agent: Dict[str, Any], turn: int) -> str:
        family = agent.get("role_family")
        if family == "submanager":
            responsibility = clean_text((agent.get("responsibilities") or ["coordinar su frente"])[0], 120)
            variants = [
                f"Soy {agent['display_name']}. Mi frente existe para {responsibility} y bajar ruido antes de escalarlo al Director.",
                f"Aqui {agent['display_name']}. Mi trabajo es {responsibility} sin romper el foco de las celulas que coordino.",
            ]
            return stable_pick(variants, agent["session_id"], turn, "intro")
        if family == "avatar":
            if agent["session_id"] == "avatar-datos":
                return "Soy Avatar de Datos. Mantengo el mapa vivo de esquemas, tablas, llaves y mutaciones para que nadie ataque a ciegas."
            return "Soy Oraculo Maestro. Sostengo arquitectura, negocio y contexto largo para que la mesa no piense sobre humo."
        cell = self.cell_by_supervisor_session.get(agent["session_id"])
        if cell:
            variants = [
                f"Soy {cell['supervisor_label']}. Protejo el flujo de {cell['specialist_label']} mientras trabajamos {cell['focus']}.",
                f"{cell['supervisor_label']} reportando. Mi escudo proxy mantiene a {cell['specialist_label']} enfocado en {cell['focus']}.",
            ]
            return stable_pick(variants, agent["session_id"], turn, "cell-intro")
        return f"Soy {agent['display_name']}. Estoy listo para entrar cuando el Director lo ordene."

    def _ack_line(self, agent: Dict[str, Any], turn: int) -> str:
        family = agent.get("role_family")
        if family == "submanager":
            variants = [
                f"Recibido, Director. {agent['display_name']} acata y baja la orden a su frente sin soltar evidencia.",
                f"Orden clara, Director. {agent['display_name']} ya alinea prioridades y evita trabajo muerto.",
            ]
            return stable_pick(variants, agent["session_id"], turn, "ack")
        if family == "avatar":
            return (
                f"Recibido. {agent['display_name']} sostiene contexto y responde consultas "
                "sin meter ruido al especialista."
            )
        cell = self.cell_by_supervisor_session.get(agent["session_id"])
        if cell:
            variants = [
                f"Recibido por la cadena. {cell['supervisor_label']} ajusta rumbo y deja a {cell['specialist_label']} en flujo.",
                f"A la orden. {cell['supervisor_label']} reencuadra {cell['label']} sin tocar el trance de {cell['specialist_label']}.",
            ]
            return stable_pick(variants, agent["session_id"], turn, "cell-ack")
        return f"Recibido. {agent['display_name']} sigue la orden y reporta cuando cierre el siguiente paso util."

    def _internal_chain_line(self, manager: Dict[str, Any], agent: Dict[str, Any], turn: int) -> str:
        cell = self.cell_by_supervisor_session.get(agent["session_id"])
        if cell:
            variants = [
                f"{manager['display_name']} a {cell['supervisor_label']}: mantengan formacion, respondan por proxy y no rompan flujo.",
                f"{manager['display_name']} a {cell['supervisor_label']}: acuse arriba; el especialista sigue aislado y ustedes me reportan.",
            ]
            return stable_pick(variants, manager["session_id"], agent["session_id"], turn)
        return (
            f"{manager['display_name']} confirma a {agent['display_name']} que la orden queda activa "
            "sin perder contexto."
        )

    def _special_intent_agents(self, intent: str) -> Dict[str, List[Dict[str, Any]]]:
        public_agents: List[Dict[str, Any]] = []
        internal_agents: List[Dict[str, Any]] = []
        if intent == "meeting_introduction":
            public_agents = [*self.submanagers, *self.avatars]
            internal_agents = self._ordered_supervisors()
        elif intent == "obedience_check":
            public_agents = [*self.submanagers, self._agent("oraculo-maestro")]
            internal_agents = self._ordered_supervisors()
        return {
            "public": [agent for agent in public_agents if agent],
            "internal": [agent for agent in internal_agents if agent],
        }

    def _message(
        self,
        speaker: str,
        role: str,
        body: str,
        audience: str,
        channel: str,
        *,
        cell_id: Optional[str] = None,
        speaker_agent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "id": f"msg-{abs(hash((speaker, role, body, channel, utc_now_iso())))}",
            "timestamp": utc_now_iso(),
            "speaker": speaker,
            "role": role,
            "body": clean_text(body, max_len=420),
            "audience": audience,
            "channel": channel,
            "cellId": cell_id,
            "speakerAgentId": speaker_agent_id,
        }

    def _cell_state(
        self,
        cell: Dict[str, Any],
        *,
        phase: str,
        headline: str,
        progress: int,
        blockers: Optional[List[str]] = None,
        focus: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "id": cell["id"],
            "label": cell["label"],
            "division": cell["division"],
            "supervisor": cell["supervisor_label"],
            "phase": phase,
            "headline": clean_text(headline, max_len=220),
            "progress": max(0, min(progress, 100)),
            "blockers": blockers or [],
            "lastUpdate": utc_now_iso(),
            "focus": focus or cell.get("focus", ""),
        }

    def _tier_model(self, tier: str, fallback: str) -> str:
        return str(self.model_plan.get(tier, {}).get("name") or fallback)

    def _model_summary_line(self) -> str:
        director = self._tier_model("director", self.director_model)
        submanager = self._tier_model("submanager", director)
        swarm_coder = self._tier_model("swarm_coder", "Qwen3.5-7B-Coder")
        swarm_math = self._tier_model("swarm_math", "Qwen3.5-7B-Math")
        avatar = self._tier_model("avatar", "Qwen3.5-7B-1M")
        return (
            f"Director={director}; Subgerentes={submanager}; "
            f"Enjambre={swarm_coder} + {swarm_math}; Avatares={avatar}"
        )

    def bootstrap(self, session_id: str) -> Dict[str, Any]:
        self._ensure_model_mode()
        session = self._state_for(session_id)
        cell_states = []
        for index, cell in enumerate(self.cells):
            state = session["cell_states"].get(cell["id"])
            if not state:
                blockers = [] if index % 3 else ["esperando una consigna concreta del Director"]
                state = self._cell_state(
                    cell,
                    phase="proxy-ready",
                    headline=(
                        f"{cell['supervisor_label']} ya protege el flujo de "
                        f"{cell['specialist_label']} sobre {cell['focus']}."
                    ),
                    progress=10 + (index % 5) * 8,
                    blockers=blockers,
                )
                session["cell_states"][cell["id"]] = state
            cell_states.append(state)

        director_agent = self._agent("director-liquido")
        oracle_agent = self._agent("oraculo-maestro")
        messages = [
            self._message(
                "Sistema",
                "Bus de Eventos",
                "Mesa redonda conectada. Tu hilo con el Director queda abierto y el resto de la mesa se repliega por hilo.",
                "system",
                "system",
            ),
            self._message(
                "Sistema",
                "Plan de Modelos",
                self._model_summary_line(),
                "system",
                "system",
            ),
            self._message(
                "Director Liquido",
                "Jefe General",
                "Estoy escuchando. Yo te respondo directo, y mi mesa trabaja por detras sin romper el foco del Especialista.",
                "public",
                "director-directo",
                speaker_agent_id=director_agent["id"] if director_agent else None,
            ),
        ]
        if oracle_agent:
            messages.append(
                self._message(
                    oracle_agent["display_name"],
                    "Avatar",
                    "Contexto base cargado. Si una celula necesita historia o arquitectura, yo la alimento sin tocar su hilo.",
                    "internal",
                    "avatar-oraculo",
                    speaker_agent_id=oracle_agent["id"],
                )
            )
        return {
            "session_id": session_id,
            "backend_mode": self.model_mode,
            "director_model": self.director_model,
            "agents": self.blueprint["agents"],
            "architecture": self.blueprint.get("architecture", {}),
            "messages": messages,
            "cell_states": cell_states,
            "tool_events": self._bootstrap_tool_events(),
        }

    def _bootstrap_tool_events(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for agent in self.blueprint["agents"]:
            role_family = agent.get("role_family")
            if role_family == "director":
                state = "active"
                status = "Trazando prioridades, deuda y huecos de cobertura"
            elif role_family == "submanager":
                state = "active"
                status = f"{agent['display_name']} esta leyendo su frente y repartiendo foco"
            elif role_family == "avatar":
                state = "waiting"
                status = f"{agent['display_name']} indexa contexto largo para la mesa"
            else:
                state = "waiting"
                status = agent.get("default_status", "Preparando herramientas")
            events.append(
                {
                    "agent_id": agent["id"],
                    "tool_name": agent.get("default_tool_name", "Plan"),
                    "status": clean_text(status),
                    "state": state,
                }
            )
        return events

    def _ensure_model_mode(self) -> None:
        if self._probed_model:
            return
        self._probed_model = True
        if not self.model_base_url:
            self.model_mode = "heuristic"
            return

        parsed = urlparse(self.model_base_url)
        host = parsed.hostname
        port = parsed.port
        if not host:
            self.model_mode = "heuristic"
            return
        if port is None:
            port = 443 if parsed.scheme == "https" else 80

        try:
            with socket.create_connection((host, port), timeout=0.35):
                self.model_mode = "openai-compatible"
        except OSError:
            self.model_mode = "heuristic"

    def _recent_director_replies(self, session_id: str) -> List[str]:
        return list(self._state_for(session_id)["recent_director_replies"][-5:])

    def _recent_manager_replies(self, session_id: str) -> List[str]:
        return list(self._state_for(session_id)["recent_manager_replies"][-8:])

    def _resolve_target_cells(self, target_agent_id: Optional[int]) -> List[Dict[str, Any]]:
        if not target_agent_id:
            return []
        agent = self.agent_by_id.get(target_agent_id)
        if not agent:
            return []
        target_cell_id = TARGET_CELL_MAP.get(agent["session_id"])
        if target_cell_id and target_cell_id in self.cell_by_id:
            return [self.cell_by_id[target_cell_id]]
        if agent.get("role_family") == "submanager":
            managed = [
                cell
                for cell in self.cells
                if cell.get("manager_session_id") == agent["session_id"]
            ]
            return managed[:2]
        if agent.get("role_family") == "avatar":
            covered = [
                cell
                for cell in self.cells
                if agent["session_id"] in list(cell.get("oracle_session_ids") or [])
            ]
            return covered[:2]
        return []

    def _select_cells(self, message: str, target_agent_id: Optional[int]) -> List[Dict[str, Any]]:
        target_cells = self._resolve_target_cells(target_agent_id)
        target_agent = self.agent_by_id.get(target_agent_id) if target_agent_id else None
        if is_simple_greeting(message):
            if target_cells:
                return target_cells
            if target_agent and target_agent.get("role_family") == "director":
                return []
            return []

        lowered = (message or "").lower()
        hits = []
        for cell_id, triggers in CELL_TRIGGER_MAP.items():
            score = sum(2 for trigger in triggers if trigger in lowered)
            if score > 0 and cell_id in self.cell_by_id:
                hits.append((score, cell_id))

        if hits:
            hits.sort(key=lambda item: (-item[0], item[1]))
            selected = list(target_cells)
            selected_ids = {cell["id"] for cell in selected}
            for _, cell_id in hits:
                if cell_id in selected_ids:
                    continue
                selected.append(self.cell_by_id[cell_id])
                selected_ids.add(cell_id)
                if len(selected) >= 3:
                    break
            if selected:
                return selected[:3]

        if target_cells:
            return target_cells

        default_ids = ["backend", "frontend", "datos", "memoria"]
        return [self.cell_by_id[cell_id] for cell_id in default_ids if cell_id in self.cell_by_id]

    def _select_managers(self, cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        session_ids = []
        for cell in cells:
            session_id = cell.get("manager_session_id")
            if session_id and session_id not in session_ids:
                session_ids.append(session_id)
        return [self.agent_by_session[item] for item in session_ids if item in self.agent_by_session]

    def _select_avatars(self, cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        session_ids = []
        for cell in cells:
            for session_id in list(cell.get("oracle_session_ids") or []):
                if session_id not in session_ids and session_id in self.agent_by_session:
                    session_ids.append(session_id)
        return [self.agent_by_session[item] for item in session_ids]

    def _select_support_agents(self, cells: List[Dict[str, Any]], message: str) -> List[Dict[str, Any]]:
        session_ids = []
        lowered = (message or "").lower()
        for cell in cells:
            for session_id in list(cell.get("support_session_ids") or []):
                if session_id in self.agent_by_session and session_id not in session_ids:
                    session_ids.append(session_id)
        if "grafo" in lowered or "memoria" in lowered:
            for session_id in ["bibliotecario", "grafo-herramientas", "compresor-grafos"]:
                if session_id in self.agent_by_session and session_id not in session_ids:
                    session_ids.append(session_id)
        if len(cells) >= 3 and "atencion-agentes" in self.agent_by_session and "atencion-agentes" not in session_ids:
            session_ids.append("atencion-agentes")
        return [self.agent_by_session[item] for item in session_ids]

    async def _chat_json(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        self._ensure_model_mode()
        if self.model_mode == "heuristic":
            return None
        try:
            raw = await self._chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=True,
                model=model,
            )
        except Exception:
            return None

        parsed = safe_json_load(raw)
        if parsed:
            self.model_mode = "openai-compatible"
            return parsed

        try:
            repaired = await self._chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "Convierte la entrada en un unico objeto JSON valido. "
                            "No agregues explicaciones ni markdown."
                        ),
                    },
                    {
                        "role": "user",
                        "content": raw,
                    },
                ],
                temperature=0.0,
                max_tokens=max(220, max_tokens),
                json_mode=True,
                model=model,
            )
        except Exception:
            return None

        parsed = safe_json_load(repaired)
        if parsed:
            self.model_mode = "openai-compatible"
            return parsed
        return None

    def _angle_for(self, session_id: str, message: str) -> str:
        turn = self._state_for(session_id)["turn"]
        seed = abs(hash((session_id, message, turn)))
        return ANGLE_FRAMES[seed % len(ANGLE_FRAMES)]

    def _heuristic_cell_payload(
        self,
        cell: Dict[str, Any],
        message: str,
        angle: str,
        turn: int,
    ) -> Dict[str, Any]:
        blocker_templates = [
            "esperando diff o artefacto confiable",
            "esperando validacion de una dependencia cruzada",
            "esperando una ventana limpia para profundizar sin ruido",
            "esperando confirmacion de borde arquitectonico",
        ]
        blocker = blocker_templates[(turn + len(cell["id"])) % len(blocker_templates)]
        assistant_count = min(max(2, (turn % 4) + 2), cell["max_assistants"])
        phase = stable_pick(PHASE_FRAMES, cell["id"], angle, turn)
        return {
            "public_status": (
                f"{cell['supervisor_label']} ya absorbio el pedido y mantiene a "
                f"{cell['specialist_label']} perforando {cell['focus']}."
            ),
            "internal_note": (
                f"{cell['specialist_label']} sigue en flujo; el escudo proxy evita que "
                f"las preguntas de la mesa le rompan el hilo."
            ),
            "phase": phase,
            "progress": min(92, 28 + assistant_count * 9 + turn * 4),
            "blockers": [blocker] if turn % 3 == 0 else [],
            "headline": (
                f"{cell['specialist_label']} trabaja sobre {cell['focus']} con "
                f"{assistant_count} asistentes y sin perder continuidad."
            ),
            "assistant_count": assistant_count,
            "cross_talk": (
                f"{cell['manager_label']} ya esta alineado con {cell['supervisor_label']} "
                f"para leer este frente con angulo {angle}."
            ),
            "next_step": f"cerrar {cell['focus']} y pasarlo limpio a memoria y grafos",
            "secretary_note": (
                f"{cell['secretary_label']} tiene TTL sobre asistentes {cell['assistant_prefix']} "
                "y mata loops si detecta deriva."
            ),
            "auditor_note": (
                f"{cell['auditor_label']} ya filtra errores y conserva solo el ADN util de la solucion."
            ),
            "specialist_voice": (
                f"{cell['specialist_label']} confirma que puede seguir sin interrupciones y luego "
                "recibira el resumen de visitas."
            ),
        }

    async def _cell_payload(
        self,
        session_id: str,
        cell: Dict[str, Any],
        message: str,
        memory_context: str,
        angle: str,
    ) -> Dict[str, Any]:
        recent = "\n".join(f"- {item}" for item in self._recent_director_replies(session_id)) or "- sin respuestas previas"
        supervisor = self._agent(cell["supervisor_session_id"])
        parsed = await self._chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Eres el Supervisor de una celula cognitiva. Proteges el flujo del Especialista, "
                        "respondes al exterior, coordinas secretario, auditor y asistentes. "
                        "Devuelve JSON valido con claves: public_status, internal_note, phase, progress, blockers, headline, "
                        "assistant_count, cross_talk, next_step, secretary_note, auditor_note, specialist_voice. "
                        "No repitas frases recientes y cambia el angulo de lectura cuando corresponda."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Turno: {self._state_for(session_id)['turn']}\n"
                        f"Angulo pedido: {angle}\n"
                        f"Celula: {json.dumps(cell, ensure_ascii=False)}\n"
                        f"Memoria: {memory_context}\n"
                        f"Mensaje del usuario: {message}\n"
                        f"Frases recientes del Director:\n{recent}\n"
                        "Responde como supervisor proxy, sin interrumpir al especialista."
                    ),
                },
            ],
            temperature=0.58,
            max_tokens=420,
            model=supervisor.get("model_name") if supervisor else self._tier_model("swarm_coder", self.director_model),
        )
        if parsed:
            return parsed
        return self._heuristic_cell_payload(cell, message, angle, self._state_for(session_id)["turn"])

    def _heuristic_manager_payload(
        self,
        manager: Dict[str, Any],
        cells: List[Dict[str, Any]],
        angle: str,
        turn: int,
    ) -> Dict[str, Any]:
        labels = ", ".join(cell["label"] for cell in cells[:3])
        challenge = stable_pick(
            [
                "no dejar que la mesa confunda urgencia con ruido",
                "cerrar dependencias antes de lanzar trabajo fino",
                "forzar evidencia antes de declarar avance",
                "hacer que cada celula reporte sin romper foco",
            ],
            manager["session_id"],
            angle,
            turn,
        )
        return {
            "public_status": (
                f"{manager['display_name']} ya sincroniza {labels} y vigila que no se dispare trabajo muerto."
            ),
            "internal_note": (
                f"{manager['display_name']} esta empujando el frente desde {angle} y mantiene el reto: {challenge}."
            ),
            "challenge": challenge,
            "progress": 25 + min(60, turn * 7 + len(cells) * 9),
            "next_step": f"cerrar el siguiente handoff util entre {labels}",
        }

    async def _manager_payload(
        self,
        session_id: str,
        manager: Dict[str, Any],
        cells: List[Dict[str, Any]],
        message: str,
        memory_context: str,
        angle: str,
    ) -> Dict[str, Any]:
        recent = "\n".join(f"- {item}" for item in self._recent_manager_replies(session_id)) or "- sin historial"
        parsed = await self._chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Eres un Subgerente de una mesa cognitiva. No interrumpes al Especialista. "
                        "Consolidas prioridad, riesgo y dependencias. Devuelve JSON con claves: "
                        "public_status, internal_note, challenge, progress, next_step."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Subgerente: {json.dumps(manager, ensure_ascii=False)}\n"
                        f"Celulas: {json.dumps(cells, ensure_ascii=False)}\n"
                        f"Angulo: {angle}\n"
                        f"Memoria: {memory_context}\n"
                        f"Mensaje del usuario: {message}\n"
                        f"Frases recientes que no debes repetir:\n{recent}"
                    ),
                },
            ],
            temperature=0.66,
            max_tokens=260,
            model=manager.get("model_name") or self._tier_model("submanager", self.director_model),
        )
        if parsed:
            return parsed
        return self._heuristic_manager_payload(manager, cells, angle, self._state_for(session_id)["turn"])

    def _heuristic_avatar_payload(
        self,
        avatar: Dict[str, Any],
        cells: List[Dict[str, Any]],
        angle: str,
        turn: int,
    ) -> Dict[str, Any]:
        labels = ", ".join(cell["label"] for cell in cells[:3])
        if avatar["session_id"] == "avatar-datos":
            note = f"Tengo mapeados esquema, llaves y mutaciones que afectan {labels}."
        else:
            note = f"Tengo cargado contexto largo de arquitectura, negocio y codigo para {labels}."
        return {
            "note": note,
            "focus": f"{avatar['display_name']} lee la mesa desde {angle}",
            "confidence": 65 + min(25, turn * 3),
        }

    async def _avatar_payload(
        self,
        session_id: str,
        avatar: Dict[str, Any],
        cells: List[Dict[str, Any]],
        message: str,
        memory_context: str,
        angle: str,
    ) -> Dict[str, Any]:
        parsed = await self._chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Eres un Avatar de contexto de una mesa cognitiva. Devuelve JSON con claves: "
                        "note, focus, confidence. Alimentas a la mesa sin romper el hilo del Especialista."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Avatar: {json.dumps(avatar, ensure_ascii=False)}\n"
                        f"Celulas activas: {json.dumps(cells, ensure_ascii=False)}\n"
                        f"Memoria: {memory_context}\n"
                        f"Mensaje del usuario: {message}\n"
                        f"Angulo: {angle}"
                    ),
                },
            ],
            temperature=0.32,
            max_tokens=180,
            model=avatar.get("model_name") or self._tier_model("avatar", self.director_model),
        )
        if parsed:
            return parsed
        return self._heuristic_avatar_payload(avatar, cells, angle, self._state_for(session_id)["turn"])

    def _heuristic_director_reply(
        self,
        message: str,
        angle: str,
        cell_payloads: List[Dict[str, Any]],
        manager_payloads: List[Dict[str, Any]],
        recent_replies: List[str],
    ) -> str:
        if not cell_payloads and is_simple_greeting(message):
            greeting_replies = [
                "Aqui estoy. Dime que frente quieres mover y yo coordino la mesa sin llenarte de ruido.",
                "Presente. Si quieres, elige un frente y hago que ese equipo te responda directo.",
                "Listo para trabajar. Puedes hablarme normal o elegir backend, frontend, datos, memoria o grafos.",
                "Te escucho. Cuando me digas un objetivo, activo solo el frente necesario y dejo el resto conversando por dentro.",
            ]
            return stable_pick(greeting_replies, message, len(recent_replies), angle)

        opening_pool = {
            "operativo": [
                "Voy a mover la mesa como una operacion coordinada, no como una fila de bots quietos.",
                "Lo bajo a ejecucion: menos rebote, mas manos alineadas y cero gente mirando al vacio.",
            ],
            "arquitectonico": [
                "Lo miro desde la estructura: cada celula conserva foco y el Supervisor absorbe el costo de la interrupcion.",
                "Lo cierro por arquitectura: la mesa no toca al Especialista directo, lo rodea con control y contexto.",
            ],
            "de riesgos": [
                "Lo tenso por el lado correcto: si mezclamos dependencias antes de tiempo, el flujo se quiebra.",
                "Voy a castigar el riesgo antes del entusiasmo: primero cierro donde puede romperse algo serio.",
            ],
            "de coordinacion": [
                "Lo ordeno por trafico humano: tu hablas conmigo, yo reparto y nadie se pisa.",
                "Voy a bajar ruido de mesa: cada Subgerente responde afuera y cada celula sigue adentro.",
            ],
            "de dependencias": [
                "Primero cierro dependencias duras para que backend y frontend no trabajen sobre humo.",
                "Voy a encadenar prerrequisitos antes de dejar que las celdas se aceleren en falso.",
            ],
            "de rendimiento": [
                "Voy a sacar latencia cognitiva: menos cambio de contexto y mas salidas limpias desde el proxy.",
                "Lo empujo por rendimiento mental: la mesa habla, el Especialista no pierde estado de flujo.",
            ],
        }
        opening = stable_pick(opening_pool.get(angle, opening_pool["operativo"]), message, angle, len(recent_replies))
        cell_summary = "; ".join(clean_text(item.get("headline", ""), 90) for item in cell_payloads[:3])
        manager_summary = "; ".join(
            clean_text(item.get("public_status", ""), 80) for item in manager_payloads[:2]
        )
        anti_repeat = ""
        if recent_replies:
            anti_repeat = " Cambio el angulo respecto a la respuesta anterior para no repetirme."
        return clean_text(
            f"{opening}{anti_repeat} Activo {len(cell_payloads)} celulas y {len(manager_payloads)} subgerencias ahora mismo. "
            f"Celulas: {cell_summary}. Subgerencias: {manager_summary}. "
            "Tu hilo conmigo queda abierto; el resto de la mesa se organiza en hilos replegados.",
            max_len=420,
        )

    async def _director_reply(
        self,
        session_id: str,
        message: str,
        memory_context: str,
        angle: str,
        cell_payloads: List[Dict[str, Any]],
        manager_payloads: List[Dict[str, Any]],
        avatar_payloads: List[Dict[str, Any]],
    ) -> str:
        recent = self._recent_director_replies(session_id)
        if not cell_payloads and is_simple_greeting(message):
            return self._heuristic_director_reply(
                message,
                angle,
                cell_payloads,
                manager_payloads,
                recent,
            )
        parsed = await self._chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Eres el Director Divergente de una mesa cognitiva. Contestale directo al usuario en espanol, "
                        "con tono firme y claro. No repitas phrasing de respuestas recientes. Usa el angulo pedido, "
                        "coordina subgerentes, avatares y celdas con supervisores proxy. Devuelve JSON con clave reply."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Angulo: {angle}\n"
                        f"Mensaje del usuario: {message}\n"
                        f"Memoria: {memory_context}\n"
                        f"Respuestas recientes que debes evitar repetir:\n"
                        f"{chr(10).join('- ' + item for item in recent) or '- ninguna'}\n"
                        f"Lectura de subgerencias: {json.dumps(manager_payloads, ensure_ascii=False)}\n"
                        f"Lectura de avatares: {json.dumps(avatar_payloads, ensure_ascii=False)}\n"
                        f"Lectura de celdas: {json.dumps(cell_payloads, ensure_ascii=False)}"
                    ),
                },
            ],
            temperature=0.72,
            max_tokens=340,
            model=self._tier_model("director", self.director_model),
        )
        if parsed and parsed.get("reply"):
            return clean_text(str(parsed["reply"]), max_len=420)
        return self._heuristic_director_reply(message, angle, cell_payloads, manager_payloads, recent)

    def _baseline_wait_status(self, agent: Dict[str, Any], turn: int) -> str:
        role_family = agent.get("role_family")
        if role_family == "director":
            return "Mantiene mapa vivo de prioridades y bloqueos"
        if role_family == "submanager":
            return f"{agent['display_name']} monitorea su frente y espera una escalacion util"
        if role_family == "avatar":
            return f"{agent['display_name']} sostiene contexto grande para la mesa"
        return stable_pick(
            [
                agent.get("default_status", "Esperando tarea"),
                f"{agent['display_name']} prepara herramientas y contexto",
                f"{agent['display_name']} sigue atento a un posible handoff",
            ],
            agent["session_id"],
            turn,
        )

    def _tool_events_for(
        self,
        selected_cells: List[Dict[str, Any]],
        cell_payloads: List[Dict[str, Any]],
        managers: List[Dict[str, Any]],
        manager_payloads: List[Dict[str, Any]],
        avatars: List[Dict[str, Any]],
        avatar_payloads: List[Dict[str, Any]],
        support_agents: List[Dict[str, Any]],
        turn: int,
        extra_active_agents: Optional[List[Dict[str, Any]]] = None,
        extra_status_by_session: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        event_by_id: Dict[int, Dict[str, Any]] = {}

        def put(agent: Dict[str, Any], state: str, status: str, tool_name: Optional[str] = None) -> None:
            event_by_id[agent["id"]] = {
                "agent_id": agent["id"],
                "tool_name": tool_name or agent.get("default_tool_name", "Plan"),
                "status": clean_text(status),
                "state": state,
            }

        for agent in self.blueprint["agents"]:
            put(agent, "waiting", self._baseline_wait_status(agent, turn))

        director = self._agent("director-liquido")
        if director:
            put(
                director,
                "active",
                "Dirige la mesa, detecta ruido y reencuadra donde haga falta",
                "Direct",
            )

        for manager, payload in zip(managers, manager_payloads):
            put(
                manager,
                "active",
                payload.get("public_status") or payload.get("internal_note") or manager["default_status"],
                manager.get("default_tool_name"),
            )

        for avatar, payload in zip(avatars, avatar_payloads):
            put(
                avatar,
                "active",
                payload.get("note") or avatar["default_status"],
                avatar.get("default_tool_name"),
            )

        for cell, payload in zip(selected_cells, cell_payloads):
            supervisor = self._agent(cell["supervisor_session_id"])
            if supervisor:
                put(
                    supervisor,
                    "active",
                    payload.get("headline") or payload.get("public_status") or supervisor["default_status"],
                    cell.get("tool_name"),
                )
            for session_id in list(cell.get("support_session_ids") or []):
                support = self._agent(session_id)
                if support:
                    put(
                        support,
                        "active",
                        f"{support['display_name']} apoya {cell['label']} con lectura lateral y handoff limpio",
                        support.get("default_tool_name"),
                    )

        for support in support_agents:
            if support["id"] not in event_by_id or event_by_id[support["id"]]["state"] != "active":
                put(
                    support,
                    "active",
                    f"{support['display_name']} esta destilando contexto para evitar espera muda",
                    support.get("default_tool_name"),
                )

        for agent in extra_active_agents or []:
            put(
                agent,
                "active",
                (extra_status_by_session or {}).get(agent["session_id"]) or agent.get("default_status", "Activo"),
                agent.get("default_tool_name"),
            )

        return [event_by_id[item["id"]] for item in self.blueprint["agents"] if item["id"] in event_by_id]

    async def _special_intent_response(
        self,
        session_id: str,
        message: str,
        target_agent_id: Optional[int],
        intent: str,
        turn: int,
    ) -> Dict[str, Any]:
        self._ensure_model_mode()
        session = self._state_for(session_id)
        subject = self._target_agent(target_agent_id)
        messages = [self._message("TU", "Usuario", message, "user", "director-directo")]
        speaker_agent_id = subject.get("id")
        director = self._agent("director-liquido")
        active_agents: List[Dict[str, Any]] = []
        status_by_session: Dict[str, str] = {}

        if intent == "identity":
            director_reply = self._identity_reply(subject)
            channel = "director-directo" if subject.get("role_family") == "director" else f"agent-{subject['session_id']}"
            messages.append(
                self._message(
                    subject["display_name"],
                    self._role_label_for(subject),
                    director_reply,
                    "public",
                    channel,
                    speaker_agent_id=speaker_agent_id,
                )
            )
            active_agents = [subject]
        elif intent == "hierarchy_count":
            director_reply = self._hierarchy_reply(subject)
            messages.append(
                self._message(
                    subject["display_name"],
                    self._role_label_for(subject),
                    director_reply,
                    "public",
                    "director-directo",
                    speaker_agent_id=speaker_agent_id,
                )
            )
            active_agents = [subject]
        elif intent in {"meeting_introduction", "obedience_check"}:
            if intent == "meeting_introduction":
                director_reply = stable_pick(
                    [
                        "Abro reunion de mesa. Hablan primero mis subgerencias y avatares; los supervisores quedan coordinando por el hilo interno.",
                        "Se abre la ronda. Quiero presentaciones limpias arriba y coordinacion por debajo, sin romper el flujo del especialista.",
                    ],
                    session_id,
                    turn,
                    intent,
                )
            else:
                counts = self._count_reports_for(subject["session_id"])
                director_reply = stable_pick(
                    [
                        f"Si. Tengo {counts['direct']} reportes directos y {counts['indirect']} indirectos. Te muestro el acuse de mando, no te lo vendo con humo.",
                        f"Si. La cadena responde: {counts['direct']} directos y {counts['indirect']} indirectos. Mira los acuses y la bajada de orden.",
                    ],
                    session_id,
                    turn,
                    intent,
                )
            messages.append(
                self._message(
                    "Director Liquido",
                    "Jefe General",
                    director_reply,
                    "public",
                    "director-directo",
                    speaker_agent_id=director["id"] if director else None,
                )
            )
            active_agents.append(director or subject)
            participants = self._special_intent_agents(intent)
            public_agents = participants["public"]
            internal_agents = participants["internal"]

            for agent in public_agents:
                line = self._intro_line(agent, turn) if intent == "meeting_introduction" else self._ack_line(agent, turn)
                messages.append(
                    self._message(
                        agent["display_name"],
                        self._role_label_for(agent),
                        line,
                        "public",
                        f"public-{agent['session_id']}",
                        speaker_agent_id=agent["id"],
                    )
                )
                active_agents.append(agent)
                status_by_session[agent["session_id"]] = line

            for agent in internal_agents:
                manager = self._agent(self.cell_by_supervisor_session.get(agent["session_id"], {}).get("manager_session_id", ""))
                line = self._intro_line(agent, turn) if intent == "meeting_introduction" else self._ack_line(agent, turn)
                chain_line = self._internal_chain_line(manager, agent, turn) if manager else line
                cell = self.cell_by_supervisor_session.get(agent["session_id"])
                channel = f"cell-{cell['id']}" if cell else f"internal-{agent['session_id']}"
                messages.append(
                    self._message(
                        agent["display_name"],
                        self._role_label_for(agent),
                        line,
                        "internal",
                        channel,
                        cell_id=cell["id"] if cell else None,
                        speaker_agent_id=agent["id"],
                    )
                )
                if manager:
                    messages.append(
                        self._message(
                            manager["display_name"],
                            "Subgerente",
                            chain_line,
                            "internal",
                            channel,
                            cell_id=cell["id"] if cell else None,
                            speaker_agent_id=manager["id"],
                        )
                    )
                    active_agents.append(manager)
                    status_by_session[manager["session_id"]] = chain_line
                active_agents.append(agent)
                status_by_session[agent["session_id"]] = line
                if cell:
                    session["cell_states"][cell["id"]] = self._cell_state(
                        cell,
                        phase="reencuadre" if intent == "meeting_introduction" else "flujo",
                        headline=line,
                        progress=35 if intent == "meeting_introduction" else 48,
                        blockers=[],
                        focus=cell.get("focus", ""),
                    )
        else:
            director_reply = clean_text(message)

        recent_director = session["recent_director_replies"]
        recent_director.append(director_reply)
        session["recent_director_replies"] = recent_director[-6:]

        route = [item["speaker"] for item in messages[1:]]
        specialist_notes = {item["speaker"]: item["body"] for item in messages[1:] if item["audience"] != "user"}
        memory_write = self.memory.registrar_turno(
            session_id=session_id,
            user_message=message,
            assistant_message=director_reply,
            route=route or [subject["display_name"]],
            specialist_notes=specialist_notes,
            memory_payload={
                "summary": director_reply,
                "entities": [
                    {
                        "name": item["speaker"],
                        "type": item["role"],
                        "metadata": {"audience": item["audience"], "intent": intent},
                    }
                    for item in messages[1:]
                ],
                "relations": [
                    {
                        "source": "Director Liquido",
                        "target": item["speaker"],
                        "type": "ordena" if intent == "obedience_check" else "coordina",
                        "metadata": {"intent": intent, "turn": turn},
                    }
                    for item in messages[2:]
                ],
                "decisions": [director_reply],
                "open_loops": [],
            },
        )

        return {
            "session_id": session_id,
            "backend_mode": self.model_mode,
            "director_model": self.director_model,
            "director_reply": next((item for item in messages[1:] if item["speaker"] == "Director Liquido"), messages[1]),
            "messages": messages,
            "cell_states": list(session["cell_states"].values()),
            "tool_events": self._tool_events_for(
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                turn,
                extra_active_agents=active_agents,
                extra_status_by_session=status_by_session,
            ),
            "selected_cells": [],
            "memory_write": memory_write,
        }

    async def chat(
        self,
        session_id: str,
        message: str,
        target_agent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        session = self._state_for(session_id)
        session["turn"] += 1
        turn = session["turn"]
        intent = self._detect_intent(message, target_agent_id)
        if intent in {"identity", "hierarchy_count", "meeting_introduction", "obedience_check"}:
            return await self._special_intent_response(
                session_id,
                message,
                target_agent_id,
                intent,
                turn,
            )
        angle = self._angle_for(session_id, message)
        memory_context = self.memory.buscar(message).to_prompt_block()
        selected_cells = self._select_cells(message, target_agent_id)
        direct_cell_ids = {
            cell["id"] for cell in (self._resolve_target_cells(target_agent_id) or selected_cells)
        }
        direct_manager_sessions = {
            cell.get("manager_session_id")
            for cell in selected_cells
            if cell["id"] in direct_cell_ids and cell.get("manager_session_id")
        }
        managers = self._select_managers(selected_cells)
        avatars = self._select_avatars(selected_cells)
        support_agents = self._select_support_agents(selected_cells, message)

        messages = [
            self._message("TU", "Usuario", message, "user", "director-directo"),
        ]

        manager_payloads = []
        for manager in managers:
            managed_cells = [
                cell for cell in selected_cells if cell.get("manager_session_id") == manager["session_id"]
            ]
            payload = await self._manager_payload(
                session_id,
                manager,
                managed_cells,
                message,
                memory_context,
                angle,
            )
            manager_payloads.append(payload)
            messages.append(
                self._message(
                    manager["display_name"],
                    "Subgerente",
                    payload.get("public_status") or manager["default_status"],
                    "public" if (not target_agent_id or manager["session_id"] in direct_manager_sessions) else "internal",
                    f"manager-{manager['session_id']}",
                    speaker_agent_id=manager["id"],
                )
            )
            messages.append(
                self._message(
                    manager["display_name"],
                    "Subgerente",
                    payload.get("internal_note") or payload.get("challenge") or "",
                    "internal",
                    f"manager-{manager['session_id']}",
                    speaker_agent_id=manager["id"],
                )
            )

        avatar_payloads = []
        for avatar in avatars:
            avatar_cells = [
                cell for cell in selected_cells if avatar["session_id"] in list(cell.get("oracle_session_ids") or [])
            ]
            payload = await self._avatar_payload(
                session_id,
                avatar,
                avatar_cells,
                message,
                memory_context,
                angle,
            )
            avatar_payloads.append(payload)
            messages.append(
                self._message(
                    avatar["display_name"],
                    "Avatar",
                    payload.get("note") or avatar["default_status"],
                    "internal",
                    f"avatar-{avatar['session_id']}",
                    speaker_agent_id=avatar["id"],
                )
            )

        cell_payloads = []
        for cell in selected_cells:
            payload = await self._cell_payload(session_id, cell, message, memory_context, angle)
            cell_payloads.append(payload)
            state = self._cell_state(
                cell,
                phase=payload.get("phase") or "flujo",
                headline=payload.get("headline") or payload.get("public_status") or cell["focus"],
                progress=int(payload.get("progress") or 35),
                blockers=[clean_text(item, 120) for item in list(payload.get("blockers") or [])[:3]],
                focus=cell.get("focus", ""),
            )
            session["cell_states"][cell["id"]] = state

            supervisor_id = self.agent_by_session.get(cell.get("supervisor_session_id", ""), {}).get("id")
            messages.append(
                self._message(
                    cell["supervisor_label"],
                    "Supervisor",
                    payload.get("public_status") or state["headline"],
                    "public" if (not target_agent_id or cell["id"] in direct_cell_ids) else "internal",
                    cell["id"],
                    cell_id=cell["id"],
                    speaker_agent_id=supervisor_id,
                )
            )
            messages.append(
                self._message(
                    cell["specialist_label"],
                    "Especialista",
                    payload.get("specialist_voice") or payload.get("internal_note") or "",
                    "internal",
                    f"{cell['id']}-interno",
                    cell_id=cell["id"],
                    speaker_agent_id=supervisor_id,
                )
            )
            messages.append(
                self._message(
                    cell["secretary_label"],
                    "Secretario",
                    payload.get("secretary_note") or "",
                    "internal",
                    f"{cell['id']}-interno",
                    cell_id=cell["id"],
                    speaker_agent_id=supervisor_id,
                )
            )
            messages.append(
                self._message(
                    cell["auditor_label"],
                    "Auditor",
                    payload.get("auditor_note") or payload.get("cross_talk") or "",
                    "internal",
                    f"{cell['id']}-interno",
                    cell_id=cell["id"],
                    speaker_agent_id=supervisor_id,
                )
            )

        for support in support_agents:
            support_line = stable_pick(
                [
                    f"{support['display_name']} abre una lectura lateral para evitar espera muda entre celdas.",
                    f"{support['display_name']} ya toma el handoff y prepara contexto limpio para la siguiente celula.",
                    f"{support['display_name']} interviene solo para bajar ruido y sostener continuidad.",
                ],
                support["session_id"],
                angle,
                turn,
            )
            messages.append(
                self._message(
                    support["display_name"],
                    "Soporte",
                    support_line,
                    "internal",
                    f"support-{support['session_id']}",
                    speaker_agent_id=support["id"],
                )
            )

        director_reply = await self._director_reply(
            session_id,
            message,
            memory_context,
            angle,
            cell_payloads,
            manager_payloads,
            avatar_payloads,
        )
        director_message = self._message(
            "Director Liquido",
            "Jefe General",
            director_reply,
            "public",
            "director-directo",
            speaker_agent_id=self.agent_by_session.get("director-liquido", {}).get("id"),
        )
        messages.insert(1, director_message)

        if not selected_cells and is_simple_greeting(message):
            recent_director = session["recent_director_replies"]
            recent_director.append(director_reply)
            session["recent_director_replies"] = recent_director[-6:]
            return {
                "session_id": session_id,
                "backend_mode": self.model_mode,
                "director_model": self.director_model,
                "director_reply": director_message,
                "messages": messages[:2],
                "cell_states": list(session["cell_states"].values()),
                "tool_events": self._tool_events_for(
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    turn,
                ),
                "selected_cells": [],
                "memory_write": self.memory.registrar_turno(
                    session_id=session_id,
                    user_message=message,
                    assistant_message=director_reply,
                    route=["Director Liquido"],
                    specialist_notes={"Director Liquido": director_reply},
                    memory_payload={
                        "summary": director_reply,
                        "entities": [{"name": "Director Liquido", "type": "Rol", "metadata": {"mode": "direct"}}],
                        "relations": [],
                        "decisions": [],
                        "open_loops": [],
                    },
                ),
            }

        specialist_notes = {
            cell["supervisor_label"]: payload.get("public_status") or payload.get("headline") or ""
            for cell, payload in zip(selected_cells, cell_payloads)
        }
        for manager, payload in zip(managers, manager_payloads):
            specialist_notes[manager["display_name"]] = payload.get("public_status") or payload.get("internal_note") or ""
        for avatar, payload in zip(avatars, avatar_payloads):
            specialist_notes[avatar["display_name"]] = payload.get("note") or ""

        memory_write = self.memory.registrar_turno(
            session_id=session_id,
            user_message=message,
            assistant_message=director_reply,
            route=[manager["display_name"] for manager in managers]
            + [cell["supervisor_label"] for cell in selected_cells],
            specialist_notes=specialist_notes,
            memory_payload={
                "summary": director_reply,
                "entities": (
                    [{"name": manager["display_name"], "type": "Subgerencia", "metadata": {"session": manager["session_id"]}} for manager in managers]
                    + [{"name": avatar["display_name"], "type": "Avatar", "metadata": {"session": avatar["session_id"]}} for avatar in avatars]
                    + [{"name": cell["label"], "type": "Celula", "metadata": {"division": cell["division"]}} for cell in selected_cells]
                ),
                "relations": (
                    [{"source": "Director Liquido", "target": manager["display_name"], "type": "coordina", "metadata": {"angle": angle}} for manager in managers]
                    + [{"source": manager["display_name"], "target": cell["label"], "type": "supervisa", "metadata": {"turn": turn}} for manager in managers for cell in selected_cells if cell.get("manager_session_id") == manager["session_id"]]
                    + [{"source": avatar["display_name"], "target": cell["label"], "type": "alimenta_contexto", "metadata": {"turn": turn}} for avatar in avatars for cell in selected_cells if avatar["session_id"] in list(cell.get("oracle_session_ids") or [])]
                ),
                "decisions": [
                    payload.get("next_step", "")
                    for payload in (manager_payloads + cell_payloads)
                    if payload.get("next_step")
                ],
                "open_loops": [
                    item
                    for payload in cell_payloads
                    for item in list(payload.get("blockers") or [])
                ],
            },
        )

        recent_director = session["recent_director_replies"]
        recent_director.append(director_reply)
        session["recent_director_replies"] = recent_director[-6:]

        recent_manager = session["recent_manager_replies"]
        for payload in manager_payloads:
            line = payload.get("public_status") or payload.get("internal_note") or ""
            if line:
                recent_manager.append(str(line))
        session["recent_manager_replies"] = recent_manager[-10:]

        return {
            "session_id": session_id,
            "backend_mode": self.model_mode,
            "director_model": self.director_model,
            "director_reply": director_message,
            "messages": messages,
            "cell_states": list(session["cell_states"].values()),
            "tool_events": self._tool_events_for(
                selected_cells,
                cell_payloads,
                managers,
                manager_payloads,
                avatars,
                avatar_payloads,
                support_agents,
                turn,
            ),
            "selected_cells": [cell["label"] for cell in selected_cells],
            "memory_write": memory_write,
        }
