# Snapshot de despliegue estable: Kimi vLLM + LangGraph NOC

Fecha: 2026-05-07  
Host: `elsecluster5` (`10.1.1.60`)  
Usuario remoto: `u23u`  
Sistema: Red Hat Enterprise Linux 9.4  
GPU: `8x NVIDIA L40S`, `46068 MiB` por tarjeta  
Driver NVIDIA validado: `550.90.07`  
Python runtime principal: `/home/u23u/miniconda/envs/orquesta_py311/bin/python` (`3.11.15`)  
vLLM validado: `0.19.1`

## Credenciales y acceso

No guardar contrasenas en texto plano dentro del repo.

Acceso operativo recomendado desde esta maquina Windows:

```powershell
ssh -i C:\Users\ptic252\.ssh\id_ed25519_elsecluster5_continue -o StrictHostKeyChecking=no u23u@10.1.1.60
```

Si un LLM o automatizador nuevo necesita secretos, debe leerlos desde archivos locales ya existentes en el host remoto:

- Hugging Face token: `/home/u23u/.cache/huggingface/token`
- Hugging Face stored tokens: `/home/u23u/.cache/huggingface/stored_tokens`

## Servicios vivos validados

| Servicio | Puerto | Estado | Uso |
|---|---:|---|---|
| `vLLM Kimi` | `8098` | OK | OpenAI-compatible `/v1`, modelo `kimi-k2.6-vllm` |
| `qa-langgraph-swarm` | `7870` | OK | NOC 3D + LangGraph + WebSocket |
| `qa-phoenix` | `6006` | OK | Observabilidad local |
| `qa-memgraph` | `7687` interno | OK | Grafo/memoria |
| `qa-runner` | `8090` | OK | QA runner operativo |
| LangGraph Studio | `2024` | OK si proceso activo | Studio del grafo |

Comprobaciones:

```bash
curl -sS http://127.0.0.1:8098/v1/models
curl -sS http://127.0.0.1:7870/health
curl -sS http://127.0.0.1:6006
podman ps --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}'
nvidia-smi
```

## Kimi vLLM estable actual

Modelo en disco:

```bash
/home/u23u/models/Kimi-K2.6
```

Script local versionado:

```bash
deploy/start_kimi_vllm_local.sh
```

Script remoto:

```bash
/home/u23u/langflow-qa/start_kimi_vllm_local.sh
```

Comando equivalente validado:

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
CUDA_HOME=/home/u23u/cuda-12.6.3 \
PATH=/home/u23u/miniconda/envs/orquesta_py311/bin:/home/u23u/cuda-12.6.3/bin:$PATH \
LD_LIBRARY_PATH=/home/u23u/cuda-12.6.3/lib64:$LD_LIBRARY_PATH \
NCCL_P2P_DISABLE=1 \
NCCL_IB_DISABLE=1 \
NCCL_SOCKET_IFNAME=lo \
/home/u23u/miniconda/envs/orquesta_py311/bin/vllm serve /home/u23u/models/Kimi-K2.6 \
  --served-model-name kimi-k2.6-vllm \
  --trust-remote-code \
  --tensor-parallel-size 8 \
  --mm-encoder-tp-mode data \
  --disable-custom-all-reduce \
  --enable-auto-tool-choice \
  --tool-call-parser kimi_k2 \
  --reasoning-parser kimi_k2 \
  --host 0.0.0.0 \
  --port 8098 \
  --max-model-len 65536 \
  --max-num-batched-tokens 32768 \
  --cpu-offload-gb 48 \
  --gpu-memory-utilization 0.90 \
  --enforce-eager
```

Notas criticas:

- `--enforce-eager` evita cuelgues/compilaciones largas.
- `--disable-custom-all-reduce` evita problemas NCCL en este host.
- `CUDA_HOME=/home/u23u/cuda-12.6.3` es necesario porque el host no tiene `nvcc` global utilizable para este flujo.
- `CPU_OFFLOAD_GB=48` fue el minimo estable observado; `32/40` fallaban por memoria.
- Con Kimi grande y offload, el throughput por stream largo fue bajo. Para agentes fluidos conviene usar prompts cortos, modo instantaneo y fan-out controlado.

## NOC/LangGraph estable actual

Codigo local:

```text
deploy/langgraph-swarm/app.py
deploy/langgraph-swarm/Dockerfile
deploy/langgraph-swarm/requirements.txt
```

Codigo remoto:

```bash
/home/u23u/langgraph-swarm/app/app.py
```

Build y arranque actual:

```bash
cd /home/u23u/langgraph-swarm/app
podman build -t localhost/kimi-langgraph-swarm:latest .
podman rm -f qa-langgraph-swarm || true
podman run -d --name qa-langgraph-swarm --network host \
  -v /home/u23u/langgraph-swarm/runtime/noc:/data:Z \
  -e KIMI_BASE_URL=http://127.0.0.1:8098/v1 \
  -e KIMI_MODEL=kimi-k2.6-vllm \
  -e KIMI_PARALLEL=4 \
  -e LEARN_PATH=/data/learned.jsonl \
  -e PHOENIX_OTLP_ENDPOINT=http://127.0.0.1:6006/v1/traces \
  localhost/kimi-langgraph-swarm:latest
```

Aunque las variables conservan prefijo `KIMI_`, el NOC solo necesita un endpoint OpenAI-compatible. Para Gemma se reutilizan igual.

## Puentes locales Windows

Tunel recomendado:

```powershell
Start-Process -FilePath ssh -ArgumentList @(
  '-N',
  '-L','2024:127.0.0.1:2024',
  '-L','7870:127.0.0.1:7870',
  '-L','6006:127.0.0.1:6006',
  '-i','C:\Users\ptic252\.ssh\id_ed25519_elsecluster5_continue',
  '-o','StrictHostKeyChecking=no',
  '-o','ExitOnForwardFailure=yes',
  'u23u@10.1.1.60'
) -WindowStyle Hidden
```

URLs locales:

- NOC 3D: `http://127.0.0.1:7870`
- Phoenix: `http://127.0.0.1:6006`
- LangGraph Studio: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

## Pruebas de humo validadas

Chat directo:

```bash
curl -sS http://127.0.0.1:7870/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Di FINAL: NOC conectado a vLLM en una linea.","mode":"chat","max_tokens":80,"run_sandbox_probe":false}'
```

Respuesta esperada:

```text
FINAL: NOC conectado a vLLM en una linea.
```

Enjambre minimo:

```bash
curl -sS http://127.0.0.1:7870/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Smoke instantaneo: crea 1 especialista Verificador, forja herramienta segura, ejecuta consola y entrega FINAL breve.","mode":"swarm","max_tokens":160,"planner_tokens":300,"swarm_width":1,"max_agents":1,"run_sandbox_probe":true}'
```

Resultado esperado:

- planner crea agente `verifier`
- `verifier_console` ejecuta mini-entorno con `rc=0`
- `sandbox` devuelve `sandbox-ok`
- `auditor` consolida estado

## Transicion prevista a Gemma agentes

Se mantiene:

- LangGraph/NOC
- Phoenix
- Memgraph
- qa-runner
- tuneles locales

Se reemplaza:

- backend de inferencia Kimi en `8098`
- modelo servido

Objetivo nuevo:

- Gemma 4 multimodal para etiquetado de imagenes
- 6 a 8 agentes concurrentes por LangGraph
- limite de VRAM del servidor de inferencia: `gpu_memory_utilization=0.65`
- contexto objetivo: `262144` tokens cuando el modelo lo soporte

Recomendacion tecnica:

- Usar un solo vLLM server Gemma multimodal y fan-out de agentes sobre ese endpoint.
- No levantar 6 u 8 copias completas del modelo; eso duplica pesos y desperdicia VRAM.
- El limite `0.65` se aplica al proceso vLLM. Si 8 agentes piden 256K simultaneamente, vLLM debe encolar o reducir concurrencia efectiva para no romper el limite.
