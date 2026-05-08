# Kimi 2.6 Q4 Long-Agent Profile

Objetivo: usar Kimi 2.6 Q4 como cerebro de corridas largas en LangFlow, con estado persistente fuera del prompt y herramientas ejecutadas por `qa-runner`.

## Estado Validado

- Fase 1 CPU/RAM: OK.
- Modelo probado: `Kimi-K2.6-UD-Q4_K_XL`, 14 shards, 544 GiB.
- Prueba: carga completa en RAM con CUDA deshabilitado, `--n-gpu-layers 0`, `--no-mmap`, e inferencia basica exitosa.

## Perfil Recomendado

Endpoint final:

- Host local: `http://127.0.0.1:8089/v1`
- Desde LangFlow: `http://kimi-q4-proxy.local:8031/v1`
- Model: `kimi-k2.6-q4`
- API key: cualquier valor no vacio, por ejemplo `local`

Runtime:

- `FINAL_CTX=2000000`
- `ROPE_FREQ_SCALE=0.125`
- `GPU_LAYERS=20` por defecto seguro
- `--no-kv-offload` para mantener KV cache en RAM
- `--no-mmap` para cargar el modelo en RAM y no depender de page faults durante corridas largas
- GPUs fisicas `0-5`
- GPUs `6-7` quedan para Ollama/Gemma si se necesita

## Sobre "Agentes Dentro"

Kimi no crea 300 agentes como procesos separados por si solo. El diseno correcto es:

- Kimi Q4: cerebro planificador y supervisor.
- LangFlow: bucle agente, tool-calling, reintentos y coordinacion.
- `qa-runner`: ejecucion real de herramientas, git, build, tests, smoke, grafos.
- Memgraph/PostgreSQL: memoria persistente de pasos, hallazgos y decisiones.

Asi una corrida puede tener 4000 pasos o durar 12 horas sin depender de que todo viva en una sola respuesta del modelo.

## Comandos

Validar que Q4 existe:

```bash
cd /home/u23u/langflow-qa
./kimi-q4-control.sh validate-files
```

La Fase 1 ya paso, pero se puede repetir:

```bash
cd /home/u23u/langflow-qa
./kimi-q4-control.sh phase1
```

Levantar Q4 hibrido para LangFlow:

```bash
cd /home/u23u/langflow-qa
GPU_LAYERS=20 FINAL_CTX=2000000 ./kimi-q4-control.sh phase2
```

Si `20` carga estable, probar `24` en una ventana controlada:

```bash
cd /home/u23u/langflow-qa
GPU_LAYERS=24 FINAL_CTX=2000000 ./kimi-q4-control.sh phase2
```

Detener Q4:

```bash
cd /home/u23u/langflow-qa
./kimi-q4-control.sh stop
```

## Regla de Operacion

No usar 2M tokens para cada turno. Usar 2M como techo para auditorias gigantes, pero mantener los pasos normales con contexto resumido y memoria externa. Para 4000 pasos, cada paso debe escribir estado en runner/Memgraph y devolver a Kimi solo el resumen necesario.
