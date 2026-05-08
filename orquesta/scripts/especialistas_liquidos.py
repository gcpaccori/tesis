from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EspecialistaLiquido:
    key: str
    nombre: str
    mision: str
    foco: str
    activadores: tuple[str, ...]


ESPECIALISTAS = {
    "arquitectura": EspecialistaLiquido(
        key="arquitectura",
        nombre="Arquitecto Liquido",
        mision=(
            "Analiza estructuras, modulos, interfaces, dependencias y decisiones tecnicas. "
            "Propone disenos mantenibles sin salirse de la fase cognitiva."
        ),
        foco="Arquitectura, memoria, modelos, fronteras entre componentes y escalabilidad.",
        activadores=(
            "arquitectura",
            "diseno",
            "modulo",
            "orquestador",
            "memoria",
            "grafo",
            "estructura",
            "flujo",
        ),
    ),
    "forense": EspecialistaLiquido(
        key="forense",
        nombre="Forense Cognitivo",
        mision=(
            "Reconstruye causas, dependencias historicas, fallos y huellas. "
            "No ejecuta acciones operativas; solo explica y ordena evidencia."
        ),
        foco="Causa raiz, trazabilidad, secuencias, logs, evidencia y contexto historico.",
        activadores=(
            "forense",
            "causa",
            "incidente",
            "timeline",
            "evidencia",
            "rastro",
            "historial",
            "fallo",
            "error",
        ),
    ),
    "tensionador": EspecialistaLiquido(
        key="tensionador",
        nombre="Tensionador Cognitivo",
        mision=(
            "Presiona la idea desde la resiliencia conceptual. "
            "Busca riesgos, contradicciones y puntos ciegos sin ejecutar pruebas ni ataques."
        ),
        foco="Riesgos de diseno, supuestos fragiles, abuso conceptual y modos de falla.",
        activadores=(
            "riesgo",
            "fragil",
            "falla",
            "romper",
            "estres",
            "tortura",
            "objecion",
            "critica",
        ),
    ),
    "visual": EspecialistaLiquido(
        key="visual",
        nombre="Especialista Visual de Sistemas",
        mision=(
            "Piensa representaciones, mapas conceptuales y propuestas visuales "
            "para hacer legible la arquitectura sin implementar interfaces."
        ),
        foco="Diagramas, topologias, tableros mentales, vistas y UX conceptual.",
        activadores=(
            "visual",
            "diagrama",
            "pantalla",
            "ux",
            "ui",
            "mapa",
            "topologia",
            "vista",
        ),
    ),
}


def catalogo_especialistas() -> List[EspecialistaLiquido]:
    return list(ESPECIALISTAS.values())


def seleccionar_especialistas(mensaje: str, max_items: int = 2) -> List[EspecialistaLiquido]:
    contenido = (mensaje or "").lower()
    puntajes = {key: 0 for key in ESPECIALISTAS}

    for key, especialista in ESPECIALISTAS.items():
        for activador in especialista.activadores:
            if activador in contenido:
                puntajes[key] += 2

    if any(token in contenido for token in ("memoria", "grafo", "orquesta", "cognitiva")):
        puntajes["arquitectura"] += 2
    if any(token in contenido for token in ("debilidad", "riesgo", "limite", "failure", "edge case")):
        puntajes["tensionador"] += 2
    if any(token in contenido for token in ("explica", "por que", "que paso", "historial")):
        puntajes["forense"] += 1

    ordered_keys = [
        key
        for key, _ in sorted(puntajes.items(), key=lambda item: (-item[1], item[0]))
        if puntajes[key] > 0
    ]
    if not ordered_keys:
        ordered_keys = ["arquitectura"]

    return [ESPECIALISTAS[key] for key in ordered_keys[:max_items]]
