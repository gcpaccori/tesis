# Lógica de investigación defendible

## Problema metodológico que se debe evitar

El error más grave sería decir:

> “El trabajador puso X y el modelo puso Y, entonces el modelo está bien o mal”.

Eso no es válido si no existe una verdad de referencia. La tesis debe demostrar desempeño, no solo coincidencia.

## Diseño correcto

Cada imagen debe tener tres capas de información:

```text
1. Ground truth CODEX auditado
2. Evaluación humana
3. Resultado del modelo
```

Luego se calcula:

```text
acierto_humano = evaluación_humana == ground_truth
acierto_modelo = resultado_modelo == ground_truth
```

Con eso recién se puede hacer:

- accuracy humano,
- accuracy modelo,
- matriz de confusión humana,
- matriz de confusión del modelo,
- McNemar,
- kappa,
- diferencia de tiempos.

## Unidad experimental

La unidad experimental principal debe ser:

```text
imagen o unidad de muestra evaluada
```

Cada imagen debe tener:

- código único,
- lote,
- sesión de captura,
- split dataset,
- ground truth,
- evaluación humana,
- resultado IA,
- tiempo humano,
- tiempo IA.

## Comparación pareada

La comparación debe ser pareada porque humano e IA evalúan la misma imagen.

Ejemplo:

| Imagen | Ground truth | Humano | IA |
|---|---|---|---|
| IMG_001 | larvas | larvas | larvas |
| IMG_002 | normal | danado | normal |
| IMG_003 | carbonizado | normal | carbonizado |

Esto permite McNemar porque cada caso tiene dos resultados binarios:

```text
humano_correcto = sí/no
modelo_correcto = sí/no
```

## Tabla de McNemar

| | Modelo correcto | Modelo incorrecto |
|---|---:|---:|
| Humano correcto | a | b |
| Humano incorrecto | c | d |

La prueba se basa en los discordantes:

```text
b = humano correcto, modelo incorrecto
c = humano incorrecto, modelo correcto
```

Interpretación:

- Si `c > b`, el modelo acierta más en los casos donde difiere.
- Si `b > c`, el humano acierta más en los casos donde difiere.
- Si `p < 0.05`, la diferencia es estadísticamente significativa.

## Capa 1: Detección

Evalúa cajas y clases.

Métricas:

- precision,
- recall,
- F1,
- mAP@0.5,
- mAP@0.5:0.95,
- falsos positivos,
- falsos negativos,
- matriz de confusión por clase.

## Capa 2: Clasificación final por imagen

Convierte varias detecciones a una etiqueta principal por imagen.

Ejemplo:

```text
Si detecta larvas y carbonizado:
    clase principal = clase de mayor prioridad metodológica
    clases secundarias = todas las detectadas
```

La tesis puede reportar ambas:

- análisis multi-etiqueta por detección,
- análisis de etiqueta principal por imagen.

## Capa 3: Decisión de conformidad

Convierte la clasificación en decisión:

```text
apto
no_apto
observado
```

Esta capa debe usar reglas CODEX operacionalizadas.

Ejemplo:

```text
Si hay carbonizado visible por encima del umbral proxy:
    no_apto u observado según regla definida.
```

## Jerarquía de evidencia

Para defender la tesis, el sistema debe conservar:

1. Imagen original.
2. Etiqueta YOLO original.
3. Correcciones de etiqueta.
4. Usuario que corrigió.
5. Fecha de corrección.
6. Ground truth final.
7. Evaluación humana.
8. Predicción IA.
9. Modelo usado.
10. Umbral de confianza usado.
11. Tiempo de evaluación.
12. Métricas generadas.

## Reglas anti-sesgo

### Evitar fuga de datos

No mezclar imágenes casi iguales entre train y test.

Regla:

```text
Split por lote o sesión de captura.
```

No basta con hacer split aleatorio si existen imágenes muy parecidas.

### Congelar test

El test debe quedar bloqueado antes de evaluación final.

```text
test_locked = true
```

Después de bloquear test:

- no se corrigen etiquetas salvo auditoría formal,
- no se entrena con esas imágenes,
- no se ajusta el modelo mirando errores del test final.

### Evaluación humana ciega

El trabajador no debe ver:

- predicción IA,
- etiqueta YOLO,
- ground truth,
- evaluación de otro trabajador.

### Evaluación IA reproducible

Cada inferencia debe registrar:

- versión del modelo,
- archivo `best.pt`,
- hash del modelo,
- umbral de confianza,
- IoU threshold,
- tamaño de imagen,
- librería Ultralytics,
- fecha de inferencia.

## Qué hace irrefutable la tesis

No existe tesis literalmente irrefutable, pero sí una tesis metodológicamente fuerte si cumple:

1. Dataset auditado.
2. Test congelado.
3. Ground truth independiente.
4. Comparación pareada.
5. Métricas por clase.
6. Tiempos medidos.
7. Bitácora reproducible.
8. Declaración de limitaciones CODEX.
9. Control de sesgo por lote/sesión.
10. Reporte de errores, no solo resultados bonitos.

## Conclusión metodológica

La herramienta debe demostrar:

```text
Bajo un protocolo controlado y con una verdad de referencia CODEX operacionalizada, YOLOv11n logra un desempeño medible y comparable frente a trabajadores humanos, con diferencias cuantificables en acierto y tiempo de inspección.
```
