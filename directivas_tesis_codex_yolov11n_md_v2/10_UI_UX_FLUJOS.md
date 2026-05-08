# UI/UX y flujos de la herramienta

## Principio de diseño

La herramienta debe guiar al tesista por el método, no solo mostrar pantallas.

Debe tener un flujo tipo investigación:

```text
Dataset -> Auditoría -> Ground truth -> Humano -> IA -> Comparación -> Reporte
```

## Menú principal

```text
1. Dashboard
2. Dataset
3. Etiquetado
4. Auditoría
5. Evaluación humana
6. Ground truth CODEX
7. Modelos IA
8. Inferencia
9. Comparación
10. Reportes
11. Configuración metodológica
```

## Pantalla 1: Dashboard general

Tarjetas:

```text
Imágenes totales
Etiquetas totales
Clases detectadas
Imágenes auditadas
Ground truth completo
Evaluaciones humanas cargadas
Inferencias realizadas
Test bloqueado
```

Alertas:

```text
Faltan ground truth
Faltan tiempos humanos
Hay clases desbalanceadas
Hay etiquetas inválidas
Hay imágenes duplicadas en splits
El test todavía no está bloqueado
```

## Pantalla 2: Dataset

Funciones:

```text
Subir imágenes
Crear lote
Asignar sesión
Ver metadatos
Detectar duplicados
Ver imágenes no válidas
Asignar split
Bloquear test
```

Vista de tabla:

| Imagen | Lote | Sesión | Split | Estado | Etiquetas | Ground truth |
|---|---|---|---|---|---:|---|

## Pantalla 3: Etiquetado

Componentes:

```text
Lista lateral de imágenes
Canvas central con cajas
Panel derecho de etiquetas
Panel inferior de observaciones
```

Acciones:

```text
Crear caja
Editar caja
Cambiar clase
Eliminar caja
Marcar observada
Aprobar auditoría
Excluir imagen
```

## Pantalla 4: Auditoría

Objetivo:

Revisar calidad de etiquetas antes de entrenamiento.

Filtros:

```text
clase
estado
error
lote
split
anotador
```

Vista:

```text
Antes / después de corrección
Historial de cambios
Motivo de auditoría
Botón aprobar
```

## Pantalla 5: Evaluación humana

Funciones:

```text
Importar Excel
Validar columnas
Ver errores
Normalizar datos
Ver evaluadores
Ver tiempos
Calcular acuerdo entre evaluadores
```

Vista:

| Imagen | Evaluador | Clase humana | Decisión | Tiempo | Estado |
|---|---|---|---|---:|---|

## Pantalla 6: Ground truth CODEX

Debe tener modo ciego.

Modo ciego:

```text
No mostrar IA.
No mostrar evaluación humana.
Solo imagen y criterios CODEX.
```

Formulario:

```text
clase_principal_real
defectos_multietiqueta
decision_real
severidad_larvas
observacion
fuente_ground_truth
nivel_confianza
```

Botones:

```text
Guardar
Marcar discrepante
Solicitar consenso
Bloquear ground truth
```

## Pantalla 7: Modelos IA

Funciones:

```text
Registrar modelo
Ver best.pt
Ver hash
Ver dataset usado
Ver hiperparámetros
Ver métricas de validación
```

Tabla:

| Versión | Dataset | Epochs | mAP50 | mAP50-95 | Fecha |
|---|---|---:|---:|---:|---|

## Pantalla 8: Inferencia

Funciones:

```text
Seleccionar lote
Seleccionar modelo
Configurar confidence
Configurar IoU
Ejecutar
Ver progreso
Ver errores
```

Resultado:

| Imagen | Clase modelo | Decisión | Detecciones | Tiempo ms |
|---|---|---|---:|---:|

## Pantalla 9: Comparación

Debe mostrar la tabla central de la tesis.

| Imagen | Ground truth | Humano | IA | Humano correcto | IA correcto | Tiempo humano | Tiempo IA |
|---|---|---|---|---|---|---:|---:|

Filtros:

```text
solo errores IA
solo errores humano
discordantes
por clase
por lote
por evaluador
```

## Pantalla 10: Reportes

Exportar:

```text
reporte_dataset.xlsx
reporte_auditoria.xlsx
reporte_humano.xlsx
reporte_modelo.xlsx
reporte_comparativo.xlsx
reporte_tesis.md
reporte_tesis.pdf
```

## Pantalla 11: Configuración metodológica

Aquí se congelan reglas.

Configurable:

```text
clases
prioridad de clase principal
reglas de decisión CODEX proxy
umbral de confidence
umbral IoU
split train/val/test
modo normal con caja o sin caja
método de consenso
```

Cuando se cierre la configuración:

```text
metodologia_locked = true
```

Ningún reporte final debe generarse si la metodología está abierta.

## Flujo ideal para el usuario

```text
1. Subir imágenes.
2. Importar etiquetas YOLO.
3. Revisar dashboard de errores.
4. Corregir etiquetas.
5. Auditar etiquetas.
6. Exportar dataset YOLO.
7. Entrenar modelo.
8. Registrar modelo.
9. Importar Excel humano.
10. Crear ground truth CODEX.
11. Ejecutar inferencia IA.
12. Comparar.
13. Exportar reportes.
```
