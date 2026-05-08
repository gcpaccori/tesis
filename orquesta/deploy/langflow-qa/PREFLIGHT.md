# Preflight del Cluster

## Hechos confirmados en el host auditado

- Host: `elsecluster5`
- SO: `RHEL 9.4`
- GPUs: `8x NVIDIA L40S`
- `LICO` y `Slurm` siguen activos como servicios del sistema y no se tocaron
- `docker` no esta instalado
- `podman` disponible en modo rootless
- `podman-compose` instalado en `~/.local/bin`
- `podman` sin rangos `subuid/subgid` para el usuario `u23u`
- `PostgreSQL` levantado como proceso de usuario en `127.0.0.1:55432`

## Ruta segura aplicada

1. `podman` rootless funcionando con `ignore_chown_errors = "true"`.
2. `podman-compose` instalado en espacio de usuario.
3. `ollama` validado en contenedor rootless viendo las `8x L40S` por passthrough manual.
4. `LangFlow` validado con `PostgreSQL` externo.
5. `Memgraph` validado con `user: "0:0"` y bind mounts explicitos.

## Estado actual

- `qa-langflow`: arriba
- `qa-ollama`: arriba
- `qa-memgraph`: arriba
- `PostgreSQL`: arriba
- `gemma4:31b`: descargado

## Puntos que siguen siendo delicados

1. no hay `docker` ni daemon global, asi que la operacion debe ser con `podman-compose`
2. sigue sin haber `subuid/subgid`, por lo que el modo rootless usa mapeo simple y puede romper algunas imagenes complejas
3. el acceso GPU depende de passthrough manual, no de `nvidia-container-toolkit`
4. `gemma4:31b` hoy carga sobre una sola `L40S`; no hay reparto automatico sobre las `8` GPUs con esta configuracion

## Prueba minima que ya paso

Se valido esto en el nodo:

- `LangFlow` accesible por tunel en `http://127.0.0.1:7860`
- `LangFlow` alcanza `PostgreSQL` en `host.containers.internal:55432`
- `LangFlow` alcanza `Ollama` en `http://ollama:11434`
- `Memgraph` arranca dentro de `qa_agent_network`
- `Ollama` lista `gemma4:31b`
