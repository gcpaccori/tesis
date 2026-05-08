#!/usr/bin/env python3
import argparse
import asyncio
import csv
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx


LABEL_GUIDE = {
    "dañado": "SOLO dano fisico claro: mordedura, rotura, hueco, tejido arrancado, pudricion localizada. No marques por color marron, arrugas normales o hongo seco.",
    "carbonizado": "SOLO zonas negras tipo quemado/carbon/necrosis intensa y localizada. No marques por sombra, piel marron oscura o iluminacion.",
    "aplastado": "SOLO deformacion evidente por presion: hongo comprimido, plano, esmagado o colapsado mecanicamente.",
    "larvas": "SOLO larvas/gusanos/insectos visibles o tuneles claros de larva. No inferir si no se ven organismos/rastros.",
    "impureza_vegetal": "SOLO restos vegetales visibles: hojas, agujas, pasto, tallos, musgo, fibras vegetales pegadas o junto al hongo.",
    "impureza_mineral": "SOLO tierra, arena, barro, piedras, polvo mineral, grava o sustrato mineral adherido/visible.",
    "pie_desprendido": "SOLO pie/tallo separado fisicamente del sombrero o trozo de pie suelto visible.",
    "contaminante": "SOLO cuerpo extrano visible no cubierto por mineral/vegetal/larva/pluma, por ejemplo plastico o basura.",
    "pluma": "SOLO pluma o fragmento de pluma visible.",
}


SYSTEM_PROMPT = """Eres un etiquetador visual experto de ALTA PRECISION para control de calidad de Suillus luteus.
Debes escoger SOLO entre las etiquetas permitidas. No inventes clases.
Prioridad: evitar falsos positivos. Si una etiqueta no es claramente visible, NO la marques.
Puede haber imagenes sin ninguna de las etiquetas objetivo; en ese caso labels_present=[].
Tarea: multi-label image classification, no segmentacion. Si no hay evidencia suficiente, usa needs_review=true.
Devuelve SOLO JSON valido, sin markdown."""


def load_ndjson(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dataset = {}
    images = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("type") == "dataset":
            dataset = obj
        elif obj.get("type") == "image":
            images.append(obj)
    return dataset, images


def annotated_labels(image: dict[str, Any], class_names: dict[str, str]) -> list[str]:
    annotations = image.get("annotations")
    labels: list[str] = []
    if isinstance(annotations, dict):
        for segment in annotations.get("segments", []) or []:
            if segment:
                name = class_names.get(str(segment[0]))
                if name and name not in labels:
                    labels.append(name)
    return labels


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def normalize_prediction(raw: dict[str, Any], labels: list[str]) -> dict[str, Any]:
    present = raw.get("labels_present") or raw.get("labels") or []
    if isinstance(present, str):
        present = [present]
    present = [x for x in present if x in labels]
    absent = [x for x in labels if x not in present]
    confidences = raw.get("confidence_by_label") or {}
    if not isinstance(confidences, dict):
        confidences = {}
    cleaned_conf = {}
    for label in labels:
        try:
            cleaned_conf[label] = max(0.0, min(1.0, float(confidences.get(label, 0.0))))
        except Exception:
            cleaned_conf[label] = 0.0
    overall = raw.get("overall_confidence", max([cleaned_conf[x] for x in present] or [0.0]))
    try:
        overall = max(0.0, min(1.0, float(overall)))
    except Exception:
        overall = 0.0
    review = bool(raw.get("needs_review", False))
    if overall < 0.78 or any(cleaned_conf.get(x, 0) < 0.72 for x in present):
        review = True
    return {
        "labels_present": present,
        "labels_absent": absent,
        "confidence_by_label": cleaned_conf,
        "overall_confidence": overall,
        "evidence": str(raw.get("evidence") or raw.get("razon") or "")[:700],
        "visual_notes": str(raw.get("visual_notes") or raw.get("notas") or "")[:700],
        "needs_review": review,
        "review_reason": str(raw.get("review_reason") or "")[:400],
    }


def prompt_for(image: dict[str, Any], labels: list[str], class_counts: Counter[str]) -> str:
    guide = "\n".join(f"- {name}: {LABEL_GUIDE.get(name, '')}" for name in labels)
    priors = ", ".join(f"{k}={v}" for k, v in class_counts.most_common())
    return f"""Imagen: {image.get('file')}
Dimensiones: {image.get('width')}x{image.get('height')}
Dataset: Suillus luteus con contaminantes/defectos.
Regla critica: no etiquetes el hongo normal como dañado solo por ser marron, oscuro, rugoso, seco o tener forma irregular natural.
Marca una etiqueta solo cuando haya evidencia visual concreta del defecto/contaminante.
Etiquetas permitidas:
{guide}
Frecuencia en 200 ejemplos anotados: {priors}

Responde JSON exacto:
{{
  "labels_present": ["impureza_vegetal"],
  "confidence_by_label": {{"dañado":0.0,"carbonizado":0.0,"aplastado":0.0,"larvas":0.0,"impureza_vegetal":0.0,"impureza_mineral":0.0,"pie_desprendido":0.0,"contaminante":0.0,"pluma":0.0}},
  "overall_confidence": 0.0,
  "evidence": "rasgos visuales concretos",
  "visual_notes": "ubicacion aproximada y textura/color",
  "needs_review": true,
  "review_reason": "por que revisar o vacio si confianza alta"
}}"""


async def label_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    endpoint: str,
    model: str,
    image: dict[str, Any],
    labels: list[str],
    class_counts: Counter[str],
    max_tokens: int,
    retries: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_for(image, labels, class_counts)},
                    {"type": "image_url", "image_url": {"url": image["url"]}},
                ],
            },
        ],
        "temperature": 0.0,
        "top_p": 0.9,
        "max_tokens": max_tokens,
        "stream": False,
    }
    last_error = ""
    for attempt in range(retries + 1):
        try:
            async with semaphore:
                started = time.perf_counter()
                response = await client.post(endpoint, json=payload, timeout=240)
                elapsed = time.perf_counter() - started
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"].get("content") or ""
            raw = extract_json(content)
            pred = normalize_prediction(raw, labels)
            pred.update(
                {
                    "file": image.get("file"),
                    "url": image.get("url"),
                    "width": image.get("width"),
                    "height": image.get("height"),
                    "split": image.get("split"),
                    "elapsed_sec": round(elapsed, 3),
                    "status": "ok",
                    "raw_response": content[:2000],
                }
            )
            return pred
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            await asyncio.sleep(1.5 * (attempt + 1))
    return {
        "file": image.get("file"),
        "url": image.get("url"),
        "width": image.get("width"),
        "height": image.get("height"),
        "split": image.get("split"),
        "labels_present": [],
        "labels_absent": labels,
        "confidence_by_label": {x: 0.0 for x in labels},
        "overall_confidence": 0.0,
        "evidence": "",
        "visual_notes": "",
        "needs_review": True,
        "review_reason": last_error,
        "elapsed_sec": 0.0,
        "status": "error",
        "raw_response": "",
    }


def write_outputs(out_dir: Path, dataset: dict[str, Any], images: list[dict[str, Any]], predictions: list[dict[str, Any]], labels: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_by_file = {p["file"]: p for p in predictions}
    (out_dir / "predictions.jsonl").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in predictions) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "predictions.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "split",
                "labels_present",
                "overall_confidence",
                "needs_review",
                "review_reason",
                "evidence",
                "visual_notes",
                "status",
                "elapsed_sec",
            ],
        )
        writer.writeheader()
        for p in predictions:
            row = dict(p)
            row["labels_present"] = "|".join(p.get("labels_present", []))
            writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
    with (out_dir / "roboflow_multilabel_tags.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", *labels, "needs_review", "confidence", "suggested_labels"])
        for p in predictions:
            present = set(p.get("labels_present", []))
            writer.writerow(
                [
                    p["file"],
                    *[1 if label in present else 0 for label in labels],
                    int(bool(p.get("needs_review"))),
                    p.get("overall_confidence", 0),
                    "|".join(p.get("labels_present", [])),
                ]
            )
    with (out_dir / "needs_review.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "suggested_labels", "confidence", "reason", "url"])
        for p in predictions:
            if p.get("needs_review"):
                writer.writerow([p["file"], "|".join(p.get("labels_present", [])), p.get("overall_confidence", 0), p.get("review_reason") or p.get("evidence"), p.get("url")])
    with (out_dir / "auto_labeled.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "suggested_labels", "confidence", "evidence", "url"])
        for p in predictions:
            if not p.get("needs_review"):
                writer.writerow([p["file"], "|".join(p.get("labels_present", [])), p.get("overall_confidence", 0), p.get("evidence"), p.get("url")])
    enriched = []
    enriched.append(dataset)
    for image in images:
        obj = dict(image)
        if image.get("file") in pred_by_file:
            obj["gemma_prediction"] = {k: v for k, v in pred_by_file[image["file"]].items() if k not in {"raw_response"}}
        enriched.append(obj)
    (out_dir / "enriched_predictions.ndjson").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in enriched) + "\n",
        encoding="utf-8",
    )
    summary = {
        "total_predictions": len(predictions),
        "auto_labeled": sum(1 for p in predictions if not p.get("needs_review")),
        "needs_review": sum(1 for p in predictions if p.get("needs_review")),
        "status_counts": Counter(p.get("status") for p in predictions),
        "label_counts": Counter(label for p in predictions for label in p.get("labels_present", [])),
        "outputs": {
            "predictions_jsonl": str(out_dir / "predictions.jsonl"),
            "predictions_csv": str(out_dir / "predictions.csv"),
            "roboflow_multilabel_tags_csv": str(out_dir / "roboflow_multilabel_tags.csv"),
            "needs_review_csv": str(out_dir / "needs_review.csv"),
            "auto_labeled_csv": str(out_dir / "auto_labeled.csv"),
            "enriched_predictions_ndjson": str(out_dir / "enriched_predictions.ndjson"),
        },
    }
    clean_summary = json.loads(json.dumps(summary, default=dict, ensure_ascii=False))
    (out_dir / "summary.json").write_text(json.dumps(clean_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "README_RESULTADOS.md").write_text(
        f"""# Resultados Gemma Suillus

Total procesadas: {summary['total_predictions']}
Auto-etiquetadas: {summary['auto_labeled']}
Para revisar: {summary['needs_review']}

Archivos principales:

- `predictions.csv`: predicciones legibles.
- `roboflow_multilabel_tags.csv`: matriz multi-label por filename para llevar a Roboflow como tags/clases auxiliares.
- `auto_labeled.csv`: sugerencias con confianza alta.
- `needs_review.csv`: cola para revisar manualmente.
- `enriched_predictions.ndjson`: NDJSON original enriquecido con `gemma_prediction`.

Nota: esto NO genera poligonos de segmentacion. Genera etiquetas visuales sugeridas para priorizar y acelerar Roboflow.
""",
        encoding="utf-8",
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8098/v1")
    parser.add_argument("--model", default="gemma-4-26b-a4b-agents")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--include-labeled", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=420)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    dataset, images = load_ndjson(input_path)
    class_names = {str(k): v for k, v in dataset.get("class_names", {}).items()}
    labels = [class_names[str(i)] for i in sorted(map(int, class_names.keys()))]
    class_counts: Counter[str] = Counter()
    for image in images:
        class_counts.update(annotated_labels(image, class_names))
    targets = [image for image in images if args.include_labeled or not image.get("annotations")]
    if args.limit:
        targets = targets[: args.limit]

    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = out_dir / "predictions.jsonl"
    done: dict[str, dict[str, Any]] = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                done[item["file"]] = item
    remaining = [image for image in targets if image.get("file") not in done]

    endpoint = args.base_url.rstrip("/") + "/chat/completions"
    semaphore = asyncio.Semaphore(args.concurrency)
    started = time.perf_counter()
    async with httpx.AsyncClient() as client:
        with checkpoint.open("a", encoding="utf-8") as f:
            tasks = [
                label_one(client, semaphore, endpoint, args.model, image, labels, class_counts, args.max_tokens, args.retries)
                for image in remaining
            ]
            completed = 0
            for coro in asyncio.as_completed(tasks):
                result = await coro
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush()
                done[result["file"]] = result
                completed += 1
                if completed % 25 == 0 or completed == len(tasks):
                    elapsed = time.perf_counter() - started
                    print(f"processed={completed}/{len(tasks)} total_done={len(done)}/{len(targets)} ips={completed/max(elapsed,0.001):.3f}", flush=True)
    predictions = [done[image["file"]] for image in targets if image.get("file") in done]
    write_outputs(out_dir, dataset, images, predictions, labels)
    print(json.dumps(json.loads((out_dir / "summary.json").read_text(encoding="utf-8")), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
