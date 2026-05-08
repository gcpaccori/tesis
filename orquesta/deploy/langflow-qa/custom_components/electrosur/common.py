"""Utilidades compartidas para todos los componentes del pipeline QA Electro Sur.

Centraliza la conexion con qa-runner, la normalizacion de datos y el manejo de
errores para que cada stage_*.py solo defina display_name, endpoint e icono.
"""

import json
import os
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from langflow.schema.data import Data


RUNNER_BASE_URL = os.environ.get("QA_RUNNER_URL", "http://qa-runner.local:8090")


def as_dict(value) -> dict:
    """Normaliza cualquier entrada de LangFlow a un dict plano."""
    if isinstance(value, Data):
        value = value.data
    if isinstance(value, dict) and "result" in value:
        return value["result"]
    return value if isinstance(value, dict) else {"raw": str(value or "")}


def error_data(stage: str, message: str, **extra) -> Data:
    """Crea un Data con estructura de error uniforme."""
    payload = {"status": "error", "stage": stage, "error": message}
    payload.update(extra)
    return Data(data=payload)


def post_stage(stage: str, endpoint: str, payload: dict) -> Data:
    """POST al qa-runner, propagando errores de etapas previas."""
    if payload.get("status") == "error":
        return Data(data=payload)

    url = f"{RUNNER_BASE_URL}{endpoint}"
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=1260) as response:
            return Data(data=json.loads(response.read().decode("utf-8")))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return error_data(stage, detail, http_status=exc.code, url=url)
    except Exception as exc:
        return error_data(
            stage,
            str(exc),
            url=url,
            input_keys=list(payload.keys()) if isinstance(payload, dict) else [],
        )


def looks_like_git_url(text: str) -> bool:
    """Detecta si el texto parece una URL de repositorio Git."""
    text = text.strip()
    if re.match(r"^https?://", text, re.IGNORECASE):
        return True
    if re.match(r"^git@", text):
        return True
    return False


def repo_name_from_url(url: str) -> str:
    """Extrae un nombre legible del URL del repo."""
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or "repo"


def build_job_from_url(url: str) -> dict:
    """Construye un QA Job JSON minimo a partir de una sola URL de repo."""
    name = repo_name_from_url(url)
    return {
        "module": name,
        "environment": "qa",
        "repos": [
            {
                "url": url.strip(),
                "branch": "main",
                "name": name,
                "kind": "auto",
            }
        ],
        "qa_targets": [],
        "notes": f"Job creado automaticamente desde URL: {url.strip()}",
        "run_builds": True,
        "run_tests": True,
        "run_frontend_build": False,
        "max_seconds": 900,
    }


def build_job_from_urls(urls: list[str]) -> dict:
    """Construye un QA Job JSON a partir de multiples URLs."""
    repos = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        name = repo_name_from_url(url)
        repos.append({"url": url, "branch": "main", "name": name, "kind": "auto"})
    module = repos[0]["name"] if repos else "modulo-sin-nombre"
    return {
        "module": module,
        "environment": "qa",
        "repos": repos,
        "qa_targets": [],
        "notes": f"Job creado automaticamente desde {len(repos)} URLs.",
        "run_builds": True,
        "run_tests": True,
        "run_frontend_build": False,
        "max_seconds": 900,
    }
