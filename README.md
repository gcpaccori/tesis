# Herramienta de validacion de tesis YOLOv11n/CODEX

Aplicacion local para sustentar una tesis de vision artificial aplicada a hongos comestibles desecados segun CODEX STAN 39-1981 en la Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec.

La regla metodologica central esta implementada desde el inicio:

```text
Excel humano != ground truth
Inferencia IA != ground truth
Humano e IA se comparan contra ground truth CODEX auditado
```

## Estructura

```text
backend/    FastAPI, SQLite, importacion Excel, validacion YOLO, metricas
frontend/   React + Vite + TypeScript + shadcn-style components
database/   migraciones SQL y semilla documentada
docs/       arquitectura, API y QA metodologico
scripts/    arranque local en PowerShell
```

## Arranque local

Backend:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

URLs:

```text
Frontend: http://localhost:5173
API:      http://127.0.0.1:8000
Docs API: http://127.0.0.1:8000/docs
```

Si esos puertos ya estan ocupados:

```powershell
$env:BACKEND_PORT="8001"; .\scripts\start_backend.ps1
$env:VITE_API_BASE_URL="http://127.0.0.1:8001"; $env:FRONTEND_PORT="5174"; .\scripts\start_frontend.ps1
```

## Pruebas

```powershell
cd backend
.\.venv\Scripts\python -m pytest

cd ..\frontend
npm run build
```

## Modulos incluidos

- Pantalla inicial de resultados: prueba ejecutada, veredicto, hipotesis, McNemar, kappa, F1/mAP, tiempos y casos visuales.
- Selector de corridas: cada resultado se calcula desde una corrida especifica.
- Carga de nuevas corridas con Excel/CSV/NDJSON experto e imagenes opcionales.
- Dataset, lotes, splits y bloqueo de test.
- Etiquetado YOLO con validacion de coordenadas.
- Auditoria de etiquetas con historial preparado.
- Importacion Excel humano separada de ground truth.
- Ground truth CODEX auditado y bloqueable.
- Registro de modelo YOLOv11n y corrida reproducible.
- Comparacion pareada humano vs IA contra ground truth.
- Accuracy, precision, recall, F1, matrices, kappa, McNemar y tiempos.
- Exportes Markdown/CSV para evidencia de tesis.
- Visualizacion grafica de detecciones reales desde `hongos-suillus (1).ndjson`.
- Descarga de `ground_truth_especialistas_casaec.xlsx` y `evaluacion_humana_simulada_casaec.xlsx`.
- Descarga de `resultados_validacion_tesis_casaec.xlsx` con resumen, preguntas, hipotesis, tabla pareada, errores por clase, casos y limites CODEX.
- Descarga de `informe_sustentacion_tesis_casaec.docx` con tablas de instrumentos I1-I10 rellenadas desde la corrida.

## Excel generados

Tambien quedan generados en:

```text
exports/evaluacion_humana_simulada_casaec.xlsx
exports/ground_truth_especialistas_casaec.xlsx
exports/instrumentos_validacion_tesis_casaec.xlsx
exports/resultados_validacion_tesis_casaec.xlsx
exports/informe_sustentacion_tesis_casaec.docx
```

Para regenerarlos:

```powershell
.\scripts\generate_excels.ps1
```

La inferencia queda en modo demo reproducible si no existe un `best.pt`; la estructura registra modelo, hash, thresholds, device, `run_id` y tiempos para conectar Ultralytics despues.
