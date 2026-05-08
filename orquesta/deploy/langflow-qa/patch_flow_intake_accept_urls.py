import os
from datetime import datetime, timezone

from sqlalchemy import MetaData, Table, create_engine, select, update


FLOW_NAME = os.environ.get("FLOW_NAME", "QA Electro Sur")


INTAKE_CODE = r'''
import json
import re

from lfx.custom.custom_component.component import Component
from lfx.io import MultilineInput, Output
from lfx.schema.data import Data


REPO_URL_RE = re.compile(r"(https?://\S+?)(?:\s|$)")


def error(stage: str, message: str, **extra) -> Data:
    payload = {"status": "error", "stage": stage, "error": message}
    payload.update(extra)
    return Data(data=payload)


def repo_kind(url: str) -> str:
    lowered = url.lower()
    if any(token in lowered for token in ("front", "web", "ui", "angular", "react", "vue")):
        return "frontend"
    if any(token in lowered for token in ("api", "back", "backend", "server")):
        return "backend"
    return "auto"


def repo_name(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or "repo"


def payload_from_text(raw: str) -> dict | None:
    urls = [match.group(1).rstrip(".,;") for match in REPO_URL_RE.finditer(raw)]
    if not urls:
        return None
    return {
        "module": repo_name(urls[0]),
        "environment": "qa",
        "repos": [
            {
                "url": url,
                "name": repo_name(url),
                "kind": repo_kind(url),
            }
            for url in urls
        ],
        "qa_targets": [],
        "notes": "Job creado automaticamente desde URL pegada en el chat. Agrega qa_targets si quieres smoke gateway/UI.",
        "run_builds": True,
        "run_tests": True,
        "run_frontend_build": False,
        "max_seconds": 900,
    }


class JobIntake(Component):
    display_name = "00 Intake JSON Electro Sur"
    description = "Acepta QA Job JSON, URL Git suelta, o varias URLs Git."
    icon = "ClipboardList"
    name = "ElectroSurJobIntake"

    inputs = [
        MultilineInput(
            name="job_json",
            display_name="QA Job JSON o URL Git",
            info="Pega un JSON completo, una URL GitHub/Git, o varias URLs separadas por saltos de linea.",
            input_types=["Message", "Text"],
            required=True,
        )
    ]
    outputs = [Output(display_name="Job JSON", name="job_data", method="parse_job")]

    def parse_job(self) -> Data:
        raw = self.job_json.text if hasattr(self.job_json, "text") else str(self.job_json or "")
        raw = raw.strip()
        if not raw:
            result = error(self.display_name, "No llego entrada. Pega una URL Git o un QA Job JSON.")
            self.status = result.data["error"]
            return result

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            payload = payload_from_text(raw)
            if payload is None:
                result = error(
                    self.display_name,
                    f"Entrada no reconocida. Pega una URL Git, varias URLs Git, o un QA Job JSON. Detalle JSON: {exc}",
                    received=raw[:500],
                )
                self.status = result.data["error"]
                return result

        if isinstance(payload, str):
            payload = payload_from_text(payload) or {}

        if isinstance(payload, list):
            urls = [str(item).strip() for item in payload if str(item).strip()]
            payload = {
                "module": repo_name(urls[0]) if urls else "repos-chat",
                "environment": "qa",
                "repos": [
                    {
                        "url": url,
                        "name": repo_name(url),
                        "kind": repo_kind(url),
                    }
                    for url in urls
                ],
                "qa_targets": [],
                "notes": "Job creado automaticamente desde lista simple.",
                "run_builds": True,
                "run_tests": True,
                "run_frontend_build": False,
                "max_seconds": 900,
            }

        if not isinstance(payload, dict) or not payload.get("repos"):
            keys = list(payload.keys()) if isinstance(payload, dict) else []
            result = error(self.display_name, "La entrada debe producir repos[].", received_keys=keys)
            self.status = result.data["error"]
            return result

        self.status = f"Pedido validado: {payload.get('module', 'modulo-sin-nombre')} con {len(payload.get('repos', []))} repos."
        return Data(data=payload)
'''


def main() -> None:
    engine = create_engine(os.environ["LANGFLOW_DATABASE_URL"])
    metadata = MetaData()
    flow_table = Table("flow", metadata, autoload_with=engine)

    with engine.begin() as conn:
        rows = conn.execute(select(flow_table.c.id, flow_table.c.name, flow_table.c.data)).mappings().all()
        patched_flows = []
        for row in rows:
            data = row["data"]
            patched = False
            for node in data.get("nodes", []):
                if node.get("data", {}).get("type") != "ElectroSurJobIntake":
                    continue
                template = node["data"]["node"]["template"]
                template["code"]["value"] = INTAKE_CODE
                if "code" in template["code"]:
                    template["code"]["code"] = INTAKE_CODE
                template["job_json"]["display_name"] = "QA Job JSON o URL Git"
                template["job_json"]["info"] = "Pega un JSON completo, una URL GitHub/Git, o varias URLs separadas por saltos de linea."
                template["job_json"]["placeholder"] = "https://github.com/org/repo.git"
                node["data"]["node"]["description"] = "Acepta QA Job JSON, URL Git suelta, o varias URLs Git."
                patched = True
            if patched:
                conn.execute(update(flow_table).where(flow_table.c.id == row["id"]).values(data=data, updated_at=datetime.now(timezone.utc)))
                patched_flows.append({"id": str(row["id"]), "name": row["name"]})

    if not patched_flows:
        raise RuntimeError("No encontre ningun nodo ElectroSurJobIntake en la base.")
    print({"status": "ok", "patched_flows": patched_flows})


if __name__ == "__main__":
    main()
