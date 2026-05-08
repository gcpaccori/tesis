from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.constants import CLASSES, VALID_DECISIONS

REQUIRED_COLUMNS = {
    "codigo_imagen",
    "evaluador",
    "etiqueta_final_humana",
    "decision_humana",
    "tiempo_segundos",
}

HUMAN_CLASS_CATALOG = set(CLASSES) | {"contaminante", "pluma"}

NORMALIZE_CLASS = {
    "dañado": "danado",
    "danado": "danado",
    "quemado": "carbonizado",
    "carbonizado": "carbonizado",
    "impureza vegetal": "impureza_vegetal",
    "impureza mineral": "impureza_mineral",
    "pie desprendido": "pie_desprendido",
}


@dataclass
class ImportErrorRow:
    row: int
    column: str
    error: str
    value: Any


def normalize_boolean(value: Any) -> int:
    normalized = str(value or "").strip().lower()
    return 1 if normalized in {"si", "sí", "x", "1", "true"} else 0


def normalize_class(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    normalized = NORMALIZE_CLASS.get(normalized, normalized.replace(" ", "_"))
    return normalized


def validate_human_records(records: list[dict[str, Any]], existing_codes: set[str]) -> tuple[list[dict[str, Any]], list[ImportErrorRow]]:
    valid: list[dict[str, Any]] = []
    errors: list[ImportErrorRow] = []

    if not records:
        return valid, [ImportErrorRow(0, "archivo", "ERR_EMPTY_FILE", "")]

    missing_columns = REQUIRED_COLUMNS - set(records[0].keys())
    for column in sorted(missing_columns):
        errors.append(ImportErrorRow(0, column, "ERR_MISSING_COLUMN", column))
    if missing_columns:
        return valid, errors

    seen: set[tuple[str, str]] = set()
    for index, record in enumerate(records, 2):
        code = str(record.get("codigo_imagen") or "").strip()
        evaluator = str(record.get("evaluador") or "").strip()
        human_class = normalize_class(record.get("etiqueta_final_humana"))
        decision = str(record.get("decision_humana") or "").strip().lower()
        time_value = record.get("tiempo_segundos")
        row_has_error = False

        if not code:
            errors.append(ImportErrorRow(index, "codigo_imagen", "ERR_REQUIRED", code))
            row_has_error = True
        elif code not in existing_codes:
            errors.append(ImportErrorRow(index, "codigo_imagen", "ERR_IMAGE_NOT_FOUND", code))
            row_has_error = True

        if not evaluator:
            errors.append(ImportErrorRow(index, "evaluador", "ERR_REQUIRED", evaluator))
            row_has_error = True

        if human_class not in HUMAN_CLASS_CATALOG:
            errors.append(ImportErrorRow(index, "etiqueta_final_humana", "ERR_INVALID_CLASS", record.get("etiqueta_final_humana")))
            row_has_error = True

        if decision not in VALID_DECISIONS:
            errors.append(ImportErrorRow(index, "decision_humana", "ERR_INVALID_DECISION", decision))
            row_has_error = True

        try:
            seconds = float(time_value)
        except (TypeError, ValueError):
            errors.append(ImportErrorRow(index, "tiempo_segundos", "ERR_NOT_NUMERIC", time_value))
            row_has_error = True
            seconds = 0.0

        if seconds <= 0:
            errors.append(ImportErrorRow(index, "tiempo_segundos", "ERR_NOT_POSITIVE", time_value))
            row_has_error = True

        key = (code, evaluator)
        if key in seen:
            errors.append(ImportErrorRow(index, "codigo_imagen/evaluador", "ERR_DUPLICATE_EVALUATION", key))
            row_has_error = True
        seen.add(key)

        if not row_has_error:
            valid.append(
                {
                    **record,
                    "codigo_imagen": code,
                    "evaluador": evaluator,
                    "etiqueta_final_humana": human_class,
                    "decision_humana": decision,
                    "tiempo_segundos": seconds,
                    "defecto_danado": normalize_boolean(record.get("defecto_danado")),
                    "defecto_carbonizado": normalize_boolean(record.get("defecto_carbonizado")),
                    "defecto_aplastado": normalize_boolean(record.get("defecto_aplastado")),
                    "impureza_vegetal": normalize_boolean(record.get("impureza_vegetal")),
                    "impureza_mineral": normalize_boolean(record.get("impureza_mineral")),
                }
            )

    return valid, errors
