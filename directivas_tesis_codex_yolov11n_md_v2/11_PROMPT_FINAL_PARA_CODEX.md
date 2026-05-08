# Prompt final para Codex / agente programador

Actúa como arquitecto full-stack y desarrollador senior. Construye una herramienta web/local para validar una tesis de visión artificial con YOLOv11n aplicada a hongos comestibles desecados según CODEX STAN 39-1981.

## Contexto de tesis

La investigación compara clasificación manual realizada por trabajadores contra clasificación automática realizada por YOLOv11n. La comparación debe hacerse sobre las mismas imágenes y contra una verdad de referencia CODEX auditada. El Excel de trabajadores no es la verdad absoluta; es la evaluación humana. La IA tampoco es verdad absoluta. Ambos métodos se comparan contra ground truth.

## Objetivo de la herramienta

Implementar un sistema que permita:

1. Gestionar imágenes y lotes.
2. Visualizar y auditar etiquetas YOLO.
3. Importar evaluaciones humanas desde Excel.
4. Registrar ground truth CODEX.
5. Ejecutar inferencia con YOLOv11n.
6. Comparar humano vs IA.
7. Calcular métricas de tesis.
8. Exportar reportes.

## Stack sugerido

Backend:

- Python FastAPI o Node/NestJS.
- MySQL o PostgreSQL.
- Python para inferencia YOLOv11n con Ultralytics.
- Pandas/OpenPyXL para Excel.
- Scikit-learn/scipy/statsmodels para métricas.

Frontend:

- React + Vite + TypeScript + shadcn, no deve haber ninguna construcion de codigo para botones o cosas asi en estilos ni nada, ahorrar tokens en fronted y dejarlo limpio y completo es la micion.
- TanStack Query.
- Zustand o Context para estado.
- Canvas/SVG para cajas sobre imágenes.
- Componentes limpios y reutilizables.

## Clases YOLO

```yaml
names:
  0: normal
  1: danado
  2: carbonizado
  3: aplastado
  4: larvas
  5: impureza_vegetal
  6: impureza_mineral
  7: pie_desprendido
```

## Módulos obligatorios

### 1. Dataset

- Crear lotes.
- Subir imágenes.
- Guardar metadatos.
- Detectar duplicados.
- Asignar split train/val/test.
- Bloquear test.

### 2. Etiquetado y auditoría

- Cargar archivos YOLO `.txt`.
- Dibujar cajas sobre imagen.
- Crear/editar/eliminar cajas.
- Validar coordenadas YOLO.
- Marcar estados: pendiente, etiquetada, observada, corregida, auditada, excluida.
- Registrar historial de auditoría.
- Exportar dataset YOLO limpio.

### 3. Importación Excel humano

- Importar Excel con evaluación de trabajadores.
- Validar columnas.
- Normalizar valores.
- Asociar cada fila a `codigo_imagen`.
- Guardar tiempos humanos.
- Permitir varios evaluadores.
- Calcular acuerdo inter-evaluador.

### 4. Ground truth CODEX

- Registrar verdad de referencia por imagen.
- Permitir modo ciego.
- Guardar clase principal real, defectos multietiqueta y decisión real.
- Registrar auditor, fuente, observación y nivel de confianza.
- Permitir bloqueo del ground truth.

### 5. Inferencia IA

- Registrar modelos YOLOv11n.
- Guardar versión, hash, hiperparámetros y dataset usado.
- Ejecutar inferencia sobre lote.
- Guardar detecciones: clase, confianza, bbox, tiempo.
- Calcular clase principal del modelo.
- Calcular decisión modelo.

### 6. Comparación

Crear tabla:

| Imagen | Ground truth | Humano | IA | Humano correcto | IA correcto | Tiempo humano | Tiempo IA |

Calcular:

- accuracy humano,
- accuracy modelo,
- precision/recall/F1 por clase,
- mAP@0.5,
- mAP@0.5:0.95,
- matriz de confusión humana,
- matriz de confusión modelo,
- kappa,
- McNemar,
- diferencia de tiempos,
- Wilcoxon o t pareada para tiempos.

### 7. Reportes

Exportar:

- reporte dataset,
- reporte auditoría,
- reporte evaluación humana,
- reporte inferencia modelo,
- reporte comparativo,
- matrices de confusión,
- tabla McNemar,
- tabla kappa,
- comparación de tiempos,
- reporte final en Markdown/Excel/PDF.

## Reglas metodológicas obligatorias

1. El Excel humano no es ground truth.
2. El ground truth debe ser auditado.
3. La IA y los humanos deben evaluar las mismas imágenes.
4. El trabajador no debe ver predicciones IA.
5. El modelo no debe entrenarse con test.
6. El test debe bloquearse antes de evaluación final.
7. La configuración metodológica debe poder bloquearse.
8. Cada inferencia debe registrar versión del modelo y parámetros.
9. Cada cambio de etiqueta debe tener auditoría.
10. No afirmar mediciones fisicoquímicas desde imagen; usar proxy visual declarado.

## Entregable técnico esperado

Genera el proyecto con:

```text
backend/
frontend/
database/
docs/
scripts/
README.md
```

Incluye:

```text
migraciones SQL
endpoints API
componentes frontend
servicio de inferencia YOLO
servicio de importación Excel
servicio de métricas
datos mock para pruebas
pruebas básicas
```

## Criterio final

El sistema está bien si permite sustentar la tesis con evidencia reproducible, no solo con pantallas bonitas.
