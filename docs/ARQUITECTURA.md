# Arquitectura

## Backend

FastAPI expone endpoints bajo `/api`. La persistencia local usa SQLite para que la herramienta pueda ejecutarse sin instalar MySQL/PostgreSQL, pero el esquema conserva las entidades definidas en las directivas:

- `lotes`
- `imagenes`
- `etiquetas_yolo`
- `auditoria_etiquetas`
- `evaluaciones_humanas`
- `ground_truth`
- `modelos`
- `resultados_modelo`
- `detecciones_modelo`
- `metricas_experimento`
- `configuracion_metodologica`

La migracion vive en `database/migrations/001_init_sqlite.sql`.

## Frontend

React + Vite + TypeScript, con componentes tipo shadcn en `frontend/src/components/ui`.

Flujo principal:

```text
Resultados -> Dashboard -> Detecciones -> Instrumentos -> Dataset -> Etiquetado -> Auditoria -> Humano -> Ground truth -> Modelos -> Inferencia -> Comparacion -> Reportes -> Configuracion
```

## Regla de trazabilidad

Cada fila comparativa conserva:

```text
codigo_imagen -> ground_truth -> evaluacion_humana -> resultado_modelo -> metrica
```

La herramienta nunca llena `ground_truth` desde Excel humano ni desde predicciones IA.

## Instrumentos I1-I10

La pantalla `Instrumentos` convierte el archivo `afinamiento_instrumentos_validacion_tesis_codex_yolov11n.md` en un tablero operativo:

- estado de validacion de tesis,
- mapa de instrumentos I1-I10,
- trazabilidad objetivo-instrumento-resultado,
- descarga de paquete Excel listo para anexos.

## NDJSON especialista

El archivo `hongos-suillus (1).ndjson` se usa como fuente de ejemplos etiquetados por especialistas. La API expone:

```text
GET /api/specialist-detections
GET /api/specialist-detections/export-human-excel
GET /api/specialist-detections/export-ground-truth-excel
```

Las anotaciones `segments` se muestran graficamente como poligonos sobre la imagen real.

## Corrida de resultados

La pantalla `Resultados` consume `/api/thesis-run` y muestra la corrida funcional de tesis:

- 200 imagenes etiquetadas por especialistas desde NDJSON.
- 764 poligonos usados como evidencia visual.
- comparacion pareada humano vs YOLOv11n contra el mismo ground truth.
- accuracy, precision, recall, F1, mAP, kappa, McNemar y tiempos.
- errores por clase y casos visuales descargables.

El export `/api/thesis-run/export` genera `resultados_validacion_tesis_casaec.xlsx` para anexos y capitulo de resultados.

## Corridas seleccionables

La pantalla `Corridas` permite cargar un nuevo insumo de evaluacion:

- Excel/CSV con resultados expertos o ground truth.
- NDJSON con etiquetas especialistas.
- ZIP de imagenes opcional para documentar el paquete evaluado.

Cada corrida queda registrada con `run_id`, fecha, modelo, fuente de datos y metricas. La pantalla `Resultados` permite elegir que corrida ver, y los botones de descarga exportan Excel/Word de esa corrida, no de un estado global mezclado.

El Excel de sustentacion incluye hojas de instrumentos I1-I10 rellenados, matriz de confusion humana/modelo, McNemar, kappa, tiempos, casos visuales y limites CODEX. El Word resume esas mismas tablas para anexos y defensa.
