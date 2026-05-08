from __future__ import annotations

import math
from collections import Counter
from statistics import mean
from typing import Any

from app.constants import CLASSES


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def labels_for_series(*series: list[str], labels: list[str] | None = None) -> list[str]:
    if labels is not None:
        return list(dict.fromkeys(labels))
    present = set()
    for values in series:
        present.update(values)
    ordered = list(CLASSES)
    ordered.extend(sorted(present - set(ordered)))
    return ordered


def cohen_kappa(y_true: list[str], y_pred: list[str], labels: list[str] | None = None) -> float:
    total = len(y_true)
    if total == 0:
        return 0.0

    observed = sum(1 for real, pred in zip(y_true, y_pred, strict=False) if real == pred) / total
    true_counts = Counter(y_true)
    pred_counts = Counter(y_pred)
    metric_labels = labels_for_series(y_true, y_pred, labels=labels)
    expected = sum((true_counts[label] / total) * (pred_counts[label] / total) for label in metric_labels)
    return safe_div(observed - expected, 1 - expected)


def per_class_metrics(y_true: list[str], y_pred: list[str], labels: list[str] | None = None) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for class_name in labels_for_series(y_true, y_pred, labels=labels):
        tp = sum(1 for real, pred in zip(y_true, y_pred, strict=False) if real == class_name and pred == class_name)
        fp = sum(1 for real, pred in zip(y_true, y_pred, strict=False) if real != class_name and pred == class_name)
        fn = sum(1 for real, pred in zip(y_true, y_pred, strict=False) if real == class_name and pred != class_name)
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1 = safe_div(2 * precision * recall, precision + recall)
        output[class_name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": sum(1 for real in y_true if real == class_name),
        }
    return output


def confusion_matrix(y_true: list[str], y_pred: list[str], labels: list[str] | None = None) -> dict[str, dict[str, int]]:
    metric_labels = labels_for_series(y_true, y_pred, labels=labels)
    matrix = {real: {pred: 0 for pred in metric_labels} for real in metric_labels}
    for real, pred in zip(y_true, y_pred, strict=False):
        if real in matrix and pred in matrix[real]:
            matrix[real][pred] += 1
    return matrix


def mcnemar_table(rows: list[dict[str, Any]]) -> dict[str, float]:
    a = b = c = d = 0
    for row in rows:
        human_correct = bool(row["humano_correcto"])
        model_correct = bool(row["ia_correcto"])
        if human_correct and model_correct:
            a += 1
        elif human_correct and not model_correct:
            b += 1
        elif not human_correct and model_correct:
            c += 1
        else:
            d += 1

    denominator = b + c
    statistic = ((abs(b - c) - 1) ** 2 / denominator) if denominator else 0.0
    p_value = math.erfc(math.sqrt(statistic / 2)) if denominator else 1.0
    return {"a": a, "b": b, "c": c, "d": d, "statistic": statistic, "p_value": p_value}


def calculate_core_metrics(
    rows: list[dict[str, Any]],
    map50: float = 0.0,
    map5095: float = 0.0,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    total = len(rows)
    y_true = [row["ground_truth"] for row in rows]
    y_human = [row["humano"] for row in rows]
    y_model = [row["ia"] for row in rows]
    metric_labels = labels_for_series(y_true, y_human, y_model, labels=labels)

    human_times = [float(row["tiempo_humano"]) for row in rows]
    model_times = [float(row["tiempo_ia"]) / 1000 for row in rows]
    avg_human = mean(human_times) if human_times else 0.0
    avg_model = mean(model_times) if model_times else 0.0

    return {
        "total": total,
        "accuracy_humano": safe_div(sum(1 for row in rows if row["humano_correcto"]), total),
        "accuracy_modelo": safe_div(sum(1 for row in rows if row["ia_correcto"]), total),
        "kappa_humano": cohen_kappa(y_true, y_human, labels=metric_labels),
        "kappa_modelo": cohen_kappa(y_true, y_model, labels=metric_labels),
        "mcnemar": mcnemar_table(rows),
        "tiempos": {
            "promedio_humano": avg_human,
            "promedio_ia": avg_model,
            "factor_velocidad": safe_div(avg_human, avg_model),
            "diferencia_promedio": avg_human - avg_model,
        },
        "per_class_human": per_class_metrics(y_true, y_human, labels=metric_labels),
        "per_class_model": per_class_metrics(y_true, y_model, labels=metric_labels),
        "confusion_human": confusion_matrix(y_true, y_human, labels=metric_labels),
        "confusion_model": confusion_matrix(y_true, y_model, labels=metric_labels),
        "map50": map50,
        "map5095": map5095,
        "labels": metric_labels,
    }
