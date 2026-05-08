# Mapeo tesis -> herramienta ejecutable

## Propósito

Este archivo evita que el agente programador borre la lógica de tesis. Cada módulo debe existir porque responde a una parte metodológica de la investigación.

## Mapa general

| Elemento de la tesis | Qué debe construir la herramienta | Evidencia que genera |
|---|---|---|
| Pregunta de investigación | Comparación humano vs YOLOv11n bajo CODEX | Tabla pareada y métricas finales |
| Objetivo general | Sistema de validación integral | Reporte comparativo final |
| Clases CODEX operacionalizadas | Codebook y etiquetas YOLO | data.yaml, etiquetas auditadas |
| Protocolo de captura | Registro de lote/sesión/condiciones | Metadatos de imagen |
| Dataset YOLO | Módulo de carga y auditoría | Dataset limpio train/val/test |
| Guía de anotación | Interfaz de revisión de cajas | Historial de correcciones |
| Evaluación humana | Importador Excel | Tabla evaluacion_humana |
| Modelo YOLOv11n | Módulo de inferencia | Detecciones, confianza, tiempo |
| Ground truth | Auditoría experta CODEX | Tabla ground_truth |
| Desempeño técnico | Métricas YOLO | precision, recall, F1, mAP |
| Comparación pareada | Humano/modelo sobre mismas imágenes | McNemar, diferencias de acierto |
| Concordancia | Acuerdo humano-humano o humano-modelo | Kappa |
| Eficiencia | Registro de tiempos | Tiempo promedio humano vs IA |
| Limitaciones | Campo de proxy visual y observaciones | Reporte de límites del método |

## Capítulo de metodología convertido en flujo operativo

### Paso 1: captura

La herramienta registra:

```text
codigo_lote
codigo_imagen
fecha_captura
origen
tipo_presentacion
sesion_captura
condiciones de captura
```

Esto sostiene el protocolo de captura y permite evitar fuga de datos por sesiones similares.

### Paso 2: etiquetado

La herramienta permite cargar o crear etiquetas YOLO:

```text
class_id x_center y_center width height
```

También valida:

```text
clase existente
coordenadas normalizadas
caja dentro de imagen
archivo txt correspondiente
imagen sin etiqueta
clases desbalanceadas
duplicados entre splits
```

### Paso 3: auditoría

Cada imagen debe tener estado:

```text
pendiente
etiquetada
observada
corregida
auditada
excluida
test_bloqueado
```

La auditoría produce evidencia de calidad del dataset.

### Paso 4: partición

La tesis recomienda dividir dataset en:

```text
train = 70%
val = 20%
test = 10%
```

La herramienta debe advertir si hay fuga:

```text
la misma imagen en train y test
imágenes casi duplicadas entre splits
sesiones demasiado parecidas mezcladas en train/test
```

### Paso 5: entrenamiento

La herramienta registra bitácora:

```text
modelo base
versión YOLO
épocas
imgsz
batch
optimizer
learning rate
patience
fecha
hardware
ruta best.pt
métricas de validación
```

### Paso 6: evaluación humana

El Excel humano se importa como evaluación manual, no como verdad.

Columnas mínimas:

```text
codigo_imagen
evaluador
defecto_danado
defecto_carbonizado
defecto_aplastado
defecto_larvas
severidad_larvas
impureza_vegetal
impureza_mineral
pie_desprendido_cantidad
etiqueta_final_humana
decision_humana
tiempo_segundos
observaciones
```

### Paso 7: inferencia IA

La herramienta ejecuta YOLOv11n y guarda:

```text
codigo_imagen
modelo_version
class_id
class_name
confidence
bbox
tiempo_inferencia_ms
clase_principal_modelo
decision_modelo
```

### Paso 8: ground truth CODEX

La herramienta crea una verdad de referencia usando:

```text
auditoria_experta
consenso_expertos
etiqueta_yolo_auditada
doble_revision
resolucion_caso_frontera
```

No debe permitir que el Excel humano llene ground truth automáticamente.

### Paso 9: comparación

La comparación final debe hacerse solo con imágenes que tengan:

```text
ground_truth
evaluacion_humana
resultado_modelo
tiempo_humano
tiempo_modelo
```

### Paso 10: reporte

El sistema debe exportar:

```text
reporte_dataset
reporte_auditoria
reporte_modelo
reporte_humano
reporte_comparativo
matriz_confusion_humano
matriz_confusion_modelo
tabla_mcnemar
kappa
tiempos
limitaciones_codex_proxy_visual
```

## Regla de irrefutabilidad práctica

Para que la tesis sea defendible, cada conclusión debe poder rastrearse así:

```text
Conclusión
  -> métrica calculada
  -> tabla usada
  -> imagen evaluada
  -> ground truth
  -> evaluación humana
  -> inferencia IA
  -> etiqueta auditada
  -> criterio CODEX operacionalizado
```

Si una conclusión no puede rastrearse hasta una imagen y un criterio CODEX, el sistema no debe mostrarla como conclusión fuerte.
