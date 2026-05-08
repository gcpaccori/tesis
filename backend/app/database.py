from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .constants import CLASS_TO_ID, decision_for_class

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "backend" / "data" / "tesis.db"
MIGRATION_PATH = ROOT_DIR / "database" / "migrations" / "001_init_sqlite.sql"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))
        image_count = connection.execute("SELECT COUNT(*) AS total FROM imagenes").fetchone()["total"]
        if image_count == 0:
            seed_demo(connection)
        connection.execute(
            """
            UPDATE lotes
            SET origen = ?
            WHERE origen IS NULL OR origen <> ?
            """,
            (
                "Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec",
                "Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec",
            ),
        )
        connection.commit()


def seed_demo(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lotes (codigo_lote, origen, fecha_captura, descripcion)
        VALUES (?, ?, ?, ?)
        """,
        (
            "LOTE_001",
            "Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec",
            "2026-05-07",
            "Lote demo de hongos comestibles desecados",
        ),
    )
    lote_id = connection.execute("SELECT id FROM lotes WHERE codigo_lote = ?", ("LOTE_001",)).fetchone()["id"]

    images = [
        ("LOTE_001_IMG_0001", "train", "auditada", "normal", "normal", "normal", 11.8, 38.0),
        ("LOTE_001_IMG_0002", "train", "auditada", "danado", "danado", "carbonizado", 13.2, 41.0),
        ("LOTE_001_IMG_0003", "val", "auditada", "larvas", "normal", "larvas", 15.9, 39.0),
        ("LOTE_001_IMG_0004", "test", "auditada", "impureza_mineral", "impureza_vegetal", "impureza_mineral", 10.4, 36.0),
        ("LOTE_001_IMG_0005", "test", "auditada", "carbonizado", "carbonizado", "carbonizado", 14.6, 42.0),
        ("LOTE_001_IMG_0006", "train", "corregida", "aplastado", "aplastado", "aplastado", 12.1, 37.0),
        ("LOTE_001_IMG_0007", "val", "auditada", "impureza_vegetal", "pie_desprendido", "impureza_vegetal", 16.0, 40.0),
        ("LOTE_001_IMG_0008", "test", "auditada", "pie_desprendido", "pie_desprendido", "normal", 9.7, 34.0),
    ]

    model_id = connection.execute(
        """
        INSERT INTO modelos (
          modelo_version, model_path, model_hash_sha256, dataset_version, epochs, imgsz,
          batch_size, optimizer, ultralytics_version, fecha_entrenamiento, metricas_validacion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "yolov11n_codex_v1",
            "models/yolov11n_codex_v1/best.pt",
            "7a3f1b4dd0a2c96e905f28ed5d87142d5d9959492a04af3f21c9d6a17bb7c001",
            "dataset_codex_auditado_v1",
            120,
            640,
            16,
            "AdamW",
            "mock-compatible",
            "2026-05-07T09:00:00",
            json.dumps({"map50": 0.884, "map5095": 0.691, "precision": 0.861, "recall": 0.842}),
        ),
    ).lastrowid

    for index, (code, split, status, gt_class, human_class, model_class, human_time, model_time_ms) in enumerate(images, 1):
        image_id = connection.execute(
            """
            INSERT INTO imagenes (
              lote_id, codigo_imagen, ruta_archivo, width, height, tipo_presentacion,
              sesion_captura, split_dataset, estado_auditoria, hash_archivo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lote_id,
                code,
                f"mock://{code}.jpg",
                1280,
                800,
                "entero",
                "SESION_DEMO_01",
                split,
                status,
                f"hash_demo_{index:04d}",
            ),
        ).lastrowid

        class_id = CLASS_TO_ID[gt_class]
        connection.execute(
            """
            INSERT INTO etiquetas_yolo (
              imagen_id, class_id, class_name, x_center, y_center, width, height,
              fuente, anotador, estado, observacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                image_id,
                class_id,
                gt_class,
                0.50,
                0.52,
                0.42 if gt_class != "normal" else 0.58,
                0.36 if gt_class != "normal" else 0.48,
                "manual",
                "A01",
                "auditada" if status == "auditada" else "corregida",
                "Etiqueta demo auditada segun codebook CODEX-YOLO.",
            ),
        )

        connection.execute(
            """
            INSERT INTO evaluaciones_humanas (
              imagen_id, evaluador, defecto_danado, defecto_carbonizado, defecto_aplastado,
              defecto_larvas, impureza_vegetal, impureza_mineral, pie_desprendido_cantidad,
              etiqueta_final_humana, decision_humana, tiempo_segundos, observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                image_id,
                "E01",
                int(human_class == "danado"),
                int(human_class == "carbonizado"),
                int(human_class == "aplastado"),
                "LEVE" if human_class == "larvas" else "NO",
                int(human_class == "impureza_vegetal"),
                int(human_class == "impureza_mineral"),
                1 if human_class == "pie_desprendido" else 0,
                human_class,
                decision_for_class(human_class),
                human_time,
                "Evaluacion humana demo; no es ground truth.",
            ),
        )

        connection.execute(
            """
            INSERT INTO ground_truth (
              imagen_id, clase_principal_real, decision_real, defectos_reales_multietiqueta,
              severidad_larvas, fuente_ground_truth, auditor, nivel_confianza, observacion, locked
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                image_id,
                gt_class,
                decision_for_class(gt_class, "leve"),
                json.dumps([gt_class]),
                "leve" if gt_class == "larvas" else None,
                "auditoria_experta_codex",
                "AUD01",
                "alta",
                "Verdad de referencia demo separada de evaluacion humana e IA.",
                1,
            ),
        )

        result_id = connection.execute(
            """
            INSERT INTO resultados_modelo (
              imagen_id, modelo_id, run_id, clase_principal_modelo, decision_modelo,
              detecciones_total, tiempo_inferencia_ms, confidence_threshold, iou_threshold
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                image_id,
                model_id,
                "demo_run_001",
                model_class,
                decision_for_class(model_class),
                0 if model_class == "normal" else 1,
                model_time_ms,
                0.25,
                0.50,
            ),
        ).lastrowid

        if model_class != "normal":
            connection.execute(
                """
                INSERT INTO detecciones_modelo (
                  resultado_modelo_id, class_id, class_name, confidence, x1, y1, x2, y2, bbox_area_px
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    CLASS_TO_ID[model_class],
                    model_class,
                    0.72 + (index % 3) * 0.06,
                    310.0,
                    210.0,
                    820.0,
                    610.0,
                    204000.0,
                ),
            )

    connection.execute(
        """
        INSERT INTO configuracion_metodologica (
          id, metodologia_locked, test_locked, class_priority, decision_rules,
          confidence_default, iou_default, split_policy
        )
        VALUES (1, 1, 1, ?, ?, 0.25, 0.50, '70/20/10')
        """,
        (
            json.dumps(["impureza_mineral", "impureza_vegetal", "larvas", "carbonizado", "danado", "aplastado", "pie_desprendido", "normal"]),
            json.dumps({"normal": "apto", "larvas_leve": "observado", "larvas_severo": "no_apto", "impurezas": "observado"}),
        ),
    )

    connection.commit()


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]
