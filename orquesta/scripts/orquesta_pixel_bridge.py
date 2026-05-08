#!/usr/bin/env python3
"""
Puente simple para mostrar tu orquesta dentro de Pixel Agents sin depender de Claude.

Lee ~/.pixel-agents/server.json y publica eventos hooks-only a /api/hooks/orquesta.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROVIDER_ID = "orquesta"


def load_server_config() -> dict[str, Any]:
    config_path = Path.home() / ".pixel-agents" / "server.json"
    if not config_path.exists():
        raise SystemExit(
            "No encontre ~/.pixel-agents/server.json. Abre primero Pixel Agents en VS Code."
        )
    return json.loads(config_path.read_text(encoding="utf-8"))


def post_event(payload: dict[str, Any]) -> None:
    config = load_server_config()
    url = f"http://127.0.0.1:{config['port']}/api/hooks/{PROVIDER_ID}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {config['token']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 200:
                raise SystemExit(f"Pixel Agents respondio con estado {response.status}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"No pude enviar el evento a Pixel Agents: {exc}") from exc


def emit_session_start(
    session_id: str,
    cwd: str,
    team_name: str | None,
    agent_name: str | None,
    is_team_lead: bool,
) -> None:
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": session_id,
        "cwd": cwd,
        "source": "orquesta",
        "team_name": team_name,
        "agent_name": agent_name,
        "is_team_lead": is_team_lead,
    }
    post_event(payload)


def emit_tool_start(session_id: str, tool_name: str, description: str) -> None:
    post_event(
        {
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_input": {"description": description},
        }
    )


def emit_tool_end(session_id: str) -> None:
    post_event({"hook_event_name": "PostToolUse", "session_id": session_id})


def emit_turn_end(session_id: str) -> None:
    post_event({"hook_event_name": "Stop", "session_id": session_id})


def emit_permission(session_id: str) -> None:
    post_event({"hook_event_name": "PermissionRequest", "session_id": session_id})


def emit_session_end(session_id: str, reason: str) -> None:
    post_event(
        {
            "hook_event_name": "SessionEnd",
            "session_id": session_id,
            "reason": reason,
        }
    )


def run_demo(cwd: str, delay: float, team_name: str) -> None:
    sessions = [
        {"id": "director-liquido", "agent_name": None, "lead": True},
        {"id": "arquitecto-liquido", "agent_name": "ARQUITECTO", "lead": False},
        {"id": "forense-cognitivo", "agent_name": "FORENSE", "lead": False},
        {"id": "tensionador-cognitivo", "agent_name": "TENSIONADOR", "lead": False},
        {"id": "visual-sistemas", "agent_name": "VISUAL", "lead": False},
    ]

    for session in sessions:
        emit_session_start(
            session["id"],
            cwd,
            team_name,
            session["agent_name"],
            session["lead"],
        )
        time.sleep(delay)

    emit_tool_start("director-liquido", "Plan", "Asignando frentes cognitivos")
    time.sleep(delay)
    emit_tool_end("director-liquido")

    specialist_moves = [
        ("arquitecto-liquido", "Analyze", "Trazando arquitectura base"),
        ("forense-cognitivo", "Inspect", "Mapeando superficie observable"),
        ("tensionador-cognitivo", "Think", "Buscando puntos de ruptura"),
        ("visual-sistemas", "Report", "Preparando vista para gerencia"),
    ]

    for session_id, tool_name, description in specialist_moves:
        emit_tool_start(session_id, tool_name, description)
        time.sleep(delay)
        emit_tool_end(session_id)
        emit_turn_end(session_id)
        time.sleep(delay)

    emit_tool_start("director-liquido", "Remember", "Consolidando hallazgos iniciales")
    time.sleep(delay)
    emit_tool_end("director-liquido")
    emit_turn_end("director-liquido")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Puente local entre Orquesta y Pixel Agents")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Levanta un enjambre demo en Pixel Agents")
    demo.add_argument("--cwd", default=os.getcwd(), help="Carpeta visible para los agentes")
    demo.add_argument("--delay", type=float, default=0.45, help="Pausa entre eventos")
    demo.add_argument("--team-name", default="ORQUESTA LIQUIDA", help="Nombre del equipo")

    session = subparsers.add_parser("session-start", help="Crear o reactivar un agente")
    session.add_argument("--session-id", required=True)
    session.add_argument("--cwd", default=os.getcwd())
    session.add_argument("--team-name", default="ORQUESTA LIQUIDA")
    session.add_argument("--agent-name")
    session.add_argument("--lead", action="store_true")

    tool_start = subparsers.add_parser("tool-start", help="Marcar herramienta activa")
    tool_start.add_argument("--session-id", required=True)
    tool_start.add_argument("--tool-name", required=True)
    tool_start.add_argument("--description", required=True)

    tool_end = subparsers.add_parser("tool-end", help="Cerrar la herramienta activa")
    tool_end.add_argument("--session-id", required=True)

    permission = subparsers.add_parser("permission", help="Mostrar solicitud de aprobacion")
    permission.add_argument("--session-id", required=True)

    turn_end = subparsers.add_parser("turn-end", help="Marcar el agente como idle")
    turn_end.add_argument("--session-id", required=True)

    session_end = subparsers.add_parser("session-end", help="Cerrar un agente")
    session_end.add_argument("--session-id", required=True)
    session_end.add_argument("--reason", default="completed")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "demo":
        run_demo(os.path.abspath(args.cwd), args.delay, args.team_name)
        return 0
    if args.command == "session-start":
        emit_session_start(
            args.session_id,
            os.path.abspath(args.cwd),
            args.team_name,
            args.agent_name,
            args.lead,
        )
        return 0
    if args.command == "tool-start":
        emit_tool_start(args.session_id, args.tool_name, args.description)
        return 0
    if args.command == "tool-end":
        emit_tool_end(args.session_id)
        return 0
    if args.command == "permission":
        emit_permission(args.session_id)
        return 0
    if args.command == "turn-end":
        emit_turn_end(args.session_id)
        return 0
    if args.command == "session-end":
        emit_session_end(args.session_id, args.reason)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
