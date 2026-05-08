# API

## Estado

```text
GET /api/health
GET /api/dashboard
```

## Dataset y etiquetas

```text
GET  /api/images
GET  /api/images/{image_id}/labels
POST /api/labels/validate
```

## NDJSON especialista

```text
GET /api/specialist-detections
GET /api/specialist-detections/summary
GET /api/specialist-detections/export-human-excel
GET /api/specialist-detections/export-ground-truth-excel
```

El Excel humano generado es simulado y reproducible. Sirve para probar comparaciones contra las imagenes ya etiquetadas por especialistas, no para reemplazar evaluaciones reales de trabajadores.

## Instrumentos de tesis

```text
GET /api/instruments
GET /api/instruments/export-all
GET /api/instruments/{code}/export
```

`export-all` genera el paquete I1-I10 en Excel:

```text
protocolo de captura
guia CODEX-YOLO
ficha humana
bitacora de entrenamiento
registro de tiempos
V de Aiken
kappa/concordancia
ground truth auditado
inferencia IA
reporte estadistico final
```

## Corrida de resultados de tesis

```text
GET /api/thesis-run
GET /api/thesis-run/export
GET /api/thesis-runs
GET /api/thesis-runs/{run_id}
POST /api/thesis-runs/upload
GET /api/thesis-runs/{run_id}/export-excel
GET /api/thesis-runs/{run_id}/export-word
```

`/api/thesis-run` devuelve la corrida funcional ya pareada:

```text
ground truth especialista NDJSON
evaluacion humana reproducible
inferencia YOLOv11n demo reproducible
accuracy, precision, recall, F1
mAP@0.5, mAP@0.5:0.95
kappa humano/modelo
McNemar
tiempos por imagen
errores por clase
casos visuales
limitaciones CODEX no visuales
```

`/api/thesis-runs` lista las corridas disponibles. Cada respuesta de resultados se calcula desde la corrida seleccionada.

`POST /api/thesis-runs/upload` permite crear una corrida nueva cargando Excel, CSV o NDJSON experto. Columnas aceptadas:

```text
codigo_imagen
ground_truth / clase_principal_real / etiqueta_especialista
humano / etiqueta_final_humana opcional
ia / clase_principal_modelo opcional
tiempo_humano / tiempo_segundos opcional
tiempo_ia / tiempo_inferencia_ms opcional
```

`/api/thesis-runs/{run_id}/export-excel` descarga un Excel impecable de sustentacion con resumen, alineacion tesis-corrida, instrumentos I1-I10 rellenados, preguntas, hipotesis, metricas por clase, distribucion, McNemar, kappa, tiempos, matrices de confusion, errores, casos, tabla pareada y limites CODEX.

`/api/thesis-runs/{run_id}/export-word` descarga un Word de sustentacion con las tablas principales ya llenadas.

`POST /api/labels/validate` acepta:

```json
{
  "lines": ["4 0.5 0.5 0.2 0.2"]
}
```

## Evaluacion humana

```text
GET  /api/human-evaluations
POST /api/human-evaluations/import-excel
```

Columnas minimas:

```text
codigo_imagen
evaluador
etiqueta_final_humana
decision_humana
tiempo_segundos
```

## Ground truth

```text
GET /api/ground-truth
```

La version inicial incluye lectura de datos demo bloqueados. La tabla SQL ya soporta edicion, bloqueo y auditoria.

## Modelos e inferencia

```text
GET  /api/models
POST /api/models/register
POST /api/inference/run
GET  /api/inference/runs/{run_id}
```

`POST /api/inference/run` registra una corrida reproducible. Si no hay `best.pt`, usa modo demo deterministico.

## Comparacion y reportes

```text
POST /api/experiments/compare
GET  /api/experiments/{experiment_id}/metrics
GET  /api/experiments/{experiment_id}/export?format=md
```

Formatos actuales:

```text
md
dataset
audit
human
model
comparison
```
