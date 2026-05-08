from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.constants import decision_for_class

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_NDJSON = ROOT_DIR / "hongos-suillus (1).ndjson"
COOPERATIVE_NAME = "Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec"

CLASS_PRIORITY = [
    "impureza_mineral",
    "impureza_vegetal",
    "contaminante",
    "pluma",
    "larvas",
    "carbonizado",
    "danado",
    "aplastado",
    "pie_desprendido",
    "normal",
]

DISPLAY_NAMES = {
    "danado": "Danado",
    "carbonizado": "Carbonizado",
    "aplastado": "Aplastado",
    "larvas": "Larvas",
    "impureza_vegetal": "Impureza vegetal",
    "impureza_mineral": "Impureza mineral",
    "pie_desprendido": "Pie desprendido",
    "contaminante": "Contaminante",
    "pluma": "Pluma",
    "normal": "Normal",
}


def normalize_class_name(value: str) -> str:
    value = (value or "").strip().lower()
    replacements = {
        "dañado": "danado",
        "daÃ±ado": "danado",
        "danado": "danado",
        "impureza vegetal": "impureza_vegetal",
        "impureza mineral": "impureza_mineral",
        "pie desprendido": "pie_desprendido",
    }
    return replacements.get(value, value.replace(" ", "_"))


def class_display(value: str) -> str:
    return DISPLAY_NAMES.get(value, value.replace("_", " ").title())


def bbox_from_points(points: list[dict[str, float]]) -> dict[str, float]:
    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    return {
        "x_min": min(xs),
        "y_min": min(ys),
        "x_max": max(xs),
        "y_max": max(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }


def parse_segment(segment: list[float], class_names: dict[str, str]) -> dict[str, Any] | None:
    if len(segment) < 7:
        return None

    class_id = int(segment[0])
    raw_name = class_names.get(str(class_id), f"clase_{class_id}")
    class_name = normalize_class_name(raw_name)
    coords = segment[1:]
    points = [
        {"x": float(coords[index]), "y": float(coords[index + 1])}
        for index in range(0, len(coords) - 1, 2)
    ]
    if len(points) < 3:
        return None

    return {
        "class_id": class_id,
        "class_name": class_name,
        "class_display": class_display(class_name),
        "points": points,
        "bbox": bbox_from_points(points),
    }


def primary_class(detections: list[dict[str, Any]]) -> str:
    if not detections:
        return "normal"
    present = {detection["class_name"] for detection in detections}
    for class_name in CLASS_PRIORITY:
        if class_name in present:
            return class_name
    return detections[0]["class_name"]


@lru_cache(maxsize=1)
def load_ndjson_dataset(path: str = str(DEFAULT_NDJSON)) -> dict[str, Any]:
    ndjson_path = Path(path)
    if not ndjson_path.exists():
        return {
            "dataset": {"name": "sin_ndjson", "class_names": {}},
            "images": [],
            "summary": {
                "total_images": 0,
                "annotated_images": 0,
                "unlabeled_images": 0,
                "total_detections": 0,
                "class_distribution": {},
            },
        }

    dataset: dict[str, Any] = {"name": ndjson_path.stem, "class_names": {}}
    images: list[dict[str, Any]] = []
    class_counter: Counter[str] = Counter()

    for line in ndjson_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("type") == "dataset":
            class_names = {
                str(key): normalize_class_name(str(value))
                for key, value in (item.get("class_names") or {}).items()
            }
            dataset = {
                "name": item.get("name", ndjson_path.stem),
                "task": item.get("task"),
                "url": item.get("url"),
                "class_names": class_names,
                "class_display": {key: class_display(value) for key, value in class_names.items()},
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            }
            continue

        if item.get("type") != "image":
            continue

        detections = []
        for segment in (item.get("annotations") or {}).get("segments", []) or []:
            detection = parse_segment(segment, dataset.get("class_names", {}))
            if detection:
                detections.append(detection)
                class_counter[detection["class_name"]] += 1

        primary = primary_class(detections)
        file_name = item.get("file", "")
        code = Path(file_name).stem
        images.append(
            {
                "codigo_imagen": code,
                "file": file_name,
                "url": item.get("url"),
                "width": item.get("width"),
                "height": item.get("height"),
                "split": item.get("split"),
                "detections": detections,
                "detections_count": len(detections),
                "primary_class": primary,
                "primary_display": class_display(primary),
                "decision_codex_proxy": decision_for_class(primary),
                "annotated": bool(detections),
            }
        )

    annotated_images = sum(1 for image in images if image["annotated"])
    images.sort(key=lambda image: (not image["annotated"], image["file"]))
    return {
        "dataset": dataset,
        "cooperative": COOPERATIVE_NAME,
        "images": images,
        "summary": {
            "total_images": len(images),
            "annotated_images": annotated_images,
            "unlabeled_images": len(images) - annotated_images,
            "total_detections": sum(image["detections_count"] for image in images),
            "class_distribution": dict(class_counter),
        },
    }


def get_detection_page(limit: int = 30, offset: int = 0, annotated_only: bool = True) -> dict[str, Any]:
    dataset = load_ndjson_dataset()
    images = dataset["images"]
    if annotated_only:
        images = [image for image in images if image["annotated"]]
    paged = images[offset : offset + limit]
    return {
        "dataset": dataset["dataset"],
        "cooperative": dataset["cooperative"],
        "summary": dataset["summary"],
        "limit": limit,
        "offset": offset,
        "total_filtered": len(images),
        "images": paged,
    }


def human_rows_from_specialist_labels(evaluators: int = 3) -> list[dict[str, Any]]:
    dataset = load_ndjson_dataset()
    rng = random.Random(20260507)
    rows: list[dict[str, Any]] = []
    evaluator_profiles = [
        ("TRAB_E01", 0.78, 1.00),
        ("TRAB_E02", 0.72, 1.12),
        ("TRAB_E03", 0.69, 0.94),
    ][: max(1, min(evaluators, 3))]

    possible_classes = [class_name for class_name in CLASS_PRIORITY if class_name != "normal"]
    for image in dataset["images"]:
        if not image["annotated"]:
            continue
        specialist_class = image["primary_class"]
        for evaluator, accuracy, speed_factor in evaluator_profiles:
            human_class = specialist_class
            if rng.random() > accuracy:
                alternatives = [class_name for class_name in possible_classes if class_name != specialist_class]
                human_class = rng.choice(alternatives)

            base_seconds = 2.85 + min(image["detections_count"], 8) * 0.08
            seconds = min(4.8, max(2.1, base_seconds * speed_factor + rng.uniform(-0.32, 0.34)))
            rows.append(
                {
                    "codigo_imagen": image["codigo_imagen"],
                    "archivo_imagen": image["file"],
                    "codigo_lote": "CASAEC_HONGOS_SUILLUS_001",
                    "fecha_evaluacion": date(2026, 5, 7).isoformat(),
                    "evaluador": evaluator,
                    "tipo_presentacion": "entero",
                    "defecto_danado": "SI" if human_class == "danado" else "NO",
                    "defecto_carbonizado": "SI" if human_class == "carbonizado" else "NO",
                    "defecto_aplastado": "SI" if human_class == "aplastado" else "NO",
                    "defecto_larvas": "LEVE" if human_class == "larvas" else "NO",
                    "impureza_vegetal": "SI" if human_class == "impureza_vegetal" else "NO",
                    "impureza_mineral": "SI" if human_class == "impureza_mineral" else "NO",
                    "pie_desprendido_cantidad": 1 if human_class == "pie_desprendido" else 0,
                    "etiqueta_final_humana": human_class,
                    "decision_humana": decision_for_class(human_class),
                    "tiempo_segundos": round(seconds, 2),
                    "clase_especialista_referencia": specialist_class,
                    "coincide_con_especialista": "SI" if human_class == specialist_class else "NO",
                    "observaciones": "Dato humano simulado para pruebas; no reemplaza ground truth especialista.",
                }
            )
    return rows


def ground_truth_rows_from_specialist_labels() -> list[dict[str, Any]]:
    dataset = load_ndjson_dataset()
    rows: list[dict[str, Any]] = []
    for image in dataset["images"]:
        if not image["annotated"]:
            continue
        rows.append(
            {
                "codigo_imagen": image["codigo_imagen"],
                "archivo_imagen": image["file"],
                "codigo_lote": "CASAEC_HONGOS_SUILLUS_001",
                "clase_principal_real": image["primary_class"],
                "decision_real": image["decision_codex_proxy"],
                "defectos_reales_multietiqueta": ", ".join(
                    sorted({detection["class_name"] for detection in image["detections"]})
                ),
                "detecciones_especialista": image["detections_count"],
                "fuente_ground_truth": "ndjson_ultralytics_especialistas",
                "auditor": "especialistas_casaec",
                "nivel_confianza": "alta",
                "locked": "SI",
                "observacion": "Etiqueta especialista importada desde NDJSON; no proviene del Excel humano.",
            }
        )
    return rows
