import os
import uuid
from typing import Annotated, Any, TypedDict

import httpx
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


NOC_URL = os.getenv("NOC_URL", "http://127.0.0.1:7870").rstrip("/")


class SwarmState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    run_id: str
    request: dict[str, Any]
    plan_note: str
    noc_response: dict[str, Any]
    sandbox_note: str
    answer: str


def latest_user_message(state: SwarmState) -> str:
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage) and getattr(message, "content", None):
            return str(message.content)
    return "Activa el enjambre QA de Kimi."


async def intake_node(state: SwarmState) -> SwarmState:
    state.setdefault("run_id", str(uuid.uuid4()))
    state["request"] = {
        "message": latest_user_message(state),
        "mode": "swarm",
        "max_tokens": 64,
        "planner_tokens": 700,
        "max_agents": 6,
        "swarm_width": 2,
        "run_sandbox_probe": True,
    }
    return state


async def planner_node(state: SwarmState) -> SwarmState:
    state["plan_note"] = (
        "El planner real vive en la cabina NOC 3D. "
        "Este nodo conserva la operacion visible en LangGraph Studio y delega la planificacion libre a Kimi."
    )
    return state


async def dynamic_swarm_node(state: SwarmState) -> SwarmState:
    async with httpx.AsyncClient(timeout=900) as client:
        response = await client.post(f"{NOC_URL}/chat", json=state["request"])
        response.raise_for_status()
        state["noc_response"] = response.json()
    return state


async def sandbox_node(state: SwarmState) -> SwarmState:
    sandbox = (state.get("noc_response") or {}).get("sandbox") or {}
    state["sandbox_note"] = (
        f"Sandbox ejecutado en NOC: mode={sandbox.get('mode')} "
        f"rc={sandbox.get('return_code')} env={sandbox.get('env_id') or sandbox.get('container')}"
    )
    return state


async def auditor_node(state: SwarmState) -> SwarmState:
    noc = state.get("noc_response") or {}
    answer = (
        "LangGraph Studio disparo el enjambre visual en NOC 3D.\n\n"
        f"- NOC URL: {NOC_URL}\n"
        f"- Run visual: {noc.get('run_id')}\n"
        f"- Modelo: {noc.get('model')}\n"
        f"- Eventos capturados: {len(noc.get('events') or [])}\n"
        f"- {state.get('sandbox_note')}\n\n"
        f"Respuesta auditor NOC:\n{noc.get('answer', '')}"
    )
    state["answer"] = answer
    state["messages"] = [AIMessage(content=answer)]
    return state


builder = StateGraph(SwarmState)
builder.add_node("intake", intake_node)
builder.add_node("planner", planner_node)
builder.add_node("dynamic_swarm", dynamic_swarm_node)
builder.add_node("sandbox", sandbox_node)
builder.add_node("auditor", auditor_node)
builder.set_entry_point("intake")
builder.add_edge("intake", "planner")
builder.add_edge("planner", "dynamic_swarm")
builder.add_edge("dynamic_swarm", "sandbox")
builder.add_edge("sandbox", "auditor")
builder.add_edge("auditor", END)

graph = builder.compile()
