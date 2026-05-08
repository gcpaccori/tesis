import asyncio
import copy
import gzip
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.request import urlopen

from langflow.interface.components import get_and_cache_all_types_dict
from langflow.services.deps import get_settings_service
from sqlalchemy import MetaData, Table, create_engine, insert, select, update


LANGFLOW_URL = os.environ.get("LANGFLOW_URL", "http://127.0.0.1:7860")
FLOW_NAME = os.environ.get("FLOW_NAME", "QA Electro Sur - Pipeline Real")
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
        }
    ],
    "qa_targets": [
        {
            "name": "gateway-health",
            "url": "https://qa-gateway.empresa.local/health",
            "expected_status": 200,
            "through_gateway": True,
        }
    ],
    "notes": "Reemplazar repos/branches/URLs por los reales de Electro Sur.",
    "run_builds": True,
    "run_tests": True,
    "run_frontend_build": False,
    "max_seconds": 900,
}


def get_basic_examples() -> list[dict]:
    with urlopen(f"{LANGFLOW_URL}/api/v1/flows/basic_examples/", timeout=30) as response:
        body = response.read()
    if body.startswith(b"\x1f\x8b"):
        body = gzip.decompress(body)
    return json.loads(body.decode("utf-8"))


def find_basic_node(examples: list[dict], display_name: str) -> dict:
    for flow in examples:
        for node in flow.get("data", {}).get("nodes", []):
            if node.get("data", {}).get("node", {}).get("display_name") == display_name:
                return copy.deepcopy(node)
    raise RuntimeError(f"No encontre nodo base {display_name!r}.")


async def custom_components() -> dict:
    all_types = await get_and_cache_all_types_dict(get_settings_service())
    return all_types["electrosur"]


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
    node["position"] = {"x": -650, "y": 160}
    node["selected"] = False
    node["data"]["id"] = node["id"]
    node["data"]["node"]["template"]["input_value"]["value"] = json.dumps(EXAMPLE_JOB, indent=2, ensure_ascii=False)
    node["data"]["node"]["template"]["input_value"]["placeholder"] = "Pega aqui el QA Job JSON real."
    return node


def patch_chat_output(node: dict) -> dict:
    node["id"] = "ChatOutput-QAReport"
    node["position"] = {"x": 3400, "y": 160}
    node["selected"] = False
    node["data"]["id"] = node["id"]
    node["data"]["node"]["template"]["sender_name"]["value"] = "QA Electro Sur"
    return node


def make_component_node(component: dict, node_id: str, component_type: str, selected_output: str, x: int) -> dict:
    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": 160},
        "selected": False,
        "dragging": False,
        "data": {
            "id": node_id,
            "type": component_type,
            "showNode": True,
            "selected_output": selected_output,
            "display_name": component["display_name"],
            "description": component.get("description", ""),
            "node": copy.deepcopy(component),
        },
    }


async def build_flow() -> dict:
    examples = get_basic_examples()
    custom = await custom_components()

    chat_input = patch_chat_input(find_basic_node(examples, "Chat Input"))
    chat_output = patch_chat_output(find_basic_node(examples, "Chat Output"))

    specs = [
        ("ElectroSurJobIntake", "ElectroSurJobIntake-00", "job_data"),
        ("ElectroSurStageStart", "ElectroSurStageStart-01", "stage_data"),
        ("ElectroSurStageClone", "ElectroSurStageClone-02", "stage_data"),
        ("ElectroSurStageInspect", "ElectroSurStageInspect-03", "stage_data"),
        ("ElectroSurStageDotnet", "ElectroSurStageDotnet-04", "stage_data"),
        ("ElectroSurStageSmoke", "ElectroSurStageSmoke-05", "stage_data"),
        ("ElectroSurStageGraph", "ElectroSurStageGraph-06", "stage_data"),
        ("ElectroSurStageReport", "ElectroSurStageReport-07", "stage_data"),
        ("ElectroSurQaFormatter", "ElectroSurQaFormatter-08", "summary"),
    ]
    nodes = [
        make_component_node(custom[component_type], node_id, component_type, selected_output, -210 + index * 390)
        for index, (component_type, node_id, selected_output) in enumerate(specs)
    ]

    edges = [
        make_edge("ChatInput-QAJob", "ElectroSurJobIntake-00", "ChatInput", "message", ["Message"], "job_json", ["Message", "Text"], "str"),
        make_edge("ElectroSurJobIntake-00", "ElectroSurStageStart-01", "ElectroSurJobIntake", "job_data", ["JSON"], "input_data", ["Data", "JSON"], "other"),
    ]
    for (source_type, source_id, _), (target_type, target_id, _) in zip(specs[1:8], specs[2:9]):
        edges.append(make_edge(source_id, target_id, source_type, "stage_data", ["JSON"], "input_data", ["Data", "JSON"], "other"))
    edges.append(make_edge("ElectroSurQaFormatter-08", "ChatOutput-QAReport", "ElectroSurQaFormatter", "summary", ["Message"], "input_value", ["Data", "JSON", "DataFrame", "Table", "Message"], "str"))

    return {
        "name": FLOW_NAME,
        "description": "Pipeline QA Electro Sur compatible con LangFlow 1.9: custom components por archivo, JSON/Data tipado y memoria Memgraph.",
        "icon": "Workflow",
        "icon_bg_color": None,
        "gradient": None,
        "data": {
            "nodes": [chat_input, *nodes, chat_output],
            "edges": edges,
            "viewport": {"x": 80, "y": 120, "zoom": 0.5},
        },
        "tags": ["qa", "electrosur", "langflow-1.9", "csharp", "memgraph"],
    }


async def main() -> None:
    flow = await build_flow()
    database_url = os.environ["LANGFLOW_DATABASE_URL"]
    engine = create_engine(database_url)
    metadata = MetaData()
    user_table = Table("user", metadata, autoload_with=engine)
    folder_table = Table("folder", metadata, autoload_with=engine)
    flow_table = Table("flow", metadata, autoload_with=engine)

    with engine.begin() as conn:
        user_row = conn.execute(select(user_table.c.id).where(user_table.c.username == TARGET_USERNAME)).mappings().first()
        if not user_row:
            raise RuntimeError(f"No encontre el usuario '{TARGET_USERNAME}' en LangFlow.")
        folder_row = conn.execute(select(folder_table.c.id).where(folder_table.c.user_id == user_row["id"]).limit(1)).mappings().first()
        if not folder_row:
            raise RuntimeError(f"No encontre carpeta para '{TARGET_USERNAME}'.")

        values = dict(
            user_id=user_row["id"],
            folder_id=folder_row["id"],
            name=flow["name"],
            description=flow["description"],
            icon=flow["icon"],
            icon_bg_color=flow["icon_bg_color"],
            gradient=flow["gradient"],
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
        existing = conn.execute(select(flow_table.c.id).where(flow_table.c.user_id == user_row["id"], flow_table.c.name == FLOW_NAME)).mappings().first()
        if existing:
            conn.execute(update(flow_table).where(flow_table.c.id == existing["id"]).values(**values))
            flow_id = existing["id"]
        else:
            flow_id = uuid.uuid4()
            conn.execute(insert(flow_table).values(id=flow_id, **values))

    print(json.dumps({"status": "ok", "flow_id": str(flow_id), "flow_name": FLOW_NAME, "nodes": len(flow["data"]["nodes"]), "edges": len(flow["data"]["edges"])}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
