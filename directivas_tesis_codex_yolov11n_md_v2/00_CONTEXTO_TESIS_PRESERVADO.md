# Contexto preservado de la tesis

## Propósito de este archivo

Este archivo mantiene el contexto académico de la tesis para que el agente programador no convierta el sistema en una aplicación genérica de visión artificial.

La herramienta debe existir para ejecutar y validar la tesis, no para reemplazarla ni cambiar su tema.

## Título de la tesis

Desarrollo y validación de un modelo de visión artificial basado en YOLOv11n para la clasificación de hongos comestibles desecados según el CODEX STAN 39-1981 en la Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec, Cusco.

## Pregunta central

¿En qué medida un modelo de visión artificial entrenado con YOLOv11n puede detectar y clasificar defectos visuales en hongos comestibles desecados conforme a las definiciones y tolerancias del CODEX STAN 39-1981, y cómo se compara su desempeño frente a la clasificación manual realizada por trabajadores entrenados de la Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec?

## Núcleo de validación

La tesis no busca solamente entrenar un modelo.

La tesis busca validar si el modelo YOLOv11n:

1. Detecta defectos visibles en hongos desecados.
2. Clasifica esos defectos usando clases operacionalizadas desde CODEX STAN 39-1981.
3. Puede compararse contra trabajadores humanos entrenados.
4. Reduce o mejora el tiempo de inspección.
5. Produce resultados medibles mediante métricas técnicas y estadísticas.

## Subpreguntas operativas

La herramienta debe responder con datos a estas preguntas:

1. ¿Qué tan consistente es el etiquetado?
2. ¿Qué desempeño tiene YOLOv11n por clase?
3. ¿En qué clases falla el humano?
4. ¿En qué clases falla el modelo?
5. ¿Existe diferencia estadística entre aciertos humanos y aciertos del modelo?
6. ¿Qué método demora menos por imagen o unidad evaluada?
7. ¿Qué límites tiene la visión artificial respecto a criterios CODEX que no son visuales?

## Objetivo general convertido a sistema

Desarrollar una herramienta que permita construir, auditar y validar un modelo YOLOv11n para detectar y clasificar defectos visibles en hongos comestibles desecados, comparando su desempeño con clasificación manual humana bajo criterios CODEX.

## Objetivos específicos convertidos a módulos

| Objetivo de tesis | Módulo de herramienta |
|---|---|
| Definir clases y criterios operativos de defectos visibles | Codebook CODEX-YOLO |
| Diseñar protocolo de captura | Gestión de lotes, sesiones e imágenes |
| Construir dataset YOLO con auditoría | Módulo de etiquetado y auditoría |
| Entrenar YOLOv11n | Bitácora de modelos e inferencia |
| Evaluar precision, recall, F1 y mAP | Módulo de métricas técnicas |
| Comparar humano vs modelo | Módulo de comparación pareada |
| Medir tiempos | Registro de tiempos humano e IA |
| Reportar evidencia para tesis | Exportación Excel/PDF y anexos |

## Hipótesis traducidas a validación computacional

### Hipótesis general

El modelo YOLOv11n entrenado con una guía de anotación validada alcanzará desempeño comparable o superior al método humano y reducirá el tiempo promedio de inspección.

### Cómo la herramienta prueba la hipótesis

La herramienta debe calcular:

```text
accuracy_modelo
accuracy_humano
precision_modelo
recall_modelo
F1_modelo
mAP@0.5
mAP@0.5:0.95
McNemar
kappa
tiempo_promedio_humano
tiempo_promedio_modelo
```

## Variables preservadas

| Variable | Cómo aparece en la herramienta |
|---|---|
| Método de clasificación | humano / YOLOv11n |
| Desempeño de clasificación | accuracy, precision, recall, F1, mAP |
| Concordancia | kappa |
| Diferencia de aciertos | McNemar |
| Eficiencia temporal | segundos por imagen |
| Calidad del rotulado | auditoría, V de Aiken si se registra juicio experto, kappa interanotador |

## Instrumentos preservados

La herramienta debe digitalizar estos instrumentos de la tesis:

1. Protocolo de captura.
2. Guía de anotación.
3. Ficha de evaluación humana.
4. Bitácora de entrenamiento.
5. Registro de tiempos.
6. Matriz de comparación humano vs modelo.

## Clases preservadas del codebook

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

## Límites que NO deben eliminarse

La herramienta no debe prometer que la imagen RGB mide directamente:

- humedad,
- residuo insoluble en ácido,
- masa m/m real,
- contaminación microbiológica,
- ensayos fisicoquímicos.

Cuando se use área, conteo o proporción visual, debe declararse como:

```text
proxy visual del criterio CODEX
```

## Regla metodológica final

La tesis se mantiene intacta si el sistema respeta esta estructura:

```text
Imagen estandarizada
  -> etiqueta/auditoría CODEX
  -> ground truth
  -> evaluación humana desde Excel
  -> inferencia YOLOv11n
  -> comparación pareada
  -> métricas técnicas + estadísticas + tiempos
  -> reporte defendible para tesis
```
