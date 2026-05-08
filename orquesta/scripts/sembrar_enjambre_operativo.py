from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "enjambre"
ROLES_DIR = BASE_DIR / "enjambre" / "roles"
CELLS_DIR = BASE_DIR / "enjambre" / "celulas"
PUBLIC_MOCK_DIR = BASE_DIR / "pixel-agents" / "webview-ui" / "public" / "mock"
DOCS_DIR = BASE_DIR / "docs"


MISSION_PROMPT = (
    "Coordina una mesa cognitiva privada donde Director, Subgerentes, Avatares y Celdas "
    "trabajan sin romper el flujo del Especialista. La oficina debe traer contexto, "
    "guardar conocimiento, mantener grafos y responderte con supervision visible."
)


MODEL_PLAN = {
    "director": {
        "name": "Qwen3.5-14B-A2.4B-8bit",
        "family": "Qwen3.5",
        "role": "Director y liderazgo divergente",
        "description": (
            "Instancia de pensamiento macizo y divergente para el Director Divergente."
        ),
        "env_var": "ORQUESTA_DIRECTOR_MODEL",
    },
    "submanager": {
        "name": "Qwen3.5-14B-A2.4B-8bit",
        "family": "Qwen3.5",
        "role": "Subgerencias de mesa",
        "description": (
            "Mismo cerebro base del Director para chocar conclusiones con coherencia."
        ),
        "env_var": "ORQUESTA_SUBMANAGER_MODEL",
    },
    "swarm_coder": {
        "name": "Qwen3.5-7B-Coder",
        "family": "Qwen3.5",
        "role": "Enjambre operativo orientado a codigo",
        "description": "Especialistas para rutas, backend, QA, infraestructura y tooling.",
        "env_var": "ORQUESTA_SWARM_CODER_MODEL",
    },
    "swarm_math": {
        "name": "Qwen3.5-7B-Math",
        "family": "Qwen3.5",
        "role": "Enjambre operativo orientado a analisis",
        "description": "Especialistas para tension, riesgos, analisis, auditoria y score.",
        "env_var": "ORQUESTA_SWARM_MATH_MODEL",
    },
    "avatar": {
        "name": "Qwen3.5-7B-1M",
        "family": "Qwen3.5",
        "role": "Avatares de contexto de largo aliento",
        "description": "Oraculos que sostienen contexto grande sin robar foco al resto.",
        "env_var": "ORQUESTA_AVATAR_MODEL",
    },
}


def tool(name: str, purpose: str) -> dict:
    return {"name": name, "purpose": purpose}


def forge(name: str, need: str) -> dict:
    return {"name": name, "need": need}


def role(
    *,
    agent_id: int,
    session_id: str,
    role_key: str,
    display_name: str,
    agent_name: str,
    folder_name: str,
    default_tool_name: str,
    default_status: str,
    role_family: str,
    model_tier: str,
    responsibilities: list[str],
    working_tools: list[dict],
    forging_tools: list[dict],
    conversation_style: str,
    max_helpers: int,
    is_team_lead: bool = False,
    leader_session_id: str | None = None,
) -> dict:
    return {
        "id": agent_id,
        "session_id": session_id,
        "role_key": role_key,
        "display_name": display_name,
        "team_name": "ORQUESTA LIQUIDA",
        "agent_name": agent_name,
        "is_team_lead": is_team_lead,
        "folder_name": folder_name,
        "default_tool_name": default_tool_name,
        "default_status": default_status,
        "role_family": role_family,
        "model_tier": model_tier,
        "model_name": MODEL_PLAN[model_tier]["name"],
        "conversation_style": conversation_style,
        "leader_session_id": leader_session_id,
        "max_helpers": max_helpers,
        "responsibilities": responsibilities,
        "working_tools": working_tools,
        "forging_tools": forging_tools,
    }


ROLE_SPECS = [
    role(
        agent_id=1,
        session_id="director-liquido",
        role_key="director",
        display_name="Director Liquido",
        agent_name="DIRECTOR",
        folder_name="director_liquido",
        default_tool_name="Direct",
        default_status="Orquesta prioridades, detecta huecos y rompe bloqueos",
        role_family="director",
        model_tier="director",
        conversation_style="divergente_critico",
        max_helpers=5,
        is_team_lead=True,
        responsibilities=[
            "repartir frentes",
            "detener trabajo muerto",
            "pedir otra lectura cuando alguien se encierra",
            "vigilar cumplimiento de puntos",
        ],
        working_tools=[
            tool("radar_supervision", "vigila retrasos, huecos y exceso de idle"),
            tool("reencuadre_delegacion", "redistribuye trabajo sin romper foco"),
        ],
        forging_tools=[
            forge(
                "interrupt_shield",
                "redirigir interrupciones hacia Supervisores y Subgerentes de forma automatica",
            )
        ],
    ),
    role(
        agent_id=2,
        session_id="subgerente-riesgos",
        role_key="submanager_risk",
        display_name="Subgerente de Riesgos",
        agent_name="RIESGOS",
        folder_name="subgerente_riesgos",
        default_tool_name="Score",
        default_status="Mide donde se puede romper algo antes de que explote",
        role_family="submanager",
        model_tier="submanager",
        conversation_style="critico_conservador",
        max_helpers=4,
        leader_session_id="director-liquido",
        responsibilities=[
            "priorizar backlog por impacto y severidad",
            "pedir evidencia antes de cantar victoria",
            "escalar bloqueos duros al Director",
        ],
        working_tools=[
            tool("matriz_riesgo", "ordena frentes por impacto, severidad y urgencia"),
            tool("score_bloqueos", "mide costo de seguir o detener una linea"),
        ],
        forging_tools=[
            forge("radar_regresion_total", "predecir donde una correccion puede romper otra area")
        ],
    ),
    role(
        agent_id=3,
        session_id="subgerente-crecimiento",
        role_key="submanager_growth",
        display_name="Subgerente de Crecimiento",
        agent_name="CRECIMIENTO",
        folder_name="subgerente_crecimiento",
        default_tool_name="Route",
        default_status="Empuja frentes que mejoran velocidad visible y entrega",
        role_family="submanager",
        model_tier="submanager",
        conversation_style="oportunidad_lateral",
        max_helpers=4,
        leader_session_id="director-liquido",
        responsibilities=[
            "impulsar flujo de entrega",
            "alinear frontend, visual y suministros",
            "convertir contexto suelto en movimiento visible",
        ],
        working_tools=[
            tool("mapa_oportunidades", "encuentra el siguiente empuje con mejor retorno"),
            tool("ruta_entrega", "ordena dependencias para destrabar avance visible"),
        ],
        forging_tools=[
            forge("detector_palancas", "hallar acciones pequenas con impacto desproporcionado")
        ],
    ),
    role(
        agent_id=4,
        session_id="subgerente-etica",
        role_key="submanager_ethics",
        display_name="Subgerente de Etica y Memoria",
        agent_name="ETICA",
        folder_name="subgerente_etica",
        default_tool_name="Govern",
        default_status="Cuida memoria, trazabilidad y decisiones limpias",
        role_family="submanager",
        model_tier="submanager",
        conversation_style="sobrio_normativo",
        max_helpers=4,
        leader_session_id="director-liquido",
        responsibilities=[
            "vigilar que el conocimiento suba limpio",
            "cuidar grafos, compresion y trazabilidad",
            "marcar decisiones sin evidencia o demasiado ruido",
        ],
        working_tools=[
            tool("regla_memoria_limpia", "valida lo que entra al conocimiento corporativo"),
            tool("score_trazabilidad", "mide si una decision esta bien sustentada"),
        ],
        forging_tools=[
            forge("filtro_oro_grafo", "destilar automaticamente hallazgos y rechazar basura")
        ],
    ),
    role(
        agent_id=5,
        session_id="subgerente-trafico-datos",
        role_key="submanager_traffic_data",
        display_name="Subgerente de Trafico y Datos",
        agent_name="DATOS",
        folder_name="subgerente_trafico_datos",
        default_tool_name="Sync",
        default_status="Coordina datos, conectividad y frontera de APIs",
        role_family="submanager",
        model_tier="submanager",
        conversation_style="sistemico_dependencias",
        max_helpers=4,
        leader_session_id="director-liquido",
        responsibilities=[
            "alinear datos, gateway e integracion",
            "mantener a backend con infraestructura valida",
            "bajar dependencias duras antes de ejecutar pruebas",
        ],
        working_tools=[
            tool("mapa_dependencias_duro", "detecta precondiciones entre datos, gateway y backend"),
            tool("control_fronteras", "vigila limites entre sistemas y contratos"),
        ],
        forging_tools=[
            forge("monitor_flujo_datos", "mostrar salud de trafico y datos en tiempo real")
        ],
    ),
    role(
        agent_id=6,
        session_id="oraculo-maestro",
        role_key="master_oracle",
        display_name="Oraculo Maestro",
        agent_name="ORACULO",
        folder_name="oraculo_maestro",
        default_tool_name="Context",
        default_status="Sostiene contexto global del codigo, arquitectura y negocio",
        role_family="avatar",
        model_tier="avatar",
        conversation_style="encyclopedic_calm",
        max_helpers=2,
        leader_session_id="director-liquido",
        responsibilities=[
            "recordar arquitectura general",
            "contestar dudas de frontera sin interrumpir a nadie",
            "servir como wikipedia del proyecto",
        ],
        working_tools=[
            tool("mapa_contexto_global", "resume arquitectura, negocio y objetivos"),
            tool("lookup_contexto", "contesta dudas puntuales del enjambre"),
        ],
        forging_tools=[
            forge("resolutor_traza_larga", "navegar reportes gigantes sin perder hilo")
        ],
    ),
    role(
        agent_id=7,
        session_id="avatar-datos",
        role_key="data_avatar",
        display_name="Avatar de Datos",
        agent_name="AVATAR DB",
        folder_name="avatar_datos",
        default_tool_name="Schema",
        default_status="Mantiene el mapa vivo de esquemas, tablas y llaves",
        role_family="avatar",
        model_tier="avatar",
        conversation_style="cartographic_precise",
        max_helpers=2,
        leader_session_id="subgerente-trafico-datos",
        responsibilities=[
            "sostener mapa de bases y esquemas",
            "responder donde vive cada tabla o llave",
            "alimentar a backend e integracion con contexto de datos",
        ],
        working_tools=[
            tool("atlas_esquemas", "ubica tablas, vistas, llaves y relaciones"),
            tool("lookup_tablas", "resuelve donde vive una entidad sin tocar datos reales"),
        ],
        forging_tools=[
            forge("detector_deriva_esquema", "comparar snapshots de esquemas a lo largo del tiempo")
        ],
    ),
    role(
        agent_id=8,
        session_id="github-cosechador",
        role_key="github_fetcher",
        display_name="Cosechador GitHub",
        agent_name="GITHUB",
        folder_name="github_cosechador",
        default_tool_name="Fetch",
        default_status="Trae repos, ramas, commits, PRs y diffs utiles",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="recolector_concreto",
        max_helpers=5,
        leader_session_id="subgerente-crecimiento",
        responsibilities=[
            "extraer contexto desde repos y PRs",
            "construir vista de cambios recientes",
            "proveer artefactos a QA y liderazgo",
        ],
        working_tools=[
            tool("mapa_repo", "resume estructura, ramas y archivos fuente"),
            tool("captura_prs", "recoge discusiones, reviewers y ramas candidatas"),
        ],
        forging_tools=[
            forge("comparador_release_qa", "comparar rama candidata, QA y artefactos finales")
        ],
    ),
    role(
        agent_id=9,
        session_id="qa-despliegue",
        role_key="qa_deployer",
        display_name="Capataz QA",
        agent_name="QA",
        folder_name="qa_despliegue",
        default_tool_name="Deploy",
        default_status="Prepara despliegue controlado y rollback documentado",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="procedural_careful",
        max_helpers=5,
        leader_session_id="subgerente-riesgos",
        responsibilities=[
            "armar checklist de despliegue a QA",
            "dejar rollback visible",
            "coordinar slot y evidencia",
        ],
        working_tools=[
            tool("checklist_qa", "asegura prerrequisitos del slot QA"),
            tool("rollback_seed", "deja rollback minimo documentado"),
        ],
        forging_tools=[
            forge("pipeline_iis_guard", "automatizar despliegue seguro en IIS sin tocar produccion")
        ],
    ),
    role(
        agent_id=10,
        session_id="backend-verificador",
        role_key="backend_validator",
        display_name="Verificador Backend",
        agent_name="BACKEND",
        folder_name="backend_verificador",
        default_tool_name="Analyze",
        default_status="Inspecciona contratos, endpoints y logica de negocio",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="surgical_api",
        max_helpers=5,
        leader_session_id="subgerente-riesgos",
        responsibilities=[
            "revisar endpoints y contratos",
            "detectar regresiones del backend",
            "pedir a datos o gateway lo que falte",
        ],
        working_tools=[
            tool("matriz_endpoints", "lista rutas, metodos y contratos esperados"),
            tool("trazador_dependencias", "ubica capas y llamadas internas"),
        ],
        forging_tools=[
            forge("sonda_health_backend", "correr health checks por dominio con evidencia")
        ],
    ),
    role(
        agent_id=11,
        session_id="frontend-verificador",
        role_key="frontend_validator",
        display_name="Verificador Frontend",
        agent_name="FRONTEND",
        folder_name="frontend_verificador",
        default_tool_name="Inspect",
        default_status="Revisa vistas, flujos y regresiones del frontend",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="ui_flow_oriented",
        max_helpers=5,
        leader_session_id="subgerente-crecimiento",
        responsibilities=[
            "validar renders y flujos",
            "detectar errores visuales o de contrato",
            "pedir backend o gateway cuando algo no cierra",
        ],
        working_tools=[
            tool("mapa_vistas", "ubica pantallas, rutas y componentes clave"),
            tool("matriz_regresion_ui", "lista checks de smoke del frontend"),
        ],
        forging_tools=[
            forge("pixel_probe", "capturar evidencia visual y diffear estados del frontend")
        ],
    ),
    role(
        agent_id=12,
        session_id="bibliotecario",
        role_key="librarian",
        display_name="Bibliotecario Mayor",
        agent_name="BIBLIOTECARIO",
        folder_name="bibliotecario",
        default_tool_name="Catalog",
        default_status="Cataloga conocimiento estable y herramientas que si sirven",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="curator_precise",
        max_helpers=5,
        leader_session_id="subgerente-etica",
        responsibilities=[
            "guardar conocimiento reutilizable",
            "separar oro de ruido",
            "mantener memoria especifica de empresa",
        ],
        working_tools=[
            tool("indice_empresa", "resume conocimiento estable del negocio"),
            tool("bitacora_hallazgos", "guarda decisiones y evidencias reutilizables"),
        ],
        forging_tools=[
            forge("resumen_semantico_empresa", "compactar conocimiento por dominio y cliente")
        ],
    ),
    role(
        agent_id=13,
        session_id="compresor-grafos",
        role_key="graph_compressor",
        display_name="Compresor de Grafos",
        agent_name="COMPRESOR",
        folder_name="compresor_grafos",
        default_tool_name="Compress",
        default_status="Reduce ruido y poda relaciones redundantes",
        role_family="swarm",
        model_tier="swarm_math",
        conversation_style="compression_sparse",
        max_helpers=2,
        leader_session_id="bibliotecario",
        responsibilities=[
            "comprimir grafos",
            "podar ruido sin perder historia",
            "destilar relaciones utiles",
        ],
        working_tools=[
            tool("compresion_relaciones", "reduce ruido de nodos repetidos"),
        ],
        forging_tools=[
            forge("pruner_grafo_empresa", "podar aristas debiles sin perder linaje")
        ],
    ),
    role(
        agent_id=14,
        session_id="atencion-agentes",
        role_key="agent_attendant",
        display_name="Atencion a Agentes",
        agent_name="SOPORTE",
        folder_name="atencion_agentes",
        default_tool_name="Support",
        default_status="Desbloquea handoffs y reparte contexto faltante",
        role_family="swarm",
        model_tier="swarm_math",
        conversation_style="supportive_router",
        max_helpers=2,
        leader_session_id="bibliotecario",
        responsibilities=[
            "atender bloqueos",
            "canalizar contexto faltante",
            "resolver handoffs entre celulas",
        ],
        working_tools=[
            tool("cola_bloqueos", "lista demoras y necesidades de apoyo"),
        ],
        forging_tools=[
            forge("router_urgencias", "redirigir urgencias hacia quien mejor pueda resolverlas")
        ],
    ),
    role(
        agent_id=15,
        session_id="grafo-herramientas",
        role_key="tool_graph_keeper",
        display_name="Custodio de Grafos",
        agent_name="GRAFOS",
        folder_name="grafo_herramientas",
        default_tool_name="Graph",
        default_status="Relaciona herramientas, exito, dependencias y reuso",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="structural_mapper",
        max_helpers=5,
        leader_session_id="subgerente-etica",
        responsibilities=[
            "relacionar herramientas y roles",
            "registrar reutilizacion",
            "exponer grafos consultables",
        ],
        working_tools=[
            tool("registro_grafo_herramientas", "relaciona toolchains por rol"),
            tool("mapa_dependencias_cruzadas", "ubica herencias y acoples"),
        ],
        forging_tools=[
            forge("explorador_grafo_herramientas", "consultar herramientas por exito, rol y dominio")
        ],
    ),
    role(
        agent_id=16,
        session_id="base-datos-custodio",
        role_key="database_keeper",
        display_name="Custodio de Base de Datos",
        agent_name="DB",
        folder_name="base_datos_custodio",
        default_tool_name="Schema",
        default_status="Inspecciona esquema, migraciones y salud de base de datos",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="schema_guard",
        max_helpers=5,
        leader_session_id="subgerente-trafico-datos",
        responsibilities=[
            "inspeccionar esquema",
            "vigilar migraciones",
            "registrar queries sensibles",
        ],
        working_tools=[
            tool("inventario_esquema", "documenta tablas, vistas y llaves"),
            tool("radar_migraciones", "resume cambios de esquema y riesgos"),
        ],
        forging_tools=[
            forge("sonda_consistencia_sql", "verificar consistencia y huellas de datos")
        ],
    ),
    role(
        agent_id=17,
        session_id="arquitecto-liquido",
        role_key="architect",
        display_name="Arquitecto Liquido",
        agent_name="ARQUITECTO",
        folder_name="arquitecto_liquido",
        default_tool_name="Blueprint",
        default_status="Define fronteras, contratos internos y topologia",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="system_designer",
        max_helpers=5,
        leader_session_id="subgerente-trafico-datos",
        responsibilities=[
            "definir fronteras",
            "crear contratos internos",
            "apoyar a equipos bloqueados",
        ],
        working_tools=[
            tool("plano_orquesta", "define modulos, limites y acoples"),
            tool("contratos_internos", "describe mensajes entre roles"),
        ],
        forging_tools=[
            forge("generador_topologias", "probar topologias del enjambre bajo carga")
        ],
    ),
    role(
        agent_id=18,
        session_id="forense-cognitivo",
        role_key="forensics",
        display_name="Forense Cognitivo",
        agent_name="FORENSE",
        folder_name="forense_cognitivo",
        default_tool_name="Trace",
        default_status="Reconstruye evidencia, errores y secuencias historicas",
        role_family="swarm",
        model_tier="swarm_math",
        conversation_style="causal_forensic",
        max_helpers=5,
        leader_session_id="subgerente-riesgos",
        responsibilities=[
            "reconstruir causas raiz",
            "ordenar errores historicos",
            "aportar evidencia al liderazgo",
        ],
        working_tools=[
            tool("linea_tiempo_incidentes", "ordena incidentes y dependencias"),
            tool("evidencia_raiz", "conecta errores con modulos y sintomas"),
        ],
        forging_tools=[
            forge("reconstructor_multifuente", "unificar logs, sintomas y cambios en una sola historia")
        ],
    ),
    role(
        agent_id=19,
        session_id="tensionador-cognitivo",
        role_key="stressor",
        display_name="Tensionador Cognitivo",
        agent_name="TENSION",
        folder_name="tensionador_cognitivo",
        default_tool_name="Stress",
        default_status="Presiona supuestos y busca puntos de falla",
        role_family="swarm",
        model_tier="swarm_math",
        conversation_style="adversarial_search",
        max_helpers=5,
        leader_session_id="subgerente-riesgos",
        responsibilities=[
            "buscar puntos ciegos",
            "presionar supuestos del equipo",
            "provocar redisenos sanos",
        ],
        working_tools=[
            tool("matriz_supuestos", "lista hipotesis fragiles del sistema"),
            tool("radar_roturas", "ubica donde conviene replantear una solucion"),
        ],
        forging_tools=[
            forge("inyector_escenarios_extremos", "simular usos extremos sin tocar sistemas reales")
        ],
    ),
    role(
        agent_id=20,
        session_id="visual-sistemas",
        role_key="visual",
        display_name="Especialista Visual",
        agent_name="VISUAL",
        folder_name="visual_sistemas",
        default_tool_name="Map",
        default_status="Traduce el estado del enjambre a mapas y vistas legibles",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="diagrammatic_storyteller",
        max_helpers=5,
        leader_session_id="subgerente-crecimiento",
        responsibilities=[
            "dibujar flujos",
            "explicar estado del enjambre",
            "armar vistas para gerencia",
        ],
        working_tools=[
            tool("vista_estado_enjambre", "resume visualmente estado y pendientes"),
            tool("mapa_flows", "muestra dependencias entre roles y herramientas"),
        ],
        forging_tools=[
            forge("tablero_vivo_operativo", "conectar estado del enjambre a una UI persistente")
        ],
    ),
    role(
        agent_id=21,
        session_id="guardian-gateway",
        role_key="gateway_guard",
        display_name="Guardian del Gateway",
        agent_name="GATEWAY",
        folder_name="guardian_gateway",
        default_tool_name="Route",
        default_status="Vigila rutas, CORS, tokens y frontera de APIs",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="border_guard",
        max_helpers=5,
        leader_session_id="subgerente-trafico-datos",
        responsibilities=[
            "auditar la puerta de entrada",
            "validar rutas, CORS y JWT",
            "impedir saltos por fuera del gateway",
        ],
        working_tools=[
            tool("matriz_rutas_gateway", "lista rutas, destinos y politicas"),
            tool("radar_tokens", "revisa frontera de auth y expiraciones"),
        ],
        forging_tools=[
            forge("sentry_gateway", "probar saltos de frontera y rutas ambiguas")
        ],
    ),
    role(
        agent_id=22,
        session_id="fontanero-integracion",
        role_key="integration_plumber",
        display_name="Fontanero de Integracion",
        agent_name="FONTANERO",
        folder_name="fontanero_integracion",
        default_tool_name="Wire",
        default_status="Valida DAL, paquetes, cadenas y pooling",
        role_family="swarm",
        model_tier="swarm_coder",
        conversation_style="plumbing_precise",
        max_helpers=5,
        leader_session_id="subgerente-trafico-datos",
        responsibilities=[
            "auditar Data Access Layer",
            "validar cadenas de conexion",
            "revisar paquetes y pooling",
        ],
        working_tools=[
            tool("chequeo_dal", "revisa DAL, paquetes y versiones"),
            tool("mapa_conexiones", "ordena cadenas de conexion y destinos"),
        ],
        forging_tools=[
            forge("probador_pooling", "estresar connection pooling y detectar fugas")
        ],
    ),
]


CELL_SPECS = [
    {
        "id": "suministros",
        "label": "Celula de Suministros",
        "division": "subgerencia-crecimiento",
        "manager_label": "Subgerente de Crecimiento",
        "manager_session_id": "subgerente-crecimiento",
        "supervisor_label": "Supervisor Suministros",
        "supervisor_session_id": "github-cosechador",
        "specialist_label": "Cosechador Principal",
        "secretary_label": "Secretario Suministros",
        "auditor_label": "Auditor de Artefactos",
        "assistant_prefix": "GH",
        "max_assistants": 4,
        "tool_name": "Fetch",
        "focus": "repositorios, ramas, PRs y artefactos",
        "oracle_session_ids": ["oraculo-maestro"],
        "support_session_ids": ["visual-sistemas"],
    },
    {
        "id": "qa_release",
        "label": "Celula QA Release",
        "division": "subgerencia-riesgos",
        "manager_label": "Subgerente de Riesgos",
        "manager_session_id": "subgerente-riesgos",
        "supervisor_label": "Supervisor QA",
        "supervisor_session_id": "qa-despliegue",
        "specialist_label": "Forjador QA",
        "secretary_label": "Secretario QA",
        "auditor_label": "Auditor QA",
        "assistant_prefix": "QA",
        "max_assistants": 4,
        "tool_name": "Deploy",
        "focus": "despliegue controlado y rollback",
        "oracle_session_ids": ["oraculo-maestro"],
        "support_session_ids": ["github-cosechador", "forense-cognitivo"],
    },
    {
        "id": "datos",
        "label": "Celula de Datos",
        "division": "subgerencia-trafico-datos",
        "manager_label": "Subgerente de Trafico y Datos",
        "manager_session_id": "subgerente-trafico-datos",
        "supervisor_label": "Supervisor Datos",
        "supervisor_session_id": "base-datos-custodio",
        "specialist_label": "Avatar de Datos",
        "secretary_label": "Secretario Datos",
        "auditor_label": "Auditor de Esquema",
        "assistant_prefix": "DB",
        "max_assistants": 4,
        "tool_name": "Schema",
        "focus": "esquemas, tablas, llaves y mutaciones semanales",
        "oracle_session_ids": ["avatar-datos", "oraculo-maestro"],
        "support_session_ids": ["grafo-herramientas"],
    },
    {
        "id": "conectividad",
        "label": "Celula de Integracion",
        "division": "subgerencia-trafico-datos",
        "manager_label": "Subgerente de Trafico y Datos",
        "manager_session_id": "subgerente-trafico-datos",
        "supervisor_label": "Supervisor Conectividad",
        "supervisor_session_id": "fontanero-integracion",
        "specialist_label": "Fontanero de Integracion",
        "secretary_label": "Secretario Conectividad",
        "auditor_label": "Auditor DAL",
        "assistant_prefix": "NET",
        "max_assistants": 6,
        "tool_name": "Wire",
        "focus": "DAL, paquetes, connection strings y pooling",
        "oracle_session_ids": ["avatar-datos", "oraculo-maestro"],
        "support_session_ids": ["arquitecto-liquido"],
    },
    {
        "id": "gateway",
        "label": "Celula del Gateway",
        "division": "subgerencia-trafico-datos",
        "manager_label": "Subgerente de Trafico y Datos",
        "manager_session_id": "subgerente-trafico-datos",
        "supervisor_label": "Supervisor Gateway",
        "supervisor_session_id": "guardian-gateway",
        "specialist_label": "Guardian de la Frontera",
        "secretary_label": "Secretario Gateway",
        "auditor_label": "Auditor de Tokens",
        "assistant_prefix": "GW",
        "max_assistants": 6,
        "tool_name": "Route",
        "focus": "rutas, CORS, JWT y frontera API",
        "oracle_session_ids": ["oraculo-maestro"],
        "support_session_ids": ["arquitecto-liquido"],
    },
    {
        "id": "backend",
        "label": "Celula Backend",
        "division": "subgerencia-riesgos",
        "manager_label": "Subgerente de Riesgos",
        "manager_session_id": "subgerente-riesgos",
        "supervisor_label": "Supervisor Backend",
        "supervisor_session_id": "backend-verificador",
        "specialist_label": "Forjador Backend",
        "secretary_label": "Secretario Backend",
        "auditor_label": "Auditor Backend",
        "assistant_prefix": "BK",
        "max_assistants": 8,
        "tool_name": "Analyze",
        "focus": "logica de negocio, endpoints y contratos",
        "oracle_session_ids": ["avatar-datos", "oraculo-maestro"],
        "support_session_ids": ["forense-cognitivo", "arquitecto-liquido"],
    },
    {
        "id": "frontend",
        "label": "Celula Frontend",
        "division": "subgerencia-crecimiento",
        "manager_label": "Subgerente de Crecimiento",
        "manager_session_id": "subgerente-crecimiento",
        "supervisor_label": "Supervisor Frontend",
        "supervisor_session_id": "frontend-verificador",
        "specialist_label": "Forjador Frontend",
        "secretary_label": "Secretario Frontend",
        "auditor_label": "Auditor Frontend",
        "assistant_prefix": "FE",
        "max_assistants": 8,
        "tool_name": "Inspect",
        "focus": "renderizado, contratos visuales y smoke UI",
        "oracle_session_ids": ["oraculo-maestro"],
        "support_session_ids": ["visual-sistemas", "guardian-gateway"],
    },
    {
        "id": "tension",
        "label": "Celula de Tension",
        "division": "subgerencia-riesgos",
        "manager_label": "Subgerente de Riesgos",
        "manager_session_id": "subgerente-riesgos",
        "supervisor_label": "Supervisor Tension",
        "supervisor_session_id": "tensionador-cognitivo",
        "specialist_label": "Forjador de Tension",
        "secretary_label": "Secretario Tension",
        "auditor_label": "Auditor de Carga",
        "assistant_prefix": "TN",
        "max_assistants": 8,
        "tool_name": "Stress",
        "focus": "carga, escenarios extremos y cuellos de botella",
        "oracle_session_ids": ["oraculo-maestro"],
        "support_session_ids": ["forense-cognitivo"],
    },
    {
        "id": "memoria",
        "label": "Celula de Memoria",
        "division": "subgerencia-etica",
        "manager_label": "Subgerente de Etica y Memoria",
        "manager_session_id": "subgerente-etica",
        "supervisor_label": "Supervisor Memoria",
        "supervisor_session_id": "bibliotecario",
        "specialist_label": "Bibliotecario Mayor",
        "secretary_label": "Secretario Memoria",
        "auditor_label": "Destilador de Conocimiento",
        "assistant_prefix": "KB",
        "max_assistants": 4,
        "tool_name": "Catalog",
        "focus": "conocimiento corporativo y herramientas que si sirven",
        "oracle_session_ids": ["oraculo-maestro"],
        "support_session_ids": ["compresor-grafos", "atencion-agentes"],
    },
    {
        "id": "grafos",
        "label": "Celula de Grafos",
        "division": "subgerencia-etica",
        "manager_label": "Subgerente de Etica y Memoria",
        "manager_session_id": "subgerente-etica",
        "supervisor_label": "Supervisor Grafos",
        "supervisor_session_id": "grafo-herramientas",
        "specialist_label": "Custodio del Grafo",
        "secretary_label": "Secretario Grafos",
        "auditor_label": "Auditor de Dependencias",
        "assistant_prefix": "GF",
        "max_assistants": 4,
        "tool_name": "Graph",
        "focus": "grafos de herramientas, dependencias y poda sinaptica",
        "oracle_session_ids": ["avatar-datos", "oraculo-maestro"],
        "support_session_ids": ["compresor-grafos", "atencion-agentes"],
    },
]


def build_error_log(role_spec: dict) -> str:
    lines = []
    for index in range(1, 41):
        lines.append(
            f"[2026-04-21T10:{index:02d}:00Z] {role_spec['session_id']} "
            f"MODEL={role_spec['model_name']} ERROR_INDEX={index:03d} "
            f"contexto=empresa-local detalle='Pendiente afinar {role_spec['role_key']} "
            "contra GitHub, QA, backend, frontend, datos, memoria y grafos' "
            "accion='registrar evidencia y conservar solo el traceback critico'"
        )
    return "\n".join(lines) + "\n"


def build_company_knowledge(role_spec: dict) -> str:
    responsibilities = "\n".join(f"- {item}" for item in role_spec["responsibilities"])
    working_tools = "\n".join(
        f"- `{item['name']}`: {item['purpose']}" for item in role_spec["working_tools"]
    )
    forging_tools = "\n".join(
        f"- `{item['name']}`: {item['need']}" for item in role_spec["forging_tools"]
    )
    return dedent(
        f"""
        # {role_spec['display_name']}

        Rol operativo dentro del enjambre de esta empresa.

        ## Identidad
        - Familia: {role_spec['role_family']}
        - Modelo base: {role_spec['model_name']}
        - Estilo conversacional: {role_spec['conversation_style']}
        - Lider de referencia: {role_spec.get('leader_session_id') or 'director-liquido'}

        ## Responsabilidades
        {responsibilities}

        ## Herramientas que ya sirven
        {working_tools}

        ## Herramientas que faltan forjar
        {forging_tools}

        ## Contexto especifico de empresa
        - La empresa necesita trazabilidad entre GitHub, QA, backend, frontend, base de datos y memoria de grafos.
        - El Director y los Subgerentes deben detectar actividad muerta y reencuadrar sin romper el flujo del Especialista.
        - El conocimiento debe guardarse por rol, herramienta, dominio y exito real de uso.
        """
    ).strip() + "\n"


def build_cell_knowledge(cell: dict) -> str:
    oracle_lines = "\n".join(f"- {item}" for item in cell["oracle_session_ids"])
    support_lines = "\n".join(f"- {item}" for item in cell["support_session_ids"])
    assistant_lines = "\n".join(
        f"- {cell['assistant_prefix']}-{index + 1}: asistente efimero para trabajo paralelo"
        for index in range(min(cell["max_assistants"], 5))
    )
    return dedent(
        f"""
        # {cell['label']}

        Plantilla universal de especialidad con aislamiento de flujo.

        ## Roles simbolicos
        - Subgerente: {cell['manager_label']}
        - Supervisor: {cell['supervisor_label']}
        - Especialista Principal: {cell['specialist_label']}
        - Secretario: {cell['secretary_label']}
        - Auditor: {cell['auditor_label']}

        ## Enfoque
        - Division: {cell['division']}
        - Foco: {cell['focus']}
        - Herramienta visible: {cell['tool_name']}

        ## Oraculos y dependencias
        {oracle_lines}

        ## Soportes de la celula
        {support_lines}

        ## Asistentes efimeros
        {assistant_lines}

        ## Regla operativa
        - El Supervisor responde al mundo sin interrumpir al Especialista.
        - El Secretario mata loops, timeouts y deltas muertos.
        - El Auditor destila soluciones limpias y solo sube oro al grafo maestro.
        """
    ).strip() + "\n"


def write_role_structure(role_spec: dict) -> None:
    role_dir = ROLES_DIR / role_spec["folder_name"]
    working_dir = role_dir / "herramientas" / "funcionando"
    forging_dir = role_dir / "herramientas" / "por_forjar"
    knowledge_dir = role_dir / "conocimiento"
    errors_dir = role_dir / "errores"

    for directory in (working_dir, forging_dir, knowledge_dir, errors_dir):
        directory.mkdir(parents=True, exist_ok=True)

    manifest = {
        "session_id": role_spec["session_id"],
        "display_name": role_spec["display_name"],
        "role_key": role_spec["role_key"],
        "team_name": role_spec["team_name"],
        "agent_name": role_spec.get("agent_name"),
        "is_team_lead": role_spec.get("is_team_lead", False),
        "role_family": role_spec["role_family"],
        "model_tier": role_spec["model_tier"],
        "model_name": role_spec["model_name"],
        "conversation_style": role_spec["conversation_style"],
        "leader_session_id": role_spec.get("leader_session_id"),
        "max_helpers": role_spec["max_helpers"],
        "responsibilities": role_spec["responsibilities"],
    }

    (role_dir / "manifiesto.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (working_dir / "catalogo.json").write_text(
        json.dumps(role_spec["working_tools"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (forging_dir / "catalogo.json").write_text(
        json.dumps(role_spec["forging_tools"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (knowledge_dir / "empresa.md").write_text(
        build_company_knowledge(role_spec),
        encoding="utf-8",
    )
    (errors_dir / "historial.log").write_text(build_error_log(role_spec), encoding="utf-8")


def write_cell_structure(cell: dict) -> None:
    cell_dir = CELLS_DIR / cell["id"]
    roles_dir = cell_dir / "roles"
    assistants_dir = cell_dir / "asistentes"
    knowledge_dir = cell_dir / "conocimiento"

    directories = [
        roles_dir / "subgerente",
        roles_dir / "supervisor",
        roles_dir / "especialista",
        roles_dir / "secretario",
        roles_dir / "auditor",
        assistants_dir,
        knowledge_dir,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    manifests = {
        "subgerente": {
            "label": cell["manager_label"],
            "function": "control de escalacion y prioridad de la celula",
            "session_id": cell.get("manager_session_id"),
        },
        "supervisor": {
            "label": cell["supervisor_label"],
            "function": "proxy tactico y escudo de interrupciones",
            "session_id": cell.get("supervisor_session_id"),
        },
        "especialista": {
            "label": cell["specialist_label"],
            "function": "forjador maestro enfocado en el objetivo",
        },
        "secretario": {
            "label": cell["secretary_label"],
            "function": "watchdog de TTL y recoleccion de procesos muertos",
        },
        "auditor": {
            "label": cell["auditor_label"],
            "function": "destilador de herramientas y errores utiles",
        },
    }

    for role_name, manifest in manifests.items():
        (roles_dir / role_name / "manifiesto.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    assistant_catalog = [
        {
            "assistant_id": f"{cell['assistant_prefix']}-{index + 1}",
            "purpose": f"operar en paralelo sobre {cell['focus']}",
        }
        for index in range(cell["max_assistants"])
    ]
    (assistants_dir / "catalogo.json").write_text(
        json.dumps(assistant_catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (knowledge_dir / "flujo.md").write_text(build_cell_knowledge(cell), encoding="utf-8")


def build_blueprint() -> dict:
    return {
        "team_name": "ORQUESTA LIQUIDA",
        "mission_prompt": MISSION_PROMPT,
        "agents": ROLE_SPECS,
        "architecture": {
            "agent_count": len(ROLE_SPECS),
            "cells": CELL_SPECS,
            "model_plan": MODEL_PLAN,
            "tiers": {
                "director_and_submanagers": 5,
                "avatars": 2,
                "swarm": 15,
            },
        },
        "quick_missions": [
            {
                "id": "upgrade_qwen35",
                "title": "Upgrade a jerarquia Qwen3.5",
                "description": (
                    "Director y Subgerentes en Qwen3.5-14B-A2.4B, Avatares en Qwen3.5-7B-1M "
                    "y enjambre operativo en Qwen3.5-7B Coder/Math."
                ),
            },
            {
                "id": "integracion_enjambre_local",
                "title": "Integracion completa del enjambre",
                "description": (
                    "Traer contexto de GitHub, preparar QA, validar backend y frontend, "
                    "guardar conocimiento, mantener grafos y supervisar bloqueos."
                ),
            },
        ],
    }


def build_plan_markdown() -> str:
    sections = [
        "# Plan de Integracion del Enjambre",
        "",
        "## Objetivo",
        "- Convertir la oficina visual en una mesa cognitiva donde Director, Subgerentes, Avatares y Celdas se coordinen sin romper el flujo del Especialista.",
        "",
        "## Jerarquia de modelos",
        f"- Director: `{MODEL_PLAN['director']['name']}`",
        f"- Subgerentes: `{MODEL_PLAN['submanager']['name']}`",
        f"- Enjambre Coder: `{MODEL_PLAN['swarm_coder']['name']}`",
        f"- Enjambre Math: `{MODEL_PLAN['swarm_math']['name']}`",
        f"- Avatares: `{MODEL_PLAN['avatar']['name']}`",
        "",
        "## Niveles",
        "- Nivel 0: Director Liquido.",
        "- Nivel 1: cuatro Subgerentes tacticos para riesgos, crecimiento, etica y trafico de datos.",
        "- Nivel 2: dos Avatares de contexto de largo aliento.",
        "- Nivel 3: quince especialistas operativos visibles en la oficina.",
        "- Nivel 4: celdas de especialidad con Supervisor, Especialista, Secretario, Auditor y Asistentes.",
        "",
        "## Celulas",
        "- Suministros, QA Release, Datos, Integracion, Gateway, Backend, Frontend, Tension, Memoria y Grafos.",
        "- Cada celula protege el estado de flujo del Especialista mediante un Supervisor proxy.",
        "- El Secretario mata procesos colgados y el Auditor solo sube soluciones limpias al conocimiento.",
        "",
        "## Entregables persistentes",
        "- Carpetas por rol con herramientas funcionando y herramientas por forjar.",
        "- Carpetas por celula con subgerente, supervisor, especialista, secretario, auditor y asistentes.",
        "- Conocimiento especifico de empresa por rol.",
        "- Historial de errores semiestructurado por rol con referencia a modelo.",
        "- Blueprint del enjambre para la oficina visual.",
        "",
        "## Regla operativa",
        "- Si un rol queda esperando, el Director o el Subgerente lo reencuadran.",
        "- Toda interrupcion pasa por el Supervisor; el Especialista no pierde el hilo.",
        "- Los Avatares y la Biblioteca sostienen contexto sin saturar a la fuerza de choque.",
        "- Toda herramienta util se registra como funcionando; lo demas queda en por forjar.",
        "",
    ]
    return "\n".join(sections) + "\n"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ROLES_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_MOCK_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    for role_spec in ROLE_SPECS:
        write_role_structure(role_spec)
    for cell in CELL_SPECS:
        write_cell_structure(cell)

    blueprint = build_blueprint()
    blueprint_json = json.dumps(blueprint, ensure_ascii=False, indent=2)

    (DATA_DIR / "enjambre_blueprint.json").write_text(blueprint_json, encoding="utf-8")
    (PUBLIC_MOCK_DIR / "enjambre_blueprint.json").write_text(blueprint_json, encoding="utf-8")
    (DOCS_DIR / "plan_integracion_enjambre.md").write_text(
        build_plan_markdown(),
        encoding="utf-8",
    )

    print("Enjambre operativo sembrado.")
    print(f"Roles: {len(ROLE_SPECS)}")
    print(f"Celdas: {len(CELL_SPECS)}")
    print(f"Blueprint: {DATA_DIR / 'enjambre_blueprint.json'}")
    print(f"Public mock: {PUBLIC_MOCK_DIR / 'enjambre_blueprint.json'}")


if __name__ == "__main__":
    main()
