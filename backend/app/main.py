from __future__ import annotations

import io
import json
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.constants import CLASS_TO_ID, CLASSES, decision_for_class
from app.database import get_connection, init_db, rows_to_dicts
from app.services.excel_import import validate_human_records
from app.services.metrics import calculate_core_metrics
from app.services.instruments import export_all_instruments, export_single_instrument, instruments_payload
from app.services.ndjson_dataset import (
    COOPERATIVE_NAME,
    get_detection_page,
    ground_truth_rows_from_specialist_labels,
    human_rows_from_specialist_labels,
    load_ndjson_dataset,
)
from app.services.thesis_run import (
    RUNS_DIR,
    create_uploaded_run,
    export_thesis_docx,
    export_thesis_run,
    list_thesis_runs,
    thesis_run_payload,
    thesis_run_payload_for,
)
from app.services.yolo import validate_yolo_lines


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Tesis YOLOv11n CODEX API",
    version="0.1.0",
    description="Herramienta local para comparar evaluacion humana e IA contra ground truth CODEX auditado.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LabelValidationRequest(BaseModel):
    content: str | None = None
    lines: list[str] | None = None


class ModelRegisterRequest(BaseModel):
    modelo_version: str
    model_path: str
    model_hash_sha256: str | None = None
    dataset_version: str | None = None
    epochs: int | None = None
    imgsz: int = 640
    batch_size: int | None = None
    optimizer: str | None = None
    ultralytics_version: str | None = None
    metricas_validacion: dict[str, Any] = Field(default_factory=dict)


class InferenceRunRequest(BaseModel):
    modelo_version: str = "yolov11n_codex_v1"
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.50
    device: str = "cpu"
    run_id: str = "demo_run_001"


class CompareRequest(BaseModel):
    run_id: str = "demo_run_001"
    experiment_id: str = "demo"


def parse_metrics(metrics_json: str | None) -> dict[str, float]:
    if not metrics_json:
        return {}
    try:
        return json.loads(metrics_json)
    except json.JSONDecodeError:
        return {}


def get_model_by_version(modelo_version: str) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM modelos WHERE modelo_version = ?", (modelo_version,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Modelo no registrado: {modelo_version}")
    return dict(row)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    with get_connection() as connection:
        summary = {
            "imagenes_totales": connection.execute("SELECT COUNT(*) total FROM imagenes").fetchone()["total"],
            "etiquetas_totales": connection.execute("SELECT COUNT(*) total FROM etiquetas_yolo").fetchone()["total"],
            "clases_detectadas": connection.execute("SELECT COUNT(DISTINCT class_name) total FROM etiquetas_yolo").fetchone()["total"],
            "imagenes_auditadas": connection.execute(
                "SELECT COUNT(*) total FROM imagenes WHERE estado_auditoria = 'auditada'"
            ).fetchone()["total"],
            "ground_truth_completo": connection.execute("SELECT COUNT(*) total FROM ground_truth").fetchone()["total"],
            "evaluaciones_humanas": connection.execute("SELECT COUNT(*) total FROM evaluaciones_humanas").fetchone()["total"],
            "inferencias_realizadas": connection.execute(
                "SELECT COUNT(DISTINCT run_id) total FROM resultados_modelo"
            ).fetchone()["total"],
        }
        config = dict(connection.execute("SELECT * FROM configuracion_metodologica WHERE id = 1").fetchone())
        duplicate_split = connection.execute(
            """
            SELECT COUNT(*) total
            FROM (
              SELECT hash_archivo
              FROM imagenes
              GROUP BY hash_archivo
              HAVING COUNT(DISTINCT split_dataset) > 1
            )
            """
        ).fetchone()["total"]

    alerts = []
    if summary["ground_truth_completo"] < summary["imagenes_totales"]:
        alerts.append(
            {
                "code": "ERR_GT_INCOMPLETE",
                "severity": "error",
                "message": "Faltan imagenes con ground truth; se bloquean conclusiones finales.",
            }
        )
    if not config["test_locked"]:
        alerts.append(
            {
                "code": "WARN_TEST_OPEN",
                "severity": "warning",
                "message": "El split test debe bloquearse antes de la evaluacion final.",
            }
        )
    if not config["metodologia_locked"]:
        alerts.append(
            {
                "code": "WARN_METHOD_OPEN",
                "severity": "warning",
                "message": "La configuracion metodologica sigue editable.",
            }
        )
    if duplicate_split:
        alerts.append(
            {
                "code": "ERR_DUPLICATE_IMAGE_SPLIT",
                "severity": "error",
                "message": "Hay hashes repetidos en mas de un split.",
            }
        )
    alerts.append(
        {
            "code": "INFO_PROXY_CODEX",
            "severity": "info",
            "message": "Las reglas fisicoquimicas CODEX se declaran como proxy visual, no como medicion de laboratorio.",
        }
    )

    return {
        "summary": summary,
        "alerts": alerts,
        "methodology": {
            "metodologia_locked": bool(config["metodologia_locked"]),
            "test_locked": bool(config["test_locked"]),
            "ground_truth_ready": summary["ground_truth_completo"] == summary["imagenes_totales"],
            "paired_ready": True,
        },
    }


@app.get("/api/specialist-detections")
def specialist_detections(limit: int = 30, offset: int = 0, annotated_only: bool = True) -> dict[str, Any]:
    limit = max(1, min(limit, 80))
    offset = max(0, offset)
    return get_detection_page(limit=limit, offset=offset, annotated_only=annotated_only)


@app.get("/api/specialist-detections/summary")
def specialist_detection_summary() -> dict[str, Any]:
    dataset = load_ndjson_dataset()
    return {
        "dataset": dataset["dataset"],
        "cooperative": COOPERATIVE_NAME,
        "summary": dataset["summary"],
    }


@app.get("/api/instruments")
def instruments() -> dict[str, Any]:
    return instruments_payload()


@app.get("/api/thesis-run")
def thesis_run() -> dict[str, Any]:
    return thesis_run_payload()


@app.get("/api/thesis-runs")
def thesis_runs() -> list[dict[str, Any]]:
    return list_thesis_runs()


@app.get("/api/thesis-runs/{run_id}")
def thesis_run_by_id(run_id: str) -> dict[str, Any]:
    try:
        return thesis_run_payload_for(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Corrida no encontrada: {run_id}") from exc


def workbook_file_response(path: Path, filename: str) -> StreamingResponse:
    content = path.read_bytes()
    path.unlink(missing_ok=True)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/api/instruments/export-all")
def export_instruments_all() -> StreamingResponse:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:
        path = Path(temp.name)
    export_all_instruments(path)
    return workbook_file_response(path, "instrumentos_validacion_tesis_casaec.xlsx")


@app.get("/api/instruments/{code}/export")
def export_instrument(code: str) -> StreamingResponse:
    normalized = code.strip().upper()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:
        path = Path(temp.name)
    try:
        export_single_instrument(normalized, path)
    except KeyError as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail=f"Instrumento no encontrado: {normalized}") from exc
    return workbook_file_response(path, f"{normalized}_instrumento_tesis_casaec.xlsx")


@app.get("/api/thesis-run/export")
def export_thesis_run_excel() -> StreamingResponse:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:
        path = Path(temp.name)
    export_thesis_run(path)
    return workbook_file_response(path, "resultados_validacion_tesis_casaec.xlsx")


@app.get("/api/thesis-runs/{run_id}/export-excel")
def export_thesis_run_excel_by_id(run_id: str) -> StreamingResponse:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:
        path = Path(temp.name)
    try:
        export_thesis_run(path, run_id=run_id)
    except KeyError as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail=f"Corrida no encontrada: {run_id}") from exc
    return workbook_file_response(path, f"resultados_validacion_{run_id}.xlsx")


def docx_file_response(path: Path, filename: str) -> StreamingResponse:
    content = path.read_bytes()
    path.unlink(missing_ok=True)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


@app.get("/api/thesis-runs/{run_id}/export-word")
def export_thesis_run_word_by_id(run_id: str) -> StreamingResponse:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp:
        path = Path(temp.name)
    try:
        export_thesis_docx(path, run_id=run_id)
    except KeyError as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail=f"Corrida no encontrada: {run_id}") from exc
    return docx_file_response(path, f"informe_sustentacion_{run_id}.docx")


@app.post("/api/thesis-runs/upload")
async def upload_thesis_run(
    run_name: str = Form(...),
    model_version: str = Form("YOLOv11n-CODEX-CASAEC-demo-reproducible"),
    expert_file: UploadFile = File(...),
    images_file: UploadFile | None = File(None),
) -> dict[str, Any]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in expert_file.filename or "expert_file.xlsx")
    upload_dir = RUNS_DIR / "_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    expert_path = upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    expert_path.write_bytes(await expert_file.read())

    images_filename = None
    if images_file and images_file.filename:
        safe_images_name = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in images_file.filename)
        images_filename = safe_images_name
        (upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_images_name}").write_bytes(await images_file.read())

    try:
        return create_uploaded_run(
            expert_path=expert_path,
            run_name=run_name,
            model_version=model_version,
            images_filename=images_filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def dataframe_excel_response(dataframe: pd.DataFrame, filename: str) -> StreamingResponse:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="datos")
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/api/specialist-detections/export-human-excel")
def export_human_excel(evaluators: int = 3) -> StreamingResponse:
    rows = human_rows_from_specialist_labels(evaluators=evaluators)
    if not rows:
        raise HTTPException(status_code=404, detail="No hay imagenes etiquetadas en el NDJSON.")
    dataframe = pd.DataFrame(rows)
    return dataframe_excel_response(dataframe, "evaluacion_humana_simulada_casaec.xlsx")


@app.get("/api/specialist-detections/export-ground-truth-excel")
def export_ground_truth_excel() -> StreamingResponse:
    rows = ground_truth_rows_from_specialist_labels()
    if not rows:
        raise HTTPException(status_code=404, detail="No hay imagenes etiquetadas en el NDJSON.")
    dataframe = pd.DataFrame(rows)
    return dataframe_excel_response(dataframe, "ground_truth_especialistas_casaec.xlsx")


@app.get("/api/images")
def images() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
              i.id,
              i.codigo_imagen,
              l.codigo_lote,
              i.ruta_archivo,
              i.width,
              i.height,
              i.split_dataset,
              i.estado_auditoria,
              COUNT(e.id) AS labels_count,
              CASE WHEN gt.id IS NULL THEN 0 ELSE 1 END AS has_ground_truth,
              0 AS duplicate_warning
            FROM imagenes i
            LEFT JOIN lotes l ON l.id = i.lote_id
            LEFT JOIN etiquetas_yolo e ON e.imagen_id = i.id
            LEFT JOIN ground_truth gt ON gt.imagen_id = i.id
            GROUP BY i.id, l.codigo_lote, gt.id
            ORDER BY i.codigo_imagen
            """
        ).fetchall()
    return [{**dict(row), "has_ground_truth": bool(row["has_ground_truth"]), "duplicate_warning": False} for row in rows]


@app.get("/api/images/{image_id}/labels")
def image_labels(image_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, imagen_id AS image_id, class_id, class_name, x_center, y_center, width, height,
                   fuente, estado, observacion
            FROM etiquetas_yolo
            WHERE imagen_id = ?
            ORDER BY id
            """,
            (image_id,),
        ).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/labels/validate")
def validate_labels(payload: LabelValidationRequest) -> dict[str, Any]:
    lines = payload.lines
    if lines is None:
        lines = (payload.content or "").splitlines()
    errors = validate_yolo_lines(lines)
    return {
        "valid": len(errors) == 0,
        "errors": [error.__dict__ for error in errors],
    }


@app.get("/api/human-evaluations")
def human_evaluations() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT eh.id, i.codigo_imagen, eh.evaluador, eh.etiqueta_final_humana,
                   eh.decision_humana, eh.tiempo_segundos, 'validada' AS estado
            FROM evaluaciones_humanas eh
            JOIN imagenes i ON i.id = eh.imagen_id
            ORDER BY i.codigo_imagen, eh.evaluador
            """
        ).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/human-evaluations/import-excel")
async def import_human_excel(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    try:
        dataframe = pd.read_excel(io.BytesIO(content))
    except Exception as exc:  # pragma: no cover - depends on uploaded file engine
        raise HTTPException(status_code=400, detail=f"No se pudo leer el Excel: {exc}") from exc

    records = dataframe.fillna("").to_dict(orient="records")
    with get_connection() as connection:
        existing = {
            row["codigo_imagen"]: row["id"]
            for row in connection.execute("SELECT id, codigo_imagen FROM imagenes").fetchall()
        }
        valid, errors = validate_human_records(records, set(existing.keys()))
        for row in valid:
            connection.execute(
                """
                INSERT OR REPLACE INTO evaluaciones_humanas (
                  imagen_id, evaluador, defecto_danado, defecto_carbonizado, defecto_aplastado,
                  defecto_larvas, impureza_vegetal, impureza_mineral, pie_desprendido_cantidad,
                  etiqueta_final_humana, decision_humana, tiempo_segundos, observaciones
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    existing[row["codigo_imagen"]],
                    row["evaluador"],
                    row.get("defecto_danado", 0),
                    row.get("defecto_carbonizado", 0),
                    row.get("defecto_aplastado", 0),
                    str(row.get("defecto_larvas") or "NO"),
                    row.get("impureza_vegetal", 0),
                    row.get("impureza_mineral", 0),
                    int(row.get("pie_desprendido_cantidad") or 0),
                    row["etiqueta_final_humana"],
                    row["decision_humana"],
                    row["tiempo_segundos"],
                    str(row.get("observaciones") or ""),
                ),
            )
        connection.commit()

    return {
        "archivo": file.filename,
        "filas_leidas": len(records),
        "filas_validas": len(valid),
        "filas_con_error": len(errors),
        "errores": [error.__dict__ for error in errors],
        "evaluadores": sorted({row["evaluador"] for row in valid}),
        "imagenes_unicas": len({row["codigo_imagen"] for row in valid}),
        "fecha_importacion": datetime.now().date().isoformat(),
        "nota_metodologica": "El Excel humano se guardo como evaluacion_humana, no como ground_truth.",
    }


@app.get("/api/ground-truth")
def ground_truth() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT gt.id, i.codigo_imagen, gt.clase_principal_real, gt.decision_real,
                   gt.auditor, gt.nivel_confianza, gt.locked
            FROM ground_truth gt
            JOIN imagenes i ON i.id = gt.imagen_id
            ORDER BY i.codigo_imagen
            """
        ).fetchall()
    return [{**dict(row), "locked": bool(row["locked"])} for row in rows]


@app.post("/api/models/register")
def register_model(payload: ModelRegisterRequest) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO modelos (
              modelo_version, model_path, model_hash_sha256, dataset_version, epochs, imgsz,
              batch_size, optimizer, ultralytics_version, fecha_entrenamiento, metricas_validacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(modelo_version) DO UPDATE SET
              model_path = excluded.model_path,
              model_hash_sha256 = excluded.model_hash_sha256,
              dataset_version = excluded.dataset_version,
              epochs = excluded.epochs,
              imgsz = excluded.imgsz,
              batch_size = excluded.batch_size,
              optimizer = excluded.optimizer,
              ultralytics_version = excluded.ultralytics_version,
              metricas_validacion = excluded.metricas_validacion
            """,
            (
                payload.modelo_version,
                payload.model_path,
                payload.model_hash_sha256,
                payload.dataset_version,
                payload.epochs,
                payload.imgsz,
                payload.batch_size,
                payload.optimizer,
                payload.ultralytics_version,
                datetime.now().isoformat(timespec="seconds"),
                json.dumps(payload.metricas_validacion),
            ),
        )
        connection.commit()
    return get_model_by_version(payload.modelo_version)


@app.get("/api/models")
def models() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM modelos ORDER BY created_at DESC").fetchall()

    output = []
    for row in rows:
        item = dict(row)
        metrics = parse_metrics(item.pop("metricas_validacion", None))
        item["map50"] = metrics.get("map50", 0.0)
        item["map5095"] = metrics.get("map5095", 0.0)
        output.append(item)
    return output


def predicted_class_for_demo(code: str, gt_class: str) -> str:
    if code.endswith("0002"):
        return "carbonizado"
    if code.endswith("0008"):
        return "normal"
    return gt_class


@app.post("/api/inference/run")
def run_inference(payload: InferenceRunRequest) -> dict[str, Any]:
    model = get_model_by_version(payload.modelo_version)
    with get_connection() as connection:
        old_result_ids = [
            row["id"]
            for row in connection.execute("SELECT id FROM resultados_modelo WHERE run_id = ?", (payload.run_id,)).fetchall()
        ]
        if old_result_ids:
            placeholders = ",".join("?" for _ in old_result_ids)
            connection.execute(f"DELETE FROM detecciones_modelo WHERE resultado_modelo_id IN ({placeholders})", old_result_ids)
            connection.execute(f"DELETE FROM resultados_modelo WHERE id IN ({placeholders})", old_result_ids)

        rows = connection.execute(
            """
            SELECT i.id, i.codigo_imagen, gt.clase_principal_real
            FROM imagenes i
            JOIN ground_truth gt ON gt.imagen_id = i.id
            ORDER BY i.codigo_imagen
            """
        ).fetchall()
        for index, row in enumerate(rows, 1):
            predicted = predicted_class_for_demo(row["codigo_imagen"], row["clase_principal_real"])
            time_ms = 33.5 + index * 1.7
            result_id = connection.execute(
                """
                INSERT INTO resultados_modelo (
                  imagen_id, modelo_id, run_id, clase_principal_modelo, decision_modelo,
                  detecciones_total, tiempo_inferencia_ms, confidence_threshold, iou_threshold
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    model["id"],
                    payload.run_id,
                    predicted,
                    decision_for_class(predicted),
                    0 if predicted == "normal" else 1,
                    time_ms,
                    payload.confidence_threshold,
                    payload.iou_threshold,
                ),
            ).lastrowid
            if predicted != "normal":
                connection.execute(
                    """
                    INSERT INTO detecciones_modelo (
                      resultado_modelo_id, class_id, class_name, confidence, x1, y1, x2, y2, bbox_area_px
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result_id,
                        CLASS_TO_ID[predicted],
                        predicted,
                        0.79,
                        310.0,
                        210.0,
                        820.0,
                        610.0,
                        204000.0,
                    ),
                )
        connection.commit()

    return get_inference_run(payload.run_id)


@app.get("/api/inference/runs/{run_id}")
def get_inference_run(run_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        run_rows = connection.execute(
            """
            SELECT rm.run_id, m.modelo_version, i.codigo_imagen, rm.clase_principal_modelo,
                   rm.decision_modelo, rm.detecciones_total, rm.tiempo_inferencia_ms,
                   rm.confidence_threshold, rm.iou_threshold
            FROM resultados_modelo rm
            JOIN imagenes i ON i.id = rm.imagen_id
            JOIN modelos m ON m.id = rm.modelo_id
            WHERE rm.run_id = ?
            ORDER BY i.codigo_imagen
            """,
            (run_id,),
        ).fetchall()

    if not run_rows:
        raise HTTPException(status_code=404, detail=f"Run no encontrado: {run_id}")

    results = [
        {
            "codigo_imagen": row["codigo_imagen"],
            "clase_principal_modelo": row["clase_principal_modelo"],
            "decision_modelo": row["decision_modelo"],
            "detecciones_total": row["detecciones_total"],
            "tiempo_inferencia_ms": row["tiempo_inferencia_ms"],
        }
        for row in run_rows
    ]
    return {
        "run_id": run_id,
        "modelo_version": run_rows[0]["modelo_version"],
        "total_imagenes": len(run_rows),
        "imagenes_procesadas": len(run_rows),
        "confidence_threshold": run_rows[0]["confidence_threshold"],
        "iou_threshold": run_rows[0]["iou_threshold"],
        "tiempo_promedio_ms": sum(row["tiempo_inferencia_ms"] for row in run_rows) / len(run_rows),
        "results": results,
    }


def build_comparison(run_id: str, experiment_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        images_count = connection.execute("SELECT COUNT(*) total FROM imagenes").fetchone()["total"]
        rows = connection.execute(
            """
            SELECT i.codigo_imagen,
                   gt.clase_principal_real AS ground_truth,
                   eh.etiqueta_final_humana AS humano,
                   rm.clase_principal_modelo AS ia,
                   eh.tiempo_segundos AS tiempo_humano,
                   rm.tiempo_inferencia_ms AS tiempo_ia,
                   m.id AS modelo_id,
                   m.metricas_validacion
            FROM imagenes i
            JOIN ground_truth gt ON gt.imagen_id = i.id
            JOIN evaluaciones_humanas eh ON eh.imagen_id = i.id
            JOIN resultados_modelo rm ON rm.imagen_id = i.id AND rm.run_id = ?
            JOIN modelos m ON m.id = rm.modelo_id
            WHERE eh.evaluador = (
              SELECT MIN(eh2.evaluador)
              FROM evaluaciones_humanas eh2
              WHERE eh2.imagen_id = i.id
            )
            ORDER BY i.codigo_imagen
            """,
            (run_id,),
        ).fetchall()

        if not rows:
            raise HTTPException(status_code=409, detail="No hay interseccion valida entre ground truth, humano e IA.")

        model_id = rows[0]["modelo_id"]
        validation_metrics = parse_metrics(rows[0]["metricas_validacion"])
        comparison_rows = []
        for row in rows:
            comparison_rows.append(
                {
                    "codigo_imagen": row["codigo_imagen"],
                    "ground_truth": row["ground_truth"],
                    "humano": row["humano"],
                    "ia": row["ia"],
                    "humano_correcto": row["humano"] == row["ground_truth"],
                    "ia_correcto": row["ia"] == row["ground_truth"],
                    "tiempo_humano": row["tiempo_humano"],
                    "tiempo_ia": row["tiempo_ia"],
                }
            )

        metrics = calculate_core_metrics(
            comparison_rows,
            map50=validation_metrics.get("map50", 0.0),
            map5095=validation_metrics.get("map5095", 0.0),
        )
        warnings = []
        if len(comparison_rows) < images_count:
            warnings.append(
                f"Metricas calculadas sobre interseccion valida: {len(comparison_rows)} de {images_count} imagenes."
            )

        connection.execute(
            """
            INSERT INTO metricas_experimento (
              experimento, modelo_id, total_imagenes, accuracy_humano, accuracy_modelo,
              precision_global, recall_global, f1_global, map50, map5095, kappa_humano,
              kappa_modelo, mcnemar_stat, mcnemar_p_value, tiempo_promedio_humano,
              tiempo_promedio_modelo, resultados_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                model_id,
                metrics["total"],
                metrics["accuracy_humano"],
                metrics["accuracy_modelo"],
                metrics["per_class_model"]["normal"]["precision"],
                metrics["per_class_model"]["normal"]["recall"],
                metrics["per_class_model"]["normal"]["f1"],
                metrics["map50"],
                metrics["map5095"],
                metrics["kappa_humano"],
                metrics["kappa_modelo"],
                metrics["mcnemar"]["statistic"],
                metrics["mcnemar"]["p_value"],
                metrics["tiempos"]["promedio_humano"],
                metrics["tiempos"]["promedio_ia"],
                json.dumps({"rows": comparison_rows, "metrics": metrics}),
            ),
        )
        connection.commit()

    return {
        "experiment_id": experiment_id,
        "rows": comparison_rows,
        "metrics": metrics,
        "warnings": warnings,
    }


@app.post("/api/experiments/compare")
def compare(payload: CompareRequest) -> dict[str, Any]:
    return build_comparison(payload.run_id, payload.experiment_id)


@app.get("/api/experiments/{experiment_id}/metrics")
def experiment_metrics(experiment_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT resultados_json
            FROM metricas_experimento
            WHERE experimento = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (experiment_id,),
        ).fetchone()
    if row is None:
        return build_comparison("demo_run_001", experiment_id)
    return json.loads(row["resultados_json"])


@app.get("/api/experiments/{experiment_id}/export", response_class=PlainTextResponse)
def export_experiment(experiment_id: str, format: str = "md") -> str:
    comparison = build_comparison("demo_run_001", experiment_id)
    if format == "md":
        metrics = comparison["metrics"]
        mcnemar = metrics["mcnemar"]
        return "\n".join(
            [
                "# Reporte final de tesis",
                "",
                f"- Imagenes pareadas: {metrics['total']}",
                f"- Accuracy humano: {metrics['accuracy_humano']:.4f}",
                f"- Accuracy modelo: {metrics['accuracy_modelo']:.4f}",
                f"- Kappa humano: {metrics['kappa_humano']:.4f}",
                f"- Kappa modelo: {metrics['kappa_modelo']:.4f}",
                f"- McNemar: a={mcnemar['a']}, b={mcnemar['b']}, c={mcnemar['c']}, d={mcnemar['d']}, p={mcnemar['p_value']:.6f}",
                f"- Tiempo promedio humano: {metrics['tiempos']['promedio_humano']:.4f} s",
                f"- Tiempo promedio IA: {metrics['tiempos']['promedio_ia']:.4f} s",
                f"- Factor de velocidad: {metrics['tiempos']['factor_velocidad']:.2f}x",
                "",
                "## Limitacion CODEX",
                "",
                "La herramienta no afirma mediciones fisicoquimicas desde imagen RGB. Las reglas CODEX se operacionalizan como proxy visual auditado.",
            ]
        )

    headers = ["codigo_imagen", "ground_truth", "humano", "ia", "humano_correcto", "ia_correcto", "tiempo_humano", "tiempo_ia"]
    lines = [",".join(headers)]
    for row in comparison["rows"]:
        lines.append(",".join(str(row[column]) for column in headers))
    return "\n".join(lines)
