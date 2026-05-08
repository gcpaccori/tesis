import copy
import gzip
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.request import urlopen

from sqlalchemy import MetaData, Table, create_engine, delete, insert, select


LANGFLOW_URL = os.environ.get("LANGFLOW_URL", "http://127.0.0.1:7860")
FLOW_NAME = os.environ.get("FLOW_NAME", "QA Electro Sur - Runner Operativo")
TARGET_USERNAME = os.environ.get("TARGET_USERNAME", "langflow")
QA_RUNNER_URL = os.environ.get("QA_RUNNER_URL", "http://qa-runner:8090")


RUNNER_COMPONENT_CODE = r'''
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lfx.custom.custom_component.component import Component
from lfx.io import MultilineInput, Output
from lfx.schema.message import Message


class ElectroSurQaRunner(Component):
    display_name = "Electro Sur QA Runner"
    description = "Clona repos, ejecuta build/test/smoke C# y genera reporte operativo."
    icon = "Hammer"
    name = "ElectroSurQaRunner"

    inputs = [
        MultilineInput(
            name="job_json",
            display_name="QA Job JSON",
            info="Pega un JSON con module, environment, repos, qa_targets y flags de ejecucion.",
            input_types=["Message", "Text"],
            value="",
            required=True,
        ),
    ]

    outputs = [
        Output(display_name="Resultado QA", name="result", method="run_job"),
    ]

    def _coerce_text(self, value):
        if hasattr(value, "text"):
            return value.text
        return str(value or "")

    def run_job(self) -> Message:
        raw = self._coerce_text(self.job_json).strip()
        if not raw:
            raise ValueError("Pega un QA Job JSON antes de ejecutar.")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"QA Job JSON invalido: {exc}") from exc

        body = json.dumps(payload).encode("utf-8")
        request = Request(
            "http://qa-runner:8090/jobs",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=max(int(payload.get("max_seconds", 900)) + 60, 120)) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"qa-runner HTTP {exc.code}: {error_body}") from exc

        summary = [
            "QA operativo ejecutado.",
            f"job_id: {result.get('job_id')}",
            f"status: {result.get('status')}",
            f"report_md: {result.get('report_md')}",
            f"report_json: {result.get('report_json')}",
            f"memgraph_cypher: {result.get('memgraph_cypher')}",
        ]
        findings = result.get("findings") or []
        if findings:
            summary.append("")
            summary.append("Hallazgos:")
            summary.extend(f"- {item}" for item in findings)
        else:
            summary.append("")
            summary.append("Sin hallazgos bloqueantes en esta pasada.")

        message = Message(text="\n".join(summary), data={"qa_result": result})
        self.status = message
        return message
'''


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
    "notes": "Cambiar repos/branches/URLs por los reales antes de ejecutar.",
    "run_builds": True,
    "run_tests": True,
    "run_frontend_build": False,
    "max_seconds": 900,
}


def get_basic_prompting_template() -> dict:
    with urlopen(f"{LANGFLOW_URL}/api/v1/flows/basic_examples/", timeout=30) as response:
        body = response.read()
        if body.startswith(b"\x1f\x8b"):
            body = gzip.decompress(body)
        examples = json.loads(body.decode("utf-8"))
    for flow in examples:
        if flow.get("name") == "Basic Prompting":
            return flow
    raise RuntimeError("No encontre la plantilla 'Basic Prompting' en LangFlow.")


def node_by_display(flow: dict, display_name: str) -> dict:
    for node in flow["data"]["nodes"]:
        if node.get("data", {}).get("node", {}).get("display_name") == display_name:
            return copy.deepcopy(node)
    raise RuntimeError(f"No encontre nodo {display_name!r}.")


def edge(source: str, target: str, source_type: str, source_name: str, target_field: str, target_type: str) -> dict:
    source_handle = {
        "dataType": source_type,
        "id": source,
        "name": source_name,
        "output_types": ["Message"],
    }
    target_handle = {
        "fieldName": target_field,
        "id": target,
        "inputTypes": ["Message", "Text"] if target_type == "str" else ["Data", "JSON", "DataFrame", "Table", "Message"],
        "type": target_type,
    }
    return {
        "animated": False,
        "className": "",
        "data": {"sourceHandle": source_handle, "targetHandle": target_handle},
        "id": f"reactflow__edge-{source}-{target}-{target_field}",
        "selected": False,
        "source": source,
        "sourceHandle": json.dumps(source_handle, ensure_ascii=False),
        "target": target,
        "targetHandle": json.dumps(target_handle, ensure_ascii=False),
    }


def make_runner_node(prompt_node: dict) -> dict:
    runner = copy.deepcopy(prompt_node)
    runner["id"] = "ElectroSurQaRunner-001"
    runner["position"] = {"x": 520, "y": 140}
    runner["selected"] = False

    node_data = runner["data"]
    node_data["id"] = runner["id"]
    node_data["type"] = "ElectroSurQaRunner"
    node_data["selected_output"] = "result"
    node_data["display_name"] = "Electro Sur QA Runner"
    node_data["description"] = "Ejecuta QA operativo real via qa-runner."

    inner = node_data["node"]
    inner["display_name"] = "Electro Sur QA Runner"
    inner["description"] = "Clona repos, ejecuta build/test/smoke C# y genera reportes."
    inner["documentation"] = ""
    inner["icon"] = "Hammer"
    inner["name"] = "ElectroSurQaRunner"
    inner["base_classes"] = ["Message"]
    inner["outputs"] = [
        {
            "allows_loop": False,
            "cache": False,
            "display_name": "Resultado QA",
            "group_outputs": False,
            "method": "run_job",
            "name": "result",
            "selected": "Message",
            "tool_mode": True,
            "types": ["Message"],
            "value": "__UNDEFINED__",
        }
    ]

    code_field = copy.deepcopy(inner["template"]["code"])
    code_field["value"] = RUNNER_COMPONENT_CODE
    code_field["code"] = RUNNER_COMPONENT_CODE
    code_field["code_hash"] = ""

    inner["template"] = {
        "_type": "Component",
        "code": code_field,
        "job_json": {
            "_input_type": "MultilineInput",
            "advanced": False,
            "display_name": "QA Job JSON",
            "dynamic": False,
            "info": "JSON con repos, ambiente, targets y flags. El chat input alimenta este campo.",
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
    return runner


def patch_chat_nodes(chat_input: dict, chat_output: dict) -> None:
    chat_input["id"] = "ChatInput-QAJob"
    chat_input["position"] = {"x": 120, "y": 150}
    chat_input["data"]["id"] = chat_input["id"]
    chat_input["data"]["node"]["template"]["input_value"]["value"] = json.dumps(EXAMPLE_JOB, indent=2, ensure_ascii=False)
    chat_input["data"]["node"]["template"]["input_value"]["placeholder"] = "Pega aqui el QA Job JSON real."

    chat_output["id"] = "ChatOutput-QAResult"
    chat_output["position"] = {"x": 940, "y": 150}
    chat_output["data"]["id"] = chat_output["id"]
    chat_output["data"]["node"]["template"]["sender_name"]["value"] = "QA Runner"


def build_flow() -> dict:
    source = get_basic_prompting_template()
    chat_input = node_by_display(source, "Chat Input")
    prompt = node_by_display(source, "Prompt Template")
    chat_output = node_by_display(source, "Chat Output")
    patch_chat_nodes(chat_input, chat_output)
    runner = make_runner_node(prompt)

    return {
        "name": FLOW_NAME,
        "description": "Flujo operativo: pega un QA Job JSON y ejecuta clone/build/test/smoke via qa-runner.",
        "icon": "Hammer",
        "icon_bg_color": None,
        "gradient": None,
        "data": {
            "nodes": [chat_input, runner, chat_output],
            "edges": [
                edge("ChatInput-QAJob", "ElectroSurQaRunner-001", "ChatInput", "message", "job_json", "str"),
                edge("ElectroSurQaRunner-001", "ChatOutput-QAResult", "ElectroSurQaRunner", "result", "input_value", "other"),
            ],
            "viewport": {"x": 0, "y": 0, "zoom": 0.8},
        },
        "tags": ["qa", "electrosur", "runner", "csharp"],
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
        user_row = conn.execute(
            select(user_table.c.id).where(user_table.c.username == TARGET_USERNAME)
        ).mappings().first()
        if not user_row:
            raise RuntimeError(f"No encontre el usuario '{TARGET_USERNAME}' en LangFlow.")

        folder_row = conn.execute(
            select(folder_table.c.id).where(folder_table.c.user_id == user_row["id"]).limit(1)
        ).mappings().first()
        if not folder_row:
            raise RuntimeError(f"No encontre carpeta para el usuario '{TARGET_USERNAME}'.")

        conn.execute(
            delete(flow_table).where(
                flow_table.c.user_id == user_row["id"],
                flow_table.c.name == FLOW_NAME,
            )
        )

        conn.execute(
            insert(flow_table).values(
                id=uuid.uuid4(),
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
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "flow_name": FLOW_NAME,
                "runner_url": QA_RUNNER_URL,
                "username": TARGET_USERNAME,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
