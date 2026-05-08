"""08 Formatear Resumen QA - Convierte resultados en mensaje legible para el chat."""

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema.data import Data
from langflow.schema.message import Message

from .common import as_dict


class QaFormatter(Component):
    display_name = "08 Formatear Resumen QA"
    description = "Convierte la respuesta final del runner en mensaje legible."
    icon = "FileText"
    name = "ElectroSurQaFormatter"
    inputs = [DataInput(name="input_data", display_name="Resultado final", required=True)]
    outputs = [Output(display_name="Resumen", name="summary", method="format_summary")]

    def format_summary(self) -> Message:
        payload = as_dict(self.input_data)

        if payload.get("status") == "error":
            lines = [
                "❌ **QA Electro Sur no se ejecuto.**",
                f"**Etapa:** {payload.get('stage', 'desconocida')}",
                f"**Error:** {payload.get('error', 'sin detalle')}",
            ]
            if payload.get("received"):
                lines.append(f"**Recibido:** `{payload['received'][:200]}`")
            if payload.get("hint"):
                lines.append(f"**Sugerencia:** {payload['hint']}")
            if payload.get("url"):
                lines.append(f"**URL del runner:** `{payload['url']}`")
            if payload.get("http_status"):
                lines.append(f"**HTTP Status:** {payload['http_status']}")
            text = "\n".join(lines)
            message = Message(text=text)
            self.status = message
            return message

        repos = payload.get("repos") or []
        findings = payload.get("findings") or []
        lines = [
            "✅ **QA Electro Sur ejecutado.**",
            f"**Job:** `{payload.get('job_id', 'N/A')}`",
            f"**Modulo:** {payload.get('module', 'N/A')}",
            f"**Ambiente:** {payload.get('environment', 'N/A')}",
            f"**Etapa final:** {payload.get('stage', 'N/A')}",
            f"**Memgraph:** {'✅ OK' if payload.get('memgraph_ingested') else '⚠️ NO INGESTADO'}",
        ]
        if payload.get("report_md"):
            lines.append(f"**Reporte:** `{payload['report_md']}`")
        lines.append("")
        lines.append("### Repos evaluados")
        if not repos:
            lines.append("- Ningun repo reportado.")
        for repo in repos:
            if isinstance(repo, dict):
                name = repo.get("name", "?")
                clone = "✅" if repo.get("clone_ok") else "❌"
                dotnet = "✅" if repo.get("dotnet") else "—"
                frontend = "✅" if repo.get("frontend") else "—"
                gateway = "✅" if repo.get("gateway") else "—"
                projects = repo.get("projects", 0)
                endpoints = repo.get("endpoints", 0)
                nugets = repo.get("nugets", 0)
                failed = repo.get("checks_failed", 0)
                lines.append(
                    f"- **{name}**: clone={clone} dotnet={dotnet} frontend={frontend} "
                    f"gateway={gateway} projects={projects} endpoints={endpoints} "
                    f"nugets={nugets} checks_failed={failed}"
                )
            else:
                lines.append(f"- {repo}")
        lines.append("")
        lines.append("### Hallazgos")
        if not findings:
            lines.append("- Sin hallazgos bloqueantes en esta pasada. 🎉")
        for finding in findings:
            if isinstance(finding, dict):
                lines.append(
                    f"- [{finding.get('severity', '?')}] "
                    f"{finding.get('area', '?')}: {finding.get('title', '?')}"
                )
            else:
                lines.append(f"- {finding}")

        if payload.get("memgraph_error"):
            lines.append("")
            lines.append(f"### Memgraph Error\n`{payload['memgraph_error'][:500]}`")

        message = Message(text="\n".join(lines))
        self.status = message
        return message
