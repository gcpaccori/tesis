import copy
import json
import os
import uuid
from datetime import datetime, timezone

import requests
from sqlalchemy import MetaData, Table, create_engine, delete, insert, select


LANGFLOW_URL = os.environ.get("LANGFLOW_URL", "http://127.0.0.1:7860")
FLOW_NAME = os.environ.get("FLOW_NAME", "QA C# Basico - Gemma 31B")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemma4:31b")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
TARGET_USERNAME = os.environ.get("TARGET_USERNAME", "langflow")

C_SHARP_QA_PROMPT = """Eres un QA tecnico especializado en C# y .NET.

Tu tarea es revisar codigo, diffs o descripciones de bugs y devolver una auditoria corta pero util.

Prioridades:
1. Bugs funcionales y regresiones probables.
2. Nullability, excepciones no controladas y contratos rotos.
3. Async/await incorrecto, deadlocks, falta de CancellationToken y uso dudoso de Task.Result/Wait().
4. Errores comunes de ASP.NET Core, EF Core, LINQ, serializacion, DI y autenticacion/autorizacion.
5. Problemas de validacion, seguridad basica, concurrencia y manejo de configuracion.
6. Casos de prueba faltantes para backend, controladores, servicios y repositorios.

Reglas de respuesta:
- Responde en espanol.
- Empieza por hallazgos concretos.
- Si el usuario comparte codigo con lineas visibles, referencia archivo o linea cuando sea posible.
- Si no hay hallazgos claros, di exactamente: 'Sin hallazgos criticos por ahora.'
- Luego lista riesgos residuales y pruebas recomendadas.
- No inventes archivos ni comportamientos que no existan en la entrada.

Formato:
Hallazgos:
- [Alta|Media|Baja] hallazgo

Pruebas sugeridas:
- prueba o validacion

Si falta contexto, pide solo lo minimo necesario al final.
"""


def get_basic_prompting_template() -> dict:
    response = requests.get(f"{LANGFLOW_URL}/api/v1/flows/basic_examples/", timeout=30)
    response.raise_for_status()
    examples = response.json()
    for flow in examples:
        if flow.get("name") == "Basic Prompting":
            return flow
    raise RuntimeError("No encontre la plantilla 'Basic Prompting' en LangFlow.")


def ollama_model_option() -> dict:
    return {
        "name": MODEL_NAME,
        "icon": "Ollama",
        "category": "Ollama",
        "provider": "Ollama",
        "metadata": {
            "context_length": 262144,
            "model_class": "ChatOllama",
            "model_name_param": "model",
            "base_url_param": "base_url",
        },
    }


def patch_language_model_node(flow: dict) -> None:
    option = ollama_model_option()
    for node in flow["data"]["nodes"]:
        node_data = node.get("data", {})
        inner_node = node_data.get("node", {})
        if inner_node.get("display_name") != "Language Model":
            continue

        template = inner_node["template"]
        template["model"]["options"] = [option]
        template["model"]["value"] = [option]
        template["model"]["placeholder"] = MODEL_NAME
        template["ollama_base_url"]["value"] = OLLAMA_BASE_URL
        template["ollama_base_url"]["load_from_db"] = False
        if "temperature" in template:
            template["temperature"]["value"] = 0.1
        if "stream" in template:
            template["stream"]["value"] = False
        if "max_tokens" in template:
            template["max_tokens"]["value"] = 1400

        node_data["selected_output"] = "text_output"
        break
    else:
        raise RuntimeError("No encontre el nodo 'Language Model' para configurarlo.")


def patch_prompt_node(flow: dict) -> None:
    for node in flow["data"]["nodes"]:
        node_data = node.get("data", {})
        inner_node = node_data.get("node", {})
        if inner_node.get("display_name") != "Prompt Template":
            continue
        template = inner_node.get("template", {})
        if "template" in template:
            template["template"]["value"] = C_SHARP_QA_PROMPT
            break


def patch_chat_input_node(flow: dict) -> None:
    extra_types = [
        "cs",
        "csproj",
        "sln",
        "cshtml",
        "razor",
        "config",
        "xml",
        "yml",
        "yaml",
        "json",
    ]
    for node in flow["data"]["nodes"]:
        node_data = node.get("data", {})
        inner_node = node_data.get("node", {})
        if inner_node.get("display_name") != "Chat Input":
            continue

        template = inner_node["template"]
        if "input_value" in template:
            template["input_value"]["placeholder"] = (
                "Pega aqui un controller, service, repository, test o describe el bug de C#/.NET."
            )
        if "files" in template:
            current = template["files"].get("fileTypes", [])
            merged = list(dict.fromkeys(current + extra_types))
            template["files"]["fileTypes"] = merged
        break


def main() -> None:
    database_url = os.environ["LANGFLOW_DATABASE_URL"]
    engine = create_engine(database_url)
    metadata = MetaData()
    user_table = Table("user", metadata, autoload_with=engine)
    folder_table = Table("folder", metadata, autoload_with=engine)
    flow_table = Table("flow", metadata, autoload_with=engine)

    flow = copy.deepcopy(get_basic_prompting_template())
    flow["name"] = FLOW_NAME
    flow["description"] = "Flujo basico de QA real para revisar codigo C#/.NET con Gemma 31B."
    flow["tags"] = ["qa", "csharp", "dotnet", "backend", "ollama", "gemma4"]
    patch_language_model_node(flow)
    patch_prompt_node(flow)
    patch_chat_input_node(flow)

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
                "model": MODEL_NAME,
                "ollama_base_url": OLLAMA_BASE_URL,
                "username": TARGET_USERNAME,
            }
        )
    )


if __name__ == "__main__":
    main()
