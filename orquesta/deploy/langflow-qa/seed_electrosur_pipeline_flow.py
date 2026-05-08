import copy
import gzip
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.request import urlopen

from sqlalchemy import MetaData, Table, create_engine, insert, select, update


LANGFLOW_URL = os.environ.get("LANGFLOW_URL", "http://127.0.0.1:7860")
FLOW_NAME = os.environ.get("FLOW_NAME", "QA Electro Sur - Pipeline Real")
OLD_FLOW_NAMES = ["QA Electro Sur - Runner Operativo"]
TARGET_USERNAME = os.environ.get("TARGET_USERNAME", "langflow")


EXAMPLE_JOB = {
    "module": "modulo-clientes-electrosur",
    "environment": "qa",
    "repos": [
        {
            "url": "https://github.com/empresa/backend-electrosur.git",
            "branch": "feature/nuevo-modulo",
            "name": "backend-electrosur",
            "kind": "backend",
        },
        {
            "url": "https://github.com/empresa/frontend-electrosur.git",
            "branch": "feature/nuevo-modulo",
            "name": "frontend-electrosur",
            "kind": "frontend",
        },
    ],
    "qa_targets": [
        {
            "name": "gateway-health",
            "url": "https://qa-gateway.empresa.local/health",
            "expected_status": 200,
            "through_gateway": True,
        }
    ],
    "notes": "Cambiar repos/branches/URLs por los reales. Este flujo ejecuta etapas, no prompt unico.",
    "run_builds": True,
    "run_tests": True,
    "run_frontend_build": False,
    "max_seconds": 900,
}


INTAKE_COMPONENT_CODE = r'''
import json
import re

try:
    from langflow.custom import Component
    from langflow.io import MultilineInput, Output
    from langflow.schema.data import Data
except ImportError:
    from lfx.custom.custom_component.component import Component
    from lfx.io import MultilineInput, Output
    from lfx.schema.data import Data


def _looks_like_git_url(text):
    text = text.strip()
    return bool(re.match(r"^https?://", text, re.IGNORECASE) or re.match(r"^git@", text))

def _repo_name(url):
    name = url.rstrip("/").split("/")[-1]
    return name[:-4] if name.endswith(".git") else (name or "repo")

def _build_job_from_urls(urls):
    repos = []
    for u in urls:
        u = u.strip()
        if not u:
            continue
        repos.append({"url": u, "branch": "main", "name": _repo_name(u), "kind": "auto"})
    return {
        "module": repos[0]["name"] if repos else "modulo-sin-nombre",
        "environment": "qa",
        "repos": repos,
        "qa_targets": [],
        "notes": f"Job creado desde {len(repos)} URL(s).",
        "run_builds": True,
        "run_tests": True,
        "run_frontend_build": False,
        "max_seconds": 900,
    }


class ElectroSurJobIntake(Component):
    display_name = "00 Intake JSON Electro Sur"
    description = "Valida el pedido de QA: acepta JSON completo o una URL de repo Git."
    icon = "ClipboardList"
    name = "ElectroSurJobIntake"

    inputs = [
        MultilineInput(
            name="job_json",
            display_name="QA Job JSON o URL",
            info="JSON con repos, ambiente, targets y flags. Tambien acepta URLs de Git directamente.",
            input_types=["Message", "Text"],
            value="",
            required=True,
        )
    ]

    outputs = [
        Output(display_name="Job Data", name="job_data", method="parse_job"),
    ]

    def _text(self, value):
        if hasattr(value, "text"):
            return value.text
        return str(value or "")

    def _error(self, msg, **extra):
        payload = {"status": "error", "stage": self.display_name, "error": msg}
        payload.update(extra)
        self.status = msg
        return Data(data=payload)

    def parse_job(self) -> Data:
        raw = self._text(self.job_json).strip()
        if not raw:
            return self._error("No llego datos. Pega un QA Job JSON o una URL de repo en el chat.")

        # --- Intentar como JSON ---
        if raw.startswith("{") or raw.startswith("["):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                return self._error(
                    f"JSON invalido: {exc}",
                    received=raw[:500],
                    hint="Tambien puedes pegar directamente la URL del repo.",
                )
        else:
            # --- Detectar URLs de Git ---
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            urls = [l for l in lines if _looks_like_git_url(l)]
            if urls:
                payload = _build_job_from_urls(urls)
            else:
                try:
                    payload = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    return self._error(
                        "Entrada no reconocida. Envia un JSON de job o una URL de repositorio Git.",
                        received=raw[:500],
                    )

        if not payload.get("repos"):
            return self._error("El QA Job JSON debe traer repos[].", received_keys=list(payload.keys()))

        self.status = f"Pedido validado: {payload.get('module', 'modulo-sin-nombre')} con {len(payload.get('repos', []))} repos."
        return Data(data=payload)
'''


FORMATTER_COMPONENT_CODE = r'''
try:
    from langflow.custom import Component
    from langflow.io import DataInput, Output
    from langflow.schema.data import Data
    from langflow.schema.message import Message
except ImportError:
    from lfx.custom.custom_component.component import Component
    from lfx.inputs.inputs import HandleInput as DataInput
    from lfx.schema.data import Data
    from lfx.schema.message import Message
    from lfx.template.field.base import Output


class ElectroSurQaFormatter(Component):
    display_name = "08 Formatear Resumen QA"
    description = "Convierte la respuesta del runner en un mensaje limpio para el chat."
    icon = "FileText"
    name = "ElectroSurQaFormatter"

    inputs = [
        DataInput(
            name="input_data",
            display_name="Resultado del Runner",
            input_types=["Data", "JSON"],
            required=True,
        )
    ]

    outputs = [
        Output(display_name="Resumen", name="summary", method="format_summary"),
    ]

    def _payload(self):
        value = self.input_data
        if isinstance(value, Data):
            value = value.data
        if isinstance(value, dict) and "result" in value:
            return value["result"]
        return value if isinstance(value, dict) else {"raw": str(value)}

    def format_summary(self) -> Message:
        payload = self._payload()
        if payload.get("status") == "error":
            lines = [
                "QA Electro Sur no se ejecuto.",
                f"Etapa: {payload.get('stage', 'desconocida')}",
                f"Error: {payload.get('error', 'sin detalle')}",
            ]
            if payload.get("received"):
                lines.append(f"Recibido: {payload['received'][:200]}")
            if payload.get("hint"):
                lines.append(f"Sugerencia: {payload['hint']}")
            if payload.get("url"):
                lines.append(f"URL del runner: {payload['url']}")
            message = Message(text="\n".join(lines))
            self.status = message
            return message

        repos = payload.get("repos") or []
        findings = payload.get("findings") or []
        lines = [
            "QA Electro Sur ejecutado.",
            f"Job: {payload.get('job_id')}",
            f"Modulo: {payload.get('module')}",
            f"Ambiente: {payload.get('environment')}",
            f"Etapa final: {payload.get('stage')}",
            f"Memgraph: {'OK' if payload.get('memgraph_ingested') else 'NO INGESTADO'}",
            f"Reporte: {payload.get('report_md')}",
            "",
            "Repos evaluados:",
        ]
        if not repos:
            lines.append("- Ningun repo reportado.")
        for repo in repos:
            if isinstance(repo, dict):
                lines.append(
                    "- {name}: clone={clone_ok} dotnet={dotnet} frontend={frontend} gateway={gateway} "
                    "projects={projects} endpoints={endpoints} nugets={nugets} checks_failed={checks_failed}".format(**repo)
                )
            else:
                lines.append(f"- {repo}")
        lines.append("")
        lines.append("Hallazgos:")
        if not findings:
            lines.append("- Sin hallazgos bloqueantes en esta pasada.")
        for finding in findings:
            if isinstance(finding, dict):
                lines.append(f"- [{finding.get('severity')}] {finding.get('area')}: {finding.get('title')}")
            else:
                lines.append(f"- {finding}")
        message = Message(text="\n".join(lines))
        self.status = message
        return message
'''


def stage_component_code(class_name: str, display_name: str, endpoint: str) -> str:
    return f'''
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

try:
    from langflow.custom import Component
    from langflow.io import DataInput, Output
    from langflow.schema.data import Data
except ImportError:
    from lfx.custom.custom_component.component import Component
    from lfx.inputs.inputs import HandleInput as DataInput
    from lfx.schema.data import Data
    from lfx.template.field.base import Output

RUNNER_BASE_URL = os.environ.get("QA_RUNNER_URL", "http://qa-runner.local:8090")


class {class_name}(Component):
    display_name = {display_name!r}
    description = "Ejecuta una etapa real del runner QA Electro Sur."
    icon = "Workflow"
    name = {class_name!r}

    inputs = [
        DataInput(
            name="input_data",
            display_name="Entrada de etapa",
            input_types=["Data", "JSON"],
            required=True,
        )
    ]

    outputs = [
        Output(display_name="Salida de etapa", name="stage_data", method="run_stage"),
    ]

    def _payload(self):
        value = self.input_data
        if isinstance(value, Data):
            value = value.data
        if isinstance(value, dict) and "result" in value:
            return value["result"]
        return value if isinstance(value, dict) else {{"raw": str(value or "")}}

    def run_stage(self) -> Data:
        payload = self._payload()
        if payload.get("status") == "error":
            self.status = payload.get("error", "Etapa previa fallo.")
            return Data(data=payload)

        url = f"{{RUNNER_BASE_URL}}{endpoint}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={{"Content-Type": "application/json"}},
            method="POST",
        )
        try:
            with urlopen(request, timeout=1260) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            result = {{
                "status": "error",
                "stage": {display_name!r},
                "http_status": exc.code,
                "error": exc.read().decode("utf-8", errors="replace"),
                "url": url,
                "input_keys": list(payload.keys()),
            }}
        except Exception as exc:
            result = {{
                "status": "error",
                "stage": {display_name!r},
                "error": str(exc),
                "url": url,
                "input_keys": list(payload.keys()) if isinstance(payload, dict) else [],
            }}

        self.status = result.get("message") or result.get("status") or str(result)[:300]
        return Data(data=result)
'''


def get_basic_examples() -> list[dict]:
    with urlopen(f"{LANGFLOW_URL}/api/v1/flows/basic_examples/", timeout=30) as response:
        body = response.read()
    if body.startswith(b"\x1f\x8b"):
        body = gzip.decompress(body)
    return json.loads(body.decode("utf-8"))


def find_node(examples: list[dict], display_name: str) -> dict:
    for flow in examples:
        for node in flow.get("data", {}).get("nodes", []):
            if node.get("data", {}).get("node", {}).get("display_name") == display_name:
                return copy.deepcopy(node)
    raise RuntimeError(f"No encontre nodo base {display_name!r}.")


def encoded_handle(handle: dict, compact: bool = False) -> str:
    def enc(value):
        if isinstance(value, list):
            items = ",".join(f"œ{item}œ" for item in value) if compact else ", ".join(f"œ{item}œ" for item in value)
            return f"[{items}]"
        return f"œ{value}œ"

    sep = "," if compact else ", "
    inner = sep.join(f"œ{key}œ:{enc(value)}" if compact else f"œ{key}œ: {enc(value)}" for key, value in handle.items())
    return "{" + inner + "}"


def make_edge(source: str, target: str, source_type: str, source_name: str, source_outputs: list[str], target_field: str, target_inputs: list[str], target_type: str) -> dict:
    source_handle = {
        "dataType": source_type,
        "id": source,
        "name": source_name,
        "output_types": source_outputs,
    }
    target_handle = {
        "fieldName": target_field,
        "id": target,
        "inputTypes": target_inputs,
        "type": target_type,
    }
    return {
        "animated": False,
        "className": "",
        "data": {"sourceHandle": source_handle, "targetHandle": target_handle},
        "id": f"xy-edge__{source}{encoded_handle(source_handle, compact=True)}-{target}{encoded_handle(target_handle, compact=True)}",
        "source": source,
        "sourceHandle": encoded_handle(source_handle),
        "target": target,
        "targetHandle": encoded_handle(target_handle),
    }


def patch_chat_input(node: dict) -> dict:
    node["id"] = "ChatInput-QAJob"
    node["position"] = {"x": -620, "y": 120}
    node["selected"] = False
    node["data"]["id"] = node["id"]
    node["data"]["node"]["template"]["input_value"]["value"] = json.dumps(EXAMPLE_JOB, indent=2, ensure_ascii=False)
    node["data"]["node"]["template"]["input_value"]["placeholder"] = "Pega aqui el QA Job JSON real."
    return node


def patch_chat_output(node: dict) -> dict:
    node["id"] = "ChatOutput-QAReport"
    node["position"] = {"x": 3370, "y": 120}
    node["selected"] = False
    node["data"]["id"] = node["id"]
    node["data"]["node"]["template"]["sender_name"]["value"] = "QA Electro Sur"
    return node


def make_intake_node(parser_template: dict) -> dict:
    node = copy.deepcopy(parser_template)
    node["id"] = "ElectroSurJobIntake-00"
    node["position"] = {"x": -180, "y": 120}
    node["selected"] = False

    data = node["data"]
    data["id"] = node["id"]
    data["type"] = "ElectroSurJobIntake"
    data["selected_output"] = "job_data"
    data["display_name"] = "00 Intake JSON Electro Sur"
    data["description"] = "Valida el pedido y lo convierte en Data."

    inner = data["node"]
    inner["display_name"] = "00 Intake JSON Electro Sur"
    inner["description"] = "Valida el pedido de QA y lo convierte en datos para la tuberia."
    inner["icon"] = "ClipboardList"
    inner["key"] = "ElectroSurJobIntake"
    inner["name"] = "ElectroSurJobIntake"
    inner["base_classes"] = ["Data", "JSON"]
    inner["field_order"] = ["job_json"]
    inner["outputs"] = [
        {
            "allows_loop": False,
            "cache": True,
            "display_name": "Job Data",
            "group_outputs": False,
            "method": "parse_job",
            "name": "job_data",
            "selected": "Data",
            "tool_mode": True,
            "types": ["Data"],
            "value": "__UNDEFINED__",
        }
    ]

    code = copy.deepcopy(inner["template"]["code"])
    code["value"] = INTAKE_COMPONENT_CODE
    code["code"] = INTAKE_COMPONENT_CODE
    inner["template"] = {
        "_type": "Component",
        "code": code,
        "job_json": {
            "_input_type": "MultilineInput",
            "advanced": False,
            "display_name": "QA Job JSON",
            "dynamic": False,
            "info": "JSON con repos, ambiente, targets y flags de ejecucion.",
            "input_types": ["Message", "Text"],
            "list": False,
            "list_add_label": "Add More",
            "load_from_db": False,
            "multiline": True,
            "name": "job_json",
            "override_skip": False,
            "placeholder": json.dumps(EXAMPLE_JOB, indent=2, ensure_ascii=False),
            "required": True,
            "show": True,
            "title_case": False,
            "tool_mode": False,
            "trace_as_input": True,
            "track_in_telemetry": False,
            "type": "str",
            "value": json.dumps(EXAMPLE_JOB, indent=2, ensure_ascii=False),
        },
    }
    return node


def make_formatter_node(parser_template: dict) -> dict:
    node = copy.deepcopy(parser_template)
    node["id"] = "ElectroSurQaFormatter-08"
    node["position"] = {"x": 2980, "y": 120}
    node["selected"] = False

    data = node["data"]
    data["id"] = node["id"]
    data["type"] = "ElectroSurQaFormatter"
    data["selected_output"] = "summary"
    data["display_name"] = "08 Formatear Resumen QA"
    data["description"] = "Formatea el resultado operativo del runner."

    inner = data["node"]
    inner["display_name"] = "08 Formatear Resumen QA"
    inner["description"] = "Convierte la respuesta del runner en un mensaje limpio para el chat."
    inner["icon"] = "FileText"
    inner["key"] = "ElectroSurQaFormatter"
    inner["name"] = "ElectroSurQaFormatter"
    inner["base_classes"] = ["Message"]
    inner["field_order"] = ["input_data"]
    inner["outputs"] = [
        {
            "allows_loop": False,
            "cache": True,
            "display_name": "Resumen",
            "group_outputs": False,
            "method": "format_summary",
            "name": "summary",
            "selected": "Message",
            "tool_mode": True,
            "types": ["Message"],
            "value": "__UNDEFINED__",
        }
    ]

    code = copy.deepcopy(inner["template"]["code"])
    code["value"] = FORMATTER_COMPONENT_CODE
    code["code"] = FORMATTER_COMPONENT_CODE
    inner["template"] = {
        "_type": "Component",
        "code": code,
        "input_data": {
            "_input_type": "HandleInput",
            "advanced": False,
            "display_name": "Resultado del Runner",
            "dynamic": False,
            "info": "Respuesta Data/JSON de la etapa 07 Reporte Final.",
            "input_types": ["Data", "JSON"],
            "list": False,
            "list_add_label": "Add More",
            "name": "input_data",
            "override_skip": False,
            "placeholder": "",
            "required": True,
            "show": True,
            "title_case": False,
            "tool_mode": False,
            "trace_as_input": True,
            "track_in_telemetry": False,
            "type": "other",
            "value": "",
        },
    }
    return node


def make_stage_node(parser_template: dict, node_id: str, class_name: str, label: str, url: str, x: int) -> dict:
    node = copy.deepcopy(parser_template)
    node["id"] = node_id
    node["position"] = {"x": x, "y": 120}
    node["selected"] = False

    data = node["data"]
    data["id"] = node_id
    data["type"] = class_name
    data["selected_output"] = "stage_data"
    data["display_name"] = label

    inner = data["node"]
    inner["display_name"] = label
    inner["description"] = "Ejecuta una etapa real del runner QA Electro Sur."
    inner["icon"] = "Workflow"
    inner["key"] = class_name
    inner["name"] = class_name
    inner["base_classes"] = ["Data", "JSON"]
    inner["field_order"] = ["input_data"]
    inner["outputs"] = [
        {
            "allows_loop": False,
            "cache": True,
            "display_name": "Salida de etapa",
            "group_outputs": False,
            "method": "run_stage",
            "name": "stage_data",
            "selected": "Data",
            "tool_mode": True,
            "types": ["Data"],
            "value": "__UNDEFINED__",
        }
    ]

    code = copy.deepcopy(inner["template"]["code"])
    code["value"] = stage_component_code(class_name, label, url)
    code["code"] = code["value"]
    inner["template"] = {
        "_type": "Component",
        "code": code,
        "input_data": {
            "_input_type": "HandleInput",
            "advanced": False,
            "display_name": "Entrada de etapa",
            "dynamic": False,
            "info": "Data/JSON de la etapa anterior.",
            "input_types": ["Data", "JSON"],
            "list": False,
            "list_add_label": "Add More",
            "name": "input_data",
            "override_skip": False,
            "placeholder": "",
            "required": True,
            "show": True,
            "title_case": False,
            "tool_mode": False,
            "trace_as_input": True,
            "track_in_telemetry": False,
            "type": "other",
            "value": "",
        },
    }
    return node


def build_flow() -> dict:
    examples = get_basic_examples()
    chat_input = patch_chat_input(find_node(examples, "Chat Input"))
    chat_output = patch_chat_output(find_node(examples, "Chat Output"))
    parser_template = find_node(examples, "Parser")
    intake = make_intake_node(parser_template)
    formatter = make_formatter_node(parser_template)

    stages = [
        ("ElectroSurStage01Start", "01 Crear Corrida QA", "http://qa-runner.local:8090/pipeline/start"),
        ("ElectroSurStage02Clone", "02 Descargar Repos", "http://qa-runner.local:8090/pipeline/clone"),
        ("ElectroSurStage03Inspect", "03 Inventario C#/Front/Gateway", "http://qa-runner.local:8090/pipeline/inspect"),
        ("ElectroSurStage04Dotnet", "04 Restore Build Test .NET", "http://qa-runner.local:8090/pipeline/dotnet"),
        ("ElectroSurStage05Smoke", "05 Smoke Gateway UI", "http://qa-runner.local:8090/pipeline/smoke"),
        ("ElectroSurStage06Graph", "06 Escribir Memgraph", "http://qa-runner.local:8090/pipeline/graph"),
        ("ElectroSurStage07Report", "07 Reporte Final", "http://qa-runner.local:8090/pipeline/report"),
    ]
    stage_nodes = [
        make_stage_node(parser_template, f"{class_name}-{index:02d}", class_name, label, url, 260 + index * 390)
        for index, (class_name, label, url) in enumerate(stages, start=1)
    ]

    edges = [
        make_edge("ChatInput-QAJob", "ElectroSurJobIntake-00", "ChatInput", "message", ["Message"], "job_json", ["Message", "Text"], "str"),
        make_edge("ElectroSurJobIntake-00", stage_nodes[0]["id"], "ElectroSurJobIntake", "job_data", ["Data"], "input_data", ["Data", "JSON"], "other"),
    ]
    for previous, current in zip(stage_nodes, stage_nodes[1:]):
        edges.append(make_edge(previous["id"], current["id"], previous["data"]["type"], "stage_data", ["Data"], "input_data", ["Data", "JSON"], "other"))
    edges.append(make_edge(stage_nodes[-1]["id"], "ElectroSurQaFormatter-08", stage_nodes[-1]["data"]["type"], "stage_data", ["Data"], "input_data", ["Data", "JSON"], "other"))
    edges.append(make_edge("ElectroSurQaFormatter-08", "ChatOutput-QAReport", "ElectroSurQaFormatter", "summary", ["Message"], "input_value", ["Data", "JSON", "DataFrame", "Table", "Message"], "str"))

    return {
        "name": FLOW_NAME,
        "description": "Pipeline visual real de QA: intake, clone, inventario, build/test, smoke, Memgraph y reporte.",
        "icon": "Workflow",
        "icon_bg_color": None,
        "gradient": None,
        "data": {
            "nodes": [chat_input, intake, *stage_nodes, formatter, chat_output],
            "edges": edges,
            "viewport": {"x": 100, "y": 80, "zoom": 0.55},
        },
        "tags": ["qa", "electrosur", "pipeline", "csharp", "memgraph"],
    }


def main() -> None:
    database_url = os.environ["LANGFLOW_DATABASE_URL"]
    engine = create_engine(database_url)
    metadata = MetaData()
    user_table = Table("user", metadata, autoload_with=engine)
    folder_table = Table("folder", metadata, autoload_with=engine)
    flow_table = Table("flow", metadata, autoload_with=engine)
    flow = build_flow()

    with engine.begin() as conn:
        user_row = conn.execute(select(user_table.c.id).where(user_table.c.username == TARGET_USERNAME)).mappings().first()
        if not user_row:
            raise RuntimeError(f"No encontre el usuario '{TARGET_USERNAME}' en LangFlow.")
        folder_row = conn.execute(select(folder_table.c.id).where(folder_table.c.user_id == user_row["id"]).limit(1)).mappings().first()
        if not folder_row:
            raise RuntimeError(f"No encontre carpeta para el usuario '{TARGET_USERNAME}'.")

        existing = conn.execute(
            select(flow_table.c.id).where(flow_table.c.user_id == user_row["id"], flow_table.c.name == FLOW_NAME)
        ).mappings().first()

        values = dict(
            user_id=user_row["id"],
            folder_id=folder_row["id"],
            name=flow["name"],
            description=flow["description"],
            icon=flow.get("icon"),
            icon_bg_color=flow.get("icon_bg_color"),
            gradient=flow.get("gradient"),
            is_component=False,
            updated_at=datetime.now(timezone.utc),
            webhook=False,
            endpoint_name=None,
            data=flow["data"],
            mcp_enabled=False,
            action_name=None,
            action_description=None,
            access_type="PRIVATE",
            tags=flow["tags"],
            locked=False,
            fs_path=None,
        )

        if existing:
            conn.execute(update(flow_table).where(flow_table.c.id == existing["id"]).values(**values))
        else:
            old = conn.execute(
                select(flow_table.c.id).where(flow_table.c.user_id == user_row["id"], flow_table.c.name.in_(OLD_FLOW_NAMES))
            ).mappings().first()
            if old:
                conn.execute(update(flow_table).where(flow_table.c.id == old["id"]).values(**values))
            else:
                conn.execute(
                    insert(flow_table).values(
                id=uuid.uuid4(),
                **values,
                    )
            )

    print(json.dumps({"status": "ok", "flow_name": FLOW_NAME, "nodes": len(flow["data"]["nodes"]), "edges": len(flow["data"]["edges"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
