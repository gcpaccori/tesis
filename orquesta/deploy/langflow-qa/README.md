# LangFlow QA Stack

Este directorio deja lista la migracion a una pila de QA basada en `LangFlow + PostgreSQL + Memgraph + Ollama`, aislada en una red privada `qa_agent_network` y preparada para correr sin tocar `LICO`.

## Snapshot estable 2026-05-07

El estado estable mas reciente ya no depende de LangFlow para el NOC principal: usa `LangGraph + vLLM + Phoenix + Memgraph`.

Documento de recuperacion completo:

```text
../DEPLOYMENT_SNAPSHOT_KIMI_VLLM_2026-05-07.md
```

Ese snapshot incluye host, usuario remoto, rutas, puertos, versiones, comandos de arranque, pruebas de humo y la transicion prevista a Gemma agentes. Las contrasenas no se guardan en texto plano; usar SSH key o pedir el secreto al operador humano.

Scripts nuevos para la migracion a Gemma multimodal:

```text
../download_gemma4_agents.sh
../start_gemma4_vllm_agents.sh
../restart_noc_for_openai_model.sh
../gemma4_image_agents_smoke.json
```

Objetivo Gemma:

- Un solo servidor vLLM Gemma 4 multimodal.
- 6 agentes iniciales, ampliable a 8.
- `gpu_memory_utilization=0.65` para no usar mas del 65% de VRAM.
- `max_model_len=262144` cuando el modelo lo soporte.
- LangGraph/NOC, Phoenix y Memgraph se mantienen como orquestacion/observabilidad/memoria.

## Servicios reales

- `langflow`: interfaz y motor de flujos.
- `memgraph`: motor de grafos para mapeo de relaciones.
- `ollama`: endpoint OpenAI-compatible interno para inferencia local.
- `ollama-pull`: inicializador opcional que descarga el modelo configurado en `.env`.
- `qa-runner`: ejecutor operativo para clonar repos, detectar C#/.NET/frontend/gateway, correr build/test/smoke y escribir conocimiento en Memgraph.
- `kimi-k2-6`: endpoint local llama.cpp para Kimi K2.6 GGUF.
- `kimi-proxy`: adaptador OpenAI-compatible para LangFlow; convierte `reasoning_content` de Kimi a `message.content`.
- `postgres`: no va en contenedor en este host; corre como proceso de usuario en `127.0.0.1:55432` y se consume desde `LANGFLOW_DATABASE_URL`.

## Estado validado en el nodo

- `qa-langflow`: arriba en `127.0.0.1:7860`
- `qa-ollama`: arriba y sano
- `qa-memgraph`: arriba
- `qa-runner`: arriba cuando se despliega el ejecutor operativo
- `PostgreSQL`: arriba en `127.0.0.1:55432` y `10.1.1.60:55432`
- `gemma4:31b`: descargado y cargando en Ollama
- `kimi-k2.6-q2`: servido por `qa-kimi-k2-6` y expuesto a LangFlow por `qa-kimi-proxy`

## Supuestos del despliegue

- En este cluster no hay `docker`; la ruta soportada es `podman-compose`.
- `podman` corre en modo rootless con `ignore_chown_errors = "true"`.
- `Ollama` usa passthrough manual de `/dev/nvidia*` y librerias CUDA/NVML.
- `LangFlow` usa `PostgreSQL` externo al contenedor mediante `LANGFLOW_DATABASE_URL`.
- Solo se expone `LangFlow` al host. `Ollama` y `Memgraph` viven en la red interna.
- `Memgraph` necesita `user: "0:0"` y bind mounts explicitos para `/etc/memgraph`, `/var/lib/memgraph` y `/var/log/memgraph` en este entorno rootless.

## Arranque esperado

1. Copiar `.env.example` a `.env`.
2. Ajustar credenciales y el modelo de Ollama.
3. Arrancar:

```bash
export PATH="$HOME/.local/bin:$HOME/miniconda/bin:$PATH"
podman-compose up -d
```

4. Verificar:

```bash
podman-compose ps
podman logs -f qa-langflow
podman logs -f qa-ollama
podman logs -f qa-memgraph
podman logs -f qa-runner
```

5. Abrir LangFlow en `http://127.0.0.1:7860` en el host remoto, o por tunel SSH.

## Configuracion en LangFlow

Para conectar LangFlow al backend local de inferencia:

- usar el nodo `ChatOpenAI`
- `Base URL`: `http://ollama:11434/v1`
- `Model`: `gemma4:31b`
- no usar nodos de OpenAI/Anthropic con claves de nube

Para usar Kimi K2.6 desde LangFlow:

- usar el nodo `ChatOpenAI`
- `Base URL`: `http://kimi-proxy.local:8031/v1`
- `Model`: `kimi-k2.6-q2`
- `API Key`: cualquier valor no vacio, por ejemplo `local`
- desde el host tambien responde en `http://127.0.0.1:8031/v1`

Para disparar QA operativo desde LangFlow o curl:

```bash
curl -s http://127.0.0.1:8090/health
curl -s -X POST http://127.0.0.1:8090/jobs \
  -H 'Content-Type: application/json' \
  -d '{"module":"modulo-clientes","environment":"qa","repos":[{"url":"https://github.com/empresa/backend.git","branch":"qa","kind":"backend"}]}'
```

Flujo visual sembrado:

- `QA Electro Sur - Pipeline Real`: pega un JSON de trabajo en el Playground y ejecuta una tuberia por etapas.
- Nodos: intake JSON, crear corrida, descargar repos, inventario C#/Frontend/Gateway, restore/build/test .NET, smoke Gateway/UI, escribir Memgraph, reporte final y formateo de respuesta.
- Cada etapa es un componente `JSON -> JSON` propio cargado desde `LANGFLOW_COMPONENTS_PATH=/app/custom_components`, con un archivo `.py` por componente. Esto sigue el loader real de LangFlow 1.9 y evita componentes `outdated` por codigo inyectado en el JSON del flujo.
- Entrada esperada: `module`, `environment`, `repos`, `qa_targets`, `run_builds`, `run_tests`, `run_frontend_build` y `max_seconds`.
- Salida esperada: resumen legible, `job_id`, hallazgos y rutas de `report.md`, `report.json` y `memgraph.cypher`.

Para resembrarlo:

```bash
podman cp seed_electrosur_pipeline_flow.py qa-langflow:/tmp/seed_electrosur_pipeline_flow.py
podman exec qa-langflow /app/.venv/bin/python /tmp/seed_electrosur_pipeline_flow.py
```

Ruta recomendada para LangFlow 1.9:

```bash
podman cp seed_electrosur_19_flow.py qa-langflow:/tmp/seed_electrosur_19_flow.py
podman exec qa-langflow /app/.venv/bin/python /tmp/seed_electrosur_19_flow.py
```

El runner actual ya hace clone, inventario, restore/build/test .NET y smoke HTTP. El build Node/frontend queda como siguiente runner separado para no mezclar runtimes en la imagen .NET base.

## Notas sobre GPU

- `gemma4:31b` queda reservado para Ollama/Gemma en GPUs fisicas `6,7`.
- `kimi-k2-6` queda reservado para Kimi K2.6 en GPUs fisicas `0,1,2,3,4,5`.
- En este host los minors `/dev/nvidiaN` no coinciden uno-a-uno con el indice de `nvidia-smi`; Kimi usa `/dev/nvidia0,1,2,3,6,7` para llegar a los indices fisicos `0-5` y no pisar Gemma.
- Esto deja el stack funcional y evita pelea silenciosa por VRAM entre modelos.
- Si luego quieres `5` agentes pesados realmente concurrentes, el siguiente paso es escalar a varias instancias de backend o cambiar la capa de inferencia.

## DeepSeek V4 Pro local

El servicio `deepseek-v4-pro` corre separado de LangFlow, Memgraph, QA runner y Ollama. Usa vLLM con offload pesado a RAM para respetar la idea de cuerpo en RAM y capa activa en GPU.

- Endpoint local: `http://127.0.0.1:8020/v1`
- Modelo servido: `deepseek-v4-pro`
- Runtime previsto: `vllm/vllm-openai:v0.20.0`
- Pesos: `/home/u23u/models/deepseek-v4-pro`
- Descarga oficial: `deepseek-ai/DeepSeek-V4-Pro`

Comandos en el servidor:

```bash
cd /home/u23u/langflow-qa
./deepseek-pro-download.sh
./deepseek-pro-status.sh
./deepseek-pro-start.sh
./deepseek-pro-test.sh
./deepseek-pro-stop.sh
```

Para usarlo desde LangFlow, agrega un nodo OpenAI-compatible:

- `Base URL`: `http://deepseek-pro.local:8020/v1`
- `Model`: `deepseek-v4-pro`

Nota operativa: DeepSeek V4 Pro oficial no se publica como GGUF Pro en este despliegue. Se descarga el checkpoint oficial `safetensors` FP4/FP8 y se sirve con vLLM. El arranque valida que existan los 64 shards antes de intentar levantar el contenedor.
