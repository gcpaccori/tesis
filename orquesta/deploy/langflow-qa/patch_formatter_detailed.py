import os
from datetime import datetime, timezone

from sqlalchemy import MetaData, Table, create_engine, select, update


FORMATTER_CODE = r'''
import json
from urllib.request import urlopen

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message


RUNNER_BASE_URL = "http://qa-runner.local:8090"


def as_dict(value):
    if isinstance(value, Data):
        value = value.data
    if isinstance(value, dict) and "result" in value:
        return value["result"]
    return value if isinstance(value, dict) else {"raw": str(value or "")}


def short(value, limit=1400):
    value = str(value or "").strip()
    return value if len(value) <= limit else value[:limit] + "\n...[truncado]"


class QaFormatter(Component):
    display_name = "08 Formatear Resumen QA"
    description = "Convierte la respuesta final del runner en reporte detallado por etapa."
    icon = "FileText"
    name = "ElectroSurQaFormatter"
    inputs = [DataInput(name="input_data", display_name="Resultado final", required=True)]
    outputs = [Output(display_name="Resumen", name="summary", method="format_summary")]

    def _load_report(self, payload: dict) -> dict:
        job_id = payload.get("job_id")
        if not job_id:
            return payload
        try:
            with urlopen(f"{RUNNER_BASE_URL}/jobs/{job_id}", timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return payload

    def format_summary(self) -> Message:
        payload = as_dict(self.input_data)
        if payload.get("status") == "error":
            text = (
                "QA Electro Sur no se ejecuto.\n"
                f"Etapa: {payload.get('stage')}\n"
                f"Error: {payload.get('error')}"
            )
            message = Message(text=text)
            self.status = message
            return message

        report = self._load_report(payload)
        repos = report.get("repos") or []
        findings = report.get("findings") or payload.get("findings") or []
        smoke = report.get("smoke") or []
        graph = report.get("graph_ingest") or {}

        lines = [
            "# QA Electro Sur ejecutado",
            "",
            f"- Job: `{payload.get('job_id') or report.get('job_id')}`",
            f"- Modulo: `{payload.get('module') or report.get('module')}`",
            f"- Ambiente: `{payload.get('environment') or report.get('environment')}`",
            f"- Reporte: `{payload.get('report_md')}`",
            f"- Memgraph: `{'OK' if payload.get('memgraph_ingested') else 'NO INGESTADO'}`",
            "",
            "## 01 Crear Corrida QA",
            f"- Inicio: `{report.get('started_at')}`",
            f"- Fin: `{report.get('finished_at')}`",
            f"- Repos solicitados: `{len(repos)}`",
            "",
            "## 02 Descargar Repos",
        ]

        for repo in repos:
            clone = repo.get("clone") or {}
            lines.extend([
                f"- Repo: `{repo.get('name')}`",
                f"- URL: `{repo.get('url')}`",
                f"- Rama: `{repo.get('branch') or 'default'}`",
                f"- Clone OK: `{clone.get('return_code') == 0}` return_code=`{clone.get('return_code')}`",
            ])
            if clone.get("stderr_tail"):
                lines.append("```text")
                lines.append(short(clone.get("stderr_tail"), 1200))
                lines.append("```")

        lines.extend(["", "## 03 Inventario C#/Frontend/Gateway"])
        for repo in repos:
            inv = repo.get("inventory") or {}
            lines.extend([
                f"- Repo `{repo.get('name')}`: dotnet=`{inv.get('dotnet')}` frontend=`{inv.get('frontend')}` gateway=`{inv.get('gateway')}`",
                f"- Solutions: `{len(inv.get('solutions') or [])}` Projects: `{len(inv.get('projects') or [])}` PackageJson: `{len(inv.get('package_json') or [])}`",
                f"- Controllers: `{len(inv.get('controllers') or [])}` Endpoints: `{len(inv.get('endpoints') or [])}` NuGets: `{len(inv.get('nuget_packages') or [])}`",
            ])
            for item in (inv.get("projects") or [])[:10]:
                lines.append(f"- csproj: `{item}`")
            for item in (inv.get("package_json") or [])[:10]:
                lines.append(f"- package.json: `{item}`")
            for item in (inv.get("gateway_configs") or [])[:10]:
                lines.append(f"- gateway config: `{item}`")
            for package in (inv.get("nuget_packages") or [])[:20]:
                lines.append(f"- NuGet: `{package.get('name')}` `{package.get('version')}` en `{package.get('project')}`")
            for endpoint in (inv.get("endpoints") or [])[:20]:
                lines.append(f"- Endpoint: `{endpoint.get('verb')}` `{endpoint.get('route')}` archivo `{endpoint.get('file')}`")
            for warning in repo.get("warnings") or []:
                lines.append(f"- Warning: {warning}")

        lines.extend(["", "## 04 Restore Build Test .NET"])
        any_checks = False
        for repo in repos:
            checks = repo.get("checks") or []
            if checks:
                any_checks = True
            for check in checks:
                lines.extend([
                    f"- Repo `{repo.get('name')}`",
                    f"- Comando: `{' '.join(check.get('command') or [])}`",
                    f"- Return code: `{check.get('return_code')}` Timeout: `{check.get('timeout')}`",
                ])
                if check.get("stderr_tail"):
                    lines.append("```text")
                    lines.append(short(check.get("stderr_tail"), 1400))
                    lines.append("```")
                if check.get("stdout_tail"):
                    lines.append("```text")
                    lines.append(short(check.get("stdout_tail"), 1000))
                    lines.append("```")
        if not any_checks:
            lines.append("- No hubo comandos .NET porque no se detectaron proyectos .NET.")

        lines.extend(["", "## 05 Smoke Gateway UI"])
        if not smoke:
            lines.append("- No se definieron qa_targets para smoke.")
        for target in smoke:
            lines.append(
                f"- `{target.get('name')}` url=`{target.get('url')}` ok=`{target.get('ok')}` "
                f"status=`{target.get('status_code')}` esperado=`{target.get('expected_status')}` gateway=`{target.get('through_gateway')}`"
            )
            if target.get("error"):
                lines.append(f"- Error: {target.get('error')}")

        lines.extend(["", "## 06 Escribir Memgraph"])
        lines.append(f"- Intentado: `{graph.get('attempted')}` Exito: `{graph.get('success')}`")
        if graph.get("error"):
            lines.append("```text")
            lines.append(short(graph.get("error"), 1600))
            lines.append("```")

        lines.extend(["", "## 07 Hallazgos"])
        if not findings:
            lines.append("- Sin hallazgos bloqueantes en esta pasada.")
        for finding in findings:
            lines.append(f"- [{finding.get('severity')}] {finding.get('area')}: {finding.get('title')}")
            if finding.get("evidence"):
                lines.append("```text")
                lines.append(short(finding.get("evidence"), 1000))
                lines.append("```")

        message = Message(text="\n".join(lines))
        self.status = message
        return message
'''


def main() -> None:
    engine = create_engine(os.environ["LANGFLOW_DATABASE_URL"])
    metadata = MetaData()
    flow_table = Table("flow", metadata, autoload_with=engine)

    patched = []
    with engine.begin() as conn:
        rows = conn.execute(select(flow_table.c.id, flow_table.c.name, flow_table.c.data)).mappings().all()
        for row in rows:
            data = row["data"]
            changed = False
            for node in data.get("nodes", []):
                if node.get("data", {}).get("type") != "ElectroSurQaFormatter":
                    continue
                template = node["data"]["node"]["template"]
                template["code"]["value"] = FORMATTER_CODE
                if "code" in template["code"]:
                    template["code"]["code"] = FORMATTER_CODE
                node["data"]["node"]["description"] = "Convierte la respuesta final del runner en reporte detallado por etapa."
                changed = True
            if changed:
                conn.execute(update(flow_table).where(flow_table.c.id == row["id"]).values(data=data, updated_at=datetime.now(timezone.utc)))
                patched.append({"id": str(row["id"]), "name": row["name"]})

    if not patched:
        raise RuntimeError("No encontre nodos ElectroSurQaFormatter.")
    print({"status": "ok", "patched": patched})


if __name__ == "__main__":
    main()
