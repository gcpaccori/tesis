from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.services.ndjson_dataset import COOPERATIVE_NAME, load_ndjson_dataset

INSTRUMENTS: list[dict[str, Any]] = [
    {
        "code": "I1",
        "name": "Protocolo de captura",
        "purpose": "Controlar iluminacion, fondo, distancia, escala y calidad de imagen.",
        "validates": "Calidad de adquisicion de datos.",
        "does_not_validate": "No mide desempeno humano ni desempeno del modelo.",
        "evidence": "Checklist de captura, conteo de imagenes validas/excluidas y motivo de exclusion.",
        "status": "parcial",
        "download": "/api/instruments/I1/export",
        "suggested_capture": "Figura X. Registro del protocolo de captura aplicado al lote de imagenes de evaluacion.",
    },
    {
        "code": "I2",
        "name": "Guia de anotacion CODEX-YOLO",
        "purpose": "Traducir CODEX STAN 39-1981 a clases visuales anotables.",
        "validates": "Operacionalizacion visual del estandar CODEX.",
        "does_not_validate": "No prueba por si sola que el modelo detecte bien.",
        "evidence": "Clases, criterios de inclusion/exclusion, unidad de anotacion y ejemplos.",
        "status": "listo",
        "download": "/api/instruments/I2/export",
        "suggested_capture": "Figura X. Interfaz de guia de anotacion basada en CODEX-YOLO.",
    },
    {
        "code": "I3",
        "name": "Ficha de evaluacion humana",
        "purpose": "Registrar clasificacion manual, decision y tiempo por imagen.",
        "validates": "Metodo manual como objeto de comparacion.",
        "does_not_validate": "No es ground truth.",
        "evidence": "Excel humano validado por columnas, evaluador, clase, decision y tiempo.",
        "status": "listo",
        "download": "/api/instruments/I3/export",
        "suggested_capture": "Figura X. Validacion de la ficha de evaluacion humana importada.",
    },
    {
        "code": "I4",
        "name": "Bitacora de entrenamiento YOLOv11n",
        "purpose": "Versionar modelo, dataset, hiperparametros y metrica de validacion.",
        "validates": "Trazabilidad del entrenamiento.",
        "does_not_validate": "No reemplaza evaluacion final en test bloqueado.",
        "evidence": "Modelo, hash, epochs, imgsz, optimizer, dataset y mAP de validacion.",
        "status": "parcial",
        "download": "/api/instruments/I4/export",
        "suggested_capture": "Figura X. Bitacora de entrenamiento del modelo YOLOv11n.",
    },
    {
        "code": "I5",
        "name": "Registro de tiempos",
        "purpose": "Comparar eficiencia de trabajadores frente al modelo.",
        "validates": "Eficiencia temporal bajo condiciones pareadas.",
        "does_not_validate": "No mide productividad industrial completa.",
        "evidence": "Tiempo humano, tiempo IA, promedio, diferencia y factor de velocidad.",
        "status": "listo",
        "download": "/api/instruments/I5/export",
        "suggested_capture": "Figura X. Comparacion de tiempos por imagen entre evaluacion humana e IA.",
    },
    {
        "code": "I6",
        "name": "Validez de contenido - V de Aiken",
        "purpose": "Validar guia/ficha con juicio de expertos.",
        "validates": "Pertinencia, claridad y coherencia de los instrumentos.",
        "does_not_validate": "No mide accuracy del modelo.",
        "evidence": "Puntajes por experto, item, V de Aiken e intervalo/observacion.",
        "status": "pendiente",
        "download": "/api/instruments/I6/export",
        "suggested_capture": "Figura X. Validez de contenido mediante V de Aiken.",
    },
    {
        "code": "I7",
        "name": "Concordancia / kappa",
        "purpose": "Medir acuerdo entre evaluadores o anotadores.",
        "validates": "Confiabilidad del etiquetado o evaluacion humana.",
        "does_not_validate": "No reemplaza accuracy contra ground truth.",
        "evidence": "Kappa, acuerdo observado, evaluadores y clases con desacuerdo.",
        "status": "parcial",
        "download": "/api/instruments/I7/export",
        "suggested_capture": "Figura X. Concordancia entre evaluadores mediante kappa.",
    },
    {
        "code": "I8",
        "name": "Ground truth CODEX auditado",
        "purpose": "Crear la referencia contra la cual se comparan humano e IA.",
        "validates": "Referencia experta basada en guia CODEX-YOLO.",
        "does_not_validate": "No proviene del Excel humano ni de la prediccion IA.",
        "evidence": "Clase real, decision, auditor, confianza, bloqueo y observacion.",
        "status": "listo",
        "download": "/api/instruments/I8/export",
        "suggested_capture": "Figura X. Ground truth CODEX auditado y bloqueado.",
    },
    {
        "code": "I9",
        "name": "Reporte de inferencia IA",
        "purpose": "Guardar salida del modelo por imagen.",
        "validates": "Ejecucion reproducible de YOLOv11n.",
        "does_not_validate": "No es verdad absoluta.",
        "evidence": "Run ID, modelo, umbrales, clase, decision, detecciones y tiempo.",
        "status": "parcial",
        "download": "/api/instruments/I9/export",
        "suggested_capture": "Figura X. Reporte de inferencia del modelo YOLOv11n.",
    },
    {
        "code": "I10",
        "name": "Reporte estadistico final",
        "purpose": "Probar hipotesis y sustentar resultados.",
        "validates": "Desempeno, concordancia, McNemar y eficiencia.",
        "does_not_validate": "No debe generarse sin datos pareados completos.",
        "evidence": "Accuracy, precision, recall, F1, mAP, kappa, McNemar y tiempos.",
        "status": "parcial",
        "download": "/api/instruments/I10/export",
        "suggested_capture": "Figura X. Tablero final de hipotesis y metricas de tesis.",
    },
]


def validation_state() -> list[dict[str, Any]]:
    dataset = load_ndjson_dataset()
    summary = dataset["summary"]
    return [
        {
            "item": "Protocolo de captura",
            "status": "parcial",
            "evidence": "Hay metadatos de imagen, falta completar checklist formal de captura.",
            "block_if_missing": False,
        },
        {
            "item": "Guia CODEX-YOLO",
            "status": "listo",
            "evidence": "Clases y criterios operacionalizados en directivas y app.",
            "block_if_missing": True,
        },
        {
            "item": "Dataset especialista",
            "status": "parcial",
            "evidence": f"{summary['annotated_images']} imagenes etiquetadas y {summary['unlabeled_images']} pendientes.",
            "block_if_missing": True,
        },
        {
            "item": "Ground truth",
            "status": "listo",
            "evidence": "Exportable desde NDJSON especialista para imagenes etiquetadas.",
            "block_if_missing": True,
        },
        {
            "item": "Excel humano",
            "status": "listo",
            "evidence": "Excel humano simulado disponible para prueba funcional.",
            "block_if_missing": True,
        },
        {
            "item": "V de Aiken",
            "status": "pendiente",
            "evidence": "Plantilla generada; requiere calificacion real de expertos.",
            "block_if_missing": False,
        },
        {
            "item": "McNemar y kappa",
            "status": "parcial",
            "evidence": "Metricas demo disponibles; deben recalcularse con evaluacion real final.",
            "block_if_missing": True,
        },
    ]


def traceability_rows() -> list[dict[str, str]]:
    return [
        {
            "objetivo": "Operacionalizar CODEX en clases visuales",
            "instrumento": "I2, I6",
            "insumo": "CODEX STAN 39-1981 y criterio experto",
            "salida": "Guia CODEX-YOLO validada",
            "metrica": "V de Aiken",
            "captura_sugerida": "Guia de anotacion + planilla V de Aiken",
        },
        {
            "objetivo": "Construir referencia auditada",
            "instrumento": "I8",
            "insumo": "Etiquetas especialista NDJSON",
            "salida": "Ground truth bloqueado",
            "metrica": "Cobertura GT y auditoria",
            "captura_sugerida": "Ground truth CODEX auditado",
        },
        {
            "objetivo": "Evaluar desempeno YOLOv11n",
            "instrumento": "I4, I9, I10",
            "insumo": "Modelo e imagenes test",
            "salida": "Detecciones y metricas",
            "metrica": "Precision, recall, F1, mAP",
            "captura_sugerida": "Reporte de inferencia + matriz de confusion",
        },
        {
            "objetivo": "Comparar humano vs IA",
            "instrumento": "I3, I5, I7, I10",
            "insumo": "Mismas imagenes con GT, humano e IA",
            "salida": "Tabla pareada",
            "metrica": "Accuracy, kappa, McNemar, tiempos",
            "captura_sugerida": "Tabla comparativa y tablero de hipotesis",
        },
    ]


def instruments_payload() -> dict[str, Any]:
    return {
        "cooperative": COOPERATIVE_NAME,
        "instruments": INSTRUMENTS,
        "validation_state": validation_state(),
        "traceability": traceability_rows(),
    }


def instrument_sheet_rows(code: str) -> list[dict[str, Any]]:
    instrument = next((item for item in INSTRUMENTS if item["code"] == code), None)
    if instrument is None:
        raise KeyError(code)

    if code == "I1":
        return [
            {"campo": "codigo_sesion", "valor": "SES_CASAEC_2026_001", "estado": "editable"},
            {"campo": "fecha", "valor": "2026-05-07", "estado": "editable"},
            {"campo": "fondo_uniforme", "valor": "SI", "estado": "por confirmar"},
            {"campo": "iluminacion_difusa", "valor": "SI", "estado": "por confirmar"},
            {"campo": "distancia_fija", "valor": "SI", "estado": "por confirmar"},
            {"campo": "sombras_controladas", "valor": "SI", "estado": "por confirmar"},
        ]
    if code == "I2":
        return [
            {"class_id": 0, "clase": "danado", "criterio": "Perdida visible de material o dano estructural."},
            {"class_id": 1, "clase": "carbonizado", "criterio": "Vestigios oscuros compatibles con carbonizacion."},
            {"class_id": 2, "clase": "aplastado", "criterio": "Fragmento o deformacion compatible con aplastamiento."},
            {"class_id": 3, "clase": "larvas", "criterio": "Agujeros visibles compatibles con dano por larvas."},
            {"class_id": 4, "clase": "impureza_vegetal", "criterio": "Materia vegetal ajena al hongo."},
            {"class_id": 5, "clase": "impureza_mineral", "criterio": "Tierra, arena o piedra visible."},
            {"class_id": 6, "clase": "pie_desprendido", "criterio": "Pie separado del sombrerete."},
            {"class_id": 7, "clase": "contaminante", "criterio": "Elemento visible ajeno al producto."},
            {"class_id": 8, "clase": "pluma", "criterio": "Pluma o fibra visible ajena al producto."},
        ]
    if code == "I3":
        return [
            {"columna": "codigo_imagen", "obligatoria": "SI", "descripcion": "Identificador de imagen"},
            {"columna": "evaluador", "obligatoria": "SI", "descripcion": "Trabajador/evaluador"},
            {"columna": "etiqueta_final_humana", "obligatoria": "SI", "descripcion": "Clase asignada por humano"},
            {"columna": "decision_humana", "obligatoria": "SI", "descripcion": "apto/no_apto/observado"},
            {"columna": "tiempo_segundos", "obligatoria": "SI", "descripcion": "Tiempo por imagen"},
        ]
    if code == "I6":
        return [
            {"item": "Claridad de definicion de clase", "experto_1": "", "experto_2": "", "experto_3": "", "v_aiken": ""},
            {"item": "Pertinencia con CODEX", "experto_1": "", "experto_2": "", "experto_3": "", "v_aiken": ""},
            {"item": "Coherencia de inclusion/exclusion", "experto_1": "", "experto_2": "", "experto_3": "", "v_aiken": ""},
            {"item": "Aplicabilidad en imagen RGB", "experto_1": "", "experto_2": "", "experto_3": "", "v_aiken": ""},
        ]
    return [
        {
            "instrumento": f"{instrument['code']} {instrument['name']}",
            "finalidad": instrument["purpose"],
            "valida": instrument["validates"],
            "evidencia": instrument["evidence"],
            "estado": instrument["status"],
        }
    ]


def export_all_instruments(path: Path) -> None:
    payload = instruments_payload()
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(payload["instruments"]).to_excel(writer, index=False, sheet_name="mapa_instrumentos")
        pd.DataFrame(payload["validation_state"]).to_excel(writer, index=False, sheet_name="estado_validacion")
        pd.DataFrame(payload["traceability"]).to_excel(writer, index=False, sheet_name="trazabilidad")
        for instrument in INSTRUMENTS:
            pd.DataFrame(instrument_sheet_rows(instrument["code"])).to_excel(
                writer,
                index=False,
                sheet_name=instrument["code"],
            )


def export_single_instrument(code: str, path: Path) -> None:
    instrument = next((item for item in INSTRUMENTS if item["code"] == code), None)
    if instrument is None:
        raise KeyError(code)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame([instrument]).to_excel(writer, index=False, sheet_name="resumen")
        pd.DataFrame(instrument_sheet_rows(code)).to_excel(writer, index=False, sheet_name=code)
