# Snapshot de despliegue estable: Gemma 4 agentes visuales + LangGraph NOC

Fecha: 2026-05-07  
Host: `elsecluster5` (`10.1.1.60`)  
Usuario remoto: `u23u`  
Sistema: Red Hat Enterprise Linux 9.4  
GPU: `8x NVIDIA L40S`, `46068 MiB` por tarjeta  
Driver NVIDIA: `550.90.07`  
Python: `/home/u23u/miniconda/envs/orquesta_py311/bin/python` (`3.11.15`)  
vLLM: `0.19.1`

## Acceso

No guardar contrasenas en texto plano dentro del repositorio.

```powershell
ssh -i C:\Users\ptic252\.ssh\id_ed25519_elsecluster5_continue -o StrictHostKeyChecking=no u23u@10.1.1.60
```

Secretos locales ya presentes en el host:

```bash
/home/u23u/.cache/huggingface/token
/home/u23u/.cache/huggingface/stored_tokens
```

## Modelo activo

Modelo: `google/gemma-4-26B-A4B-it`  
Nombre servido: `gemma-4-26b-a4b-agents`  
Ruta local:

```bash
/home/u23u/models/Gemma-4-26B-A4B-it
```

Peso en disco observado: `49G`

## vLLM activo

Endpoint:

```bash
http://127.0.0.1:8098/v1
```

Comando equivalente:

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
CUDA_HOME=/home/u23u/cuda-12.6.3 \
PATH=/home/u23u/miniconda/envs/orquesta_py311/bin:/home/u23u/cuda-12.6.3/bin:$PATH \
LD_LIBRARY_PATH=/home/u23u/cuda-12.6.3/lib64:$LD_LIBRARY_PATH \
NCCL_P2P_DISABLE=1 \
NCCL_IB_DISABLE=1 \
NCCL_SOCKET_IFNAME=lo \
/home/u23u/miniconda/envs/orquesta_py311/bin/vllm serve /home/u23u/models/Gemma-4-26B-A4B-it \
  --served-model-name gemma-4-26b-a4b-agents \
  --trust-remote-code \
  --tensor-parallel-size 8 \
  --mm-encoder-tp-mode data \
  --disable-custom-all-reduce \
  --host 0.0.0.0 \
  --port 8098 \
  --max-model-len 262144 \
  --max-num-seqs 6 \
  --max-num-batched-tokens 65536 \
  --gpu-memory-utilization 0.65 \
  --enforce-eager
```

Script versionado:

```bash
/home/u23u/langflow-qa/start_gemma4_vllm_agents.sh
```

Script local:

```text
deploy/start_gemma4_vllm_agents.sh
```

## Recursos observados

vLLM reporto:

- `max_model_len`: `262144`
- `GPU KV cache size`: `213,376 tokens`
- `Maximum concurrency for 262,144 tokens per request`: `2.99x`
- memoria por GPU despues de carga: aprox. `26877 MiB / 46068 MiB`
- uso por GPU: aprox. `58%`, debajo del limite operativo pedido de `65%`

Lectura importante:

- Se pueden lanzar 6 agentes LangGraph.
- Si los 6 agentes intentan usar 256K tokens completos simultaneamente, vLLM va a encolar o reducir concurrencia efectiva. Esto es correcto para no romper el limite de VRAM.
- Para etiquetado de imagenes, usar prompts cortos por agente y reservar contexto largo para auditorias/datasets grandes.

## NOC / LangGraph activo

Endpoint:

```bash
http://127.0.0.1:7870
```

Health:

```bash
curl -sS http://127.0.0.1:7870/health
```

Respuesta esperada:

```json
{"ok":true,"model":"gemma-4-26b-a4b-agents","kimi_status":200,"phoenix":"http://127.0.0.1:6006/v1/traces"}
```

Arranque:

```bash
cd /home/u23u/langflow-qa
MODEL=gemma-4-26b-a4b-agents \
PARALLEL=6 \
BASE_URL=http://127.0.0.1:8098/v1 \
./restart_noc_for_openai_model.sh
```

Variables internas conservan prefijo `KIMI_` por compatibilidad, pero ahora apuntan a Gemma:

- `KIMI_BASE_URL=http://127.0.0.1:8098/v1`
- `KIMI_MODEL=gemma-4-26b-a4b-agents`
- `KIMI_PARALLEL=6`

## Soporte multimodal agregado al NOC

El endpoint `/chat` acepta:

- `image_url`: URL remota accesible por vLLM.
- `image_path`: ruta dentro del contenedor NOC. Usar `/data/images/...`.

La ruta host montada como `/data` es:

```bash
/home/u23u/langgraph-swarm/runtime/noc
```

Para copiar imagenes:

```bash
mkdir -p /home/u23u/langgraph-swarm/runtime/noc/images
cp /ruta/host/imagen.jpg /home/u23u/langgraph-swarm/runtime/noc/images/
```

Luego llamar con:

```json
{
  "image_path": "/data/images/imagen.jpg"
}
```

## Agentes visuales actuales

Cuando el pedido contiene `imagen`, `image`, `etiquet`, `label`, `ocr` o `visual`, el fallback crea roles visuales:

- `intake_visual`
- `ocr_validator`
- `object_detector`
- `label_quality`
- `dataset_consistency`
- `visual_auditor`

Cada agente:

- invoca Gemma multimodal si hay imagen.
- crea mini-entorno efimero.
- forja herramienta reproducible.
- deja evidencia en consola.
- reporta a Phoenix y al NOC visual.

## Smoke multimodal validado

Imagen sintetica creada:

```bash
/home/u23u/langgraph-swarm/runtime/noc/images/red_blue_split.png
```

Chat multimodal:

```bash
curl -sS --max-time 240 http://127.0.0.1:7870/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Etiqueta esta imagen en JSON corto con campos: descripcion, colores, objetos, calidad_label.","mode":"chat","max_tokens":180,"run_sandbox_probe":false,"image_path":"/data/images/red_blue_split.png"}'
```

Resultado validado:

```json
{
  "descripcion": "Imagen dividida verticalmente en dos bloques de color solido.",
  "colores": ["rojo", "azul"],
  "objetos": ["rectangulos"],
  "calidad_label": "alta"
}
```

Smoke de 6 agentes:

```bash
curl -sS --max-time 600 http://127.0.0.1:7870/chat \
  -H 'Content-Type: application/json' \
  -d @/tmp/gemma4_image_agents_smoke_run.json
```

Resultado validado:

- `15` eventos.
- agentes visuales correctos.
- `FAILED_CONSOLES []`.
- auditor aborto correctamente el pipeline sobre imagen sintetica sin semantica util, evitando etiquetas falsas.

## Servicios que se mantienen

- `qa-phoenix`: `http://127.0.0.1:6006`
- `qa-memgraph`: memoria/grafo
- `qa-runner`: `http://127.0.0.1:8090`
- LangGraph Studio si esta activo: `127.0.0.1:2024`

## Recuperacion rapida

```bash
cd /home/u23u/langflow-qa
./start_gemma4_vllm_agents.sh
MODEL=gemma-4-26b-a4b-agents PARALLEL=6 BASE_URL=http://127.0.0.1:8098/v1 ./restart_noc_for_openai_model.sh
curl -sS http://127.0.0.1:7870/health
```

## Volver a Kimi si hace falta

Usar el snapshot anterior:

```text
DEPLOYMENT_SNAPSHOT_KIMI_VLLM_2026-05-07.md
```

Y el script:

```bash
/home/u23u/langflow-qa/start_kimi_vllm_local.sh
```
