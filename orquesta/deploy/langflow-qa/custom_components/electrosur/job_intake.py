"""00 Intake JSON Electro Sur - Componente de entrada inteligente.

Acepta TRES formatos de entrada:
  1. JSON completo del job (el formato original)
  2. URL de repositorio Git (construye el JSON automaticamente)
  3. Multiples URLs separadas por lineas nuevas

Esto permite al usuario pegar simplemente una URL en el chat
en vez de construir el JSON manualmente.
"""

import json

from langflow.custom import Component
from langflow.io import MultilineInput, Output
from langflow.schema.data import Data

from .common import (
    build_job_from_url,
    build_job_from_urls,
    error_data,
    looks_like_git_url,
)


EXAMPLE_JOB = """{
  "module": "modulo-clientes-electrosur",
  "environment": "qa",
  "repos": [
    {
      "url": "https://github.com/empresa/backend.git",
      "branch": "main",
      "name": "backend",
      "kind": "backend"
    }
  ],
  "qa_targets": [],
  "run_builds": true,
  "run_tests": true,
  "max_seconds": 900
}"""


class JobIntake(Component):
    display_name = "00 Intake JSON Electro Sur"
    description = (
        "Valida el pedido de QA: acepta JSON completo, "
        "una URL de repo Git, o varias URLs separadas por linea."
    )
    icon = "ClipboardList"
    name = "ElectroSurJobIntake"

    inputs = [
        MultilineInput(
            name="job_json",
            display_name="QA Job JSON o URL",
            info=(
                "JSON con repos, ambiente, targets y flags de ejecucion. "
                "Tambien puedes pegar directamente una URL de GitHub."
            ),
            input_types=["Message", "Text"],
            required=True,
        )
    ]
    outputs = [Output(display_name="Job Data", name="job_data", method="parse_job")]

    def parse_job(self) -> Data:
        # --- Extraer texto plano ---
        raw = self.job_json
        if hasattr(raw, "text"):
            raw = raw.text
        raw = str(raw or "").strip()

        if not raw:
            result = error_data(
                self.display_name,
                "No llego datos al flujo. Pega un QA Job JSON o una URL de repo en el chat.",
            )
            self.status = result.data["error"]
            return result

        # --- Intentar parsear como JSON primero ---
        if raw.startswith("{") or raw.startswith("["):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                result = error_data(
                    self.display_name,
                    f"JSON invalido: {exc}",
                    received=raw[:500],
                    hint="Asegurate de que el JSON este bien formado. "
                    "Tambien puedes pegar directamente la URL del repo.",
                )
                self.status = result.data["error"]
                return result
        else:
            # --- Deteccion inteligente de URLs ---
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            urls = [line for line in lines if looks_like_git_url(line)]

            if urls:
                if len(urls) == 1:
                    payload = build_job_from_url(urls[0])
                    self.status = f"Job creado desde URL: {urls[0]}"
                else:
                    payload = build_job_from_urls(urls)
                    self.status = f"Job creado desde {len(urls)} URLs."
            else:
                # Ultimo intento: quizas es JSON sin llaves al inicio por espacios
                try:
                    payload = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    result = error_data(
                        self.display_name,
                        "Entrada no reconocida. Envia un JSON de job o una URL de repositorio Git.",
                        received=raw[:500],
                        hint=f"Ejemplo JSON:\n{EXAMPLE_JOB}\n\nO simplemente pega: https://github.com/org/repo.git",
                    )
                    self.status = result.data["error"]
                    return result

        # --- Validar que tenga repos ---
        if isinstance(payload, dict) and not payload.get("repos"):
            result = error_data(
                self.display_name,
                "El QA Job JSON debe traer repos[].",
                received_keys=list(payload.keys()),
            )
            self.status = result.data["error"]
            return result

        self.status = (
            f"Pedido validado: {payload.get('module', 'modulo-sin-nombre')} "
            f"con {len(payload.get('repos', []))} repos."
        )
        return Data(data=payload)
