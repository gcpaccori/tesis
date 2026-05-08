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
from sqlalchemy import MetaData, Table, create_engine, delete, insert, select


LANGFLOW_URL = os.environ.get("LANGFLOW_URL", "http://127.0.0.1:7860")
FLOW_NAME = os.environ.get("FLOW_NAME", "Kimi Q4 Long Agent - Local")
TARGET_USERNAME = os.environ.get("TARGET_USERNAME", "langflow")


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
    return all_types["kimi"]


def encoded_handle(handle: dict, compact: bool = False) -> str:
    def enc(value):
        if isinstance(value, list):
            items = ",".join(f"Å“{item}Å“" for item in value) if compact else ", ".join(f"Å“{item}Å“" for item in value)
            return f"[{items}]"
        return f"Å“{value}Å“"

    sep = "," if compact else ", "
    inner = sep.join(f"Å“{key}Å“:{enc(value)}" if compact else f"Å“{key}Å“: {enc(value)}" for key, value in handle.items())
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
    node["id"] = "ChatInput-KimiQ4"
    node["position"] = {"x": -620, "y": 120}
    node["selected"] = False
    node["data"]["id"] = node["id"]
    template = node["data"]["node"]["template"]
    template["input_value"]["value"] = "Confirma tu estado y explica como manejaras una corrida QA de 4000 pasos."
    template["input_value"]["placeholder"] = "Pide a Kimi Q4 una corrida larga, QA, arquitectura o plan de herramientas."
    return node


def patch_chat_output(node: dict) -> dict:
    node["id"] = "ChatOutput-KimiQ4"
    node["position"] = {"x": 600, "y": 120}
    node["selected"] = False
    node["data"]["id"] = node["id"]
    node["data"]["node"]["template"]["sender_name"]["value"] = "Kimi Q4 Long Agent"
    return node


def make_component_node(component: dict) -> dict:
    node = {
        "id": "KimiQ4LongAgent-01",
        "type": "genericNode",
        "position": {"x": -40, "y": 120},
        "selected": False,
        "dragging": False,
        "data": {
            "id": "KimiQ4LongAgent-01",
            "type": "KimiQ4LongAgent",
            "showNode": True,
            "selected_output": "message",
            "display_name": component["display_name"],
            "description": component.get("description", ""),
            "node": copy.deepcopy(component),
        },
    }
    template = node["data"]["node"]["template"]
    template["base_url"]["value"] = "http://kimi-q4-proxy.local:8031/v1"
    template["model"]["value"] = "kimi-k2.6-q4"
    template["max_tokens"]["value"] = 1800
    template["timeout_seconds"]["value"] = 900
    template["thinking"]["value"] = False
    return node


async def build_flow() -> dict:
    examples = get_basic_examples()
    custom = await custom_components()

    chat_input = patch_chat_input(find_basic_node(examples, "Chat Input"))
    chat_output = patch_chat_output(find_basic_node(examples, "Chat Output"))
    kimi_node = make_component_node(custom["KimiQ4LongAgent"])

    edges = [
        make_edge("ChatInput-KimiQ4", "KimiQ4LongAgent-01", "ChatInput", "message", ["Message"], "input_value", ["Message", "Text"], "str"),
        make_edge("KimiQ4LongAgent-01", "ChatOutput-KimiQ4", "KimiQ4LongAgent", "message", ["Message"], "input_value", ["Data", "JSON", "DataFrame", "Table", "Message"], "str"),
    ]

    return {
        "name": FLOW_NAME,
        "description": "Flujo local preconfigurado para Kimi 2.6 Q4 como cerebro de agente largo.",
        "icon": "BrainCircuit",
        "icon_bg_color": None,
        "gradient": None,
        "data": {
            "nodes": [chat_input, kimi_node, chat_output],
            "edges": edges,
            "viewport": {"x": 180, "y": 160, "zoom": 0.75},
        },
        "tags": ["kimi", "q4", "local", "long-agent", "qa"],
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
            raise RuntimeError(f"No encontre carpeta para el usuario '{TARGET_USERNAME}'.")

        conn.execute(delete(flow_table).where(flow_table.c.user_id == user_row["id"], flow_table.c.name == FLOW_NAME))
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

    print(json.dumps({"status": "ok", "flow_name": FLOW_NAME, "model": "kimi-k2.6-q4"}))


if __name__ == "__main__":
    asyncio.run(main())
