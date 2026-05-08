# QA y criterios de aceptación

## Objetivo

Definir pruebas mínimas para comprobar que la herramienta sirve para validar la tesis sin romper la lógica metodológica.

## QA metodológico

### Test 1: Excel humano no es ground truth

Dado:

```text
Se importa Excel de trabajadores.
```

Esperado:

```text
El sistema guarda los datos en evaluaciones_humanas.
No llena automáticamente ground_truth.
No calcula métricas finales si falta ground_truth.
```

### Test 2: Ground truth obligatorio

Dado:

```text
Hay inferencia IA y evaluación humana, pero no ground truth.
```

Esperado:

```text
El sistema muestra comparación de coincidencia, pero bloquea conclusiones de desempeño.
```

### Test 3: Evaluación pareada

Dado:

```text
Humano evaluó 100 imágenes.
IA procesó 90 imágenes.
Ground truth tiene 100 imágenes.
```

Esperado:

```text
El sistema calcula métricas finales solo con intersección válida o advierte faltantes.
```

### Test 4: Test bloqueado

Dado:

```text
El usuario intenta modificar una etiqueta del test bloqueado.
```

Esperado:

```text
El sistema bloquea la edición o exige auditoría formal.
```

### Test 5: Sin fuga de datos

Dado:

```text
Una imagen aparece en train y test.
```

Esperado:

```text
El sistema marca ERR_DUPLICATE_IMAGE_SPLIT.
```

## QA de etiquetas YOLO

### Casos inválidos

```text
8 0.5 0.5 0.2 0.2       -> clase fuera de rango
1 1.2 0.5 0.2 0.2       -> x fuera de rango
1 0.5 0.5 0 0.2         -> ancho cero
1 0.5 0.5 -0.1 0.2      -> ancho negativo
abc 0.5 0.5 0.2 0.2     -> clase no numérica
```

Esperado:

```text
El sistema detecta y lista errores.
```

## QA de importación Excel

### Columnas faltantes

Si falta:

```text
codigo_imagen
evaluador
etiqueta_final_humana
tiempo_segundos
```

Esperado:

```text
Importación rechazada o marcada como incompleta.
```

### Valores inválidos

```text
etiqueta_final_humana = quemado
decision_humana = tal vez
tiempo_segundos = texto
```

Esperado:

```text
El sistema muestra errores por fila y columna.
```

## QA de inferencia IA

Dado:

```text
Mismo modelo + mismos parámetros + mismas imágenes.
```

Esperado:

```text
La corrida debe ser reproducible o al menos guardar la configuración exacta.
```

Debe guardar:

```text
modelo_version
hash
confidence
iou
imgsz
device
fecha
run_id
```

## QA de métricas

### McNemar

Crear datos artificiales:

| Imagen | GT | Humano | IA |
|---|---|---|---|
| 1 | normal | normal | normal |
| 2 | normal | normal | danado |
| 3 | danado | normal | danado |
| 4 | larvas | normal | larvas |

Esperado:

```text
a = 1
b = 1
c = 2
d = 0
```

### Accuracy

Con la misma tabla:

```text
accuracy_humano = 2/4 = 0.5
accuracy_modelo = 3/4 = 0.75
```

## QA de tiempos

Dado:

```text
tiempo humano: 10, 12, 8
tiempo IA: 0.04, 0.05, 0.03
```

Esperado:

```text
promedio_humano = 10
promedio_ia = 0.04
factor_velocidad = 250
```

## QA de reportes

El reporte final debe contener:

```text
número de imágenes
distribución por clase
métricas modelo
métricas humano
McNemar
kappa
tiempos
limitaciones
configuración del modelo
configuración del dataset
```

## Criterio de aceptación final

La herramienta se considera lista para tesis si:

1. No confunde humano con ground truth.
2. Permite auditoría de etiquetas.
3. Congela test.
4. Versiona modelo.
5. Compara sobre las mismas imágenes.
6. Calcula métricas correctamente.
7. Exporta evidencia reproducible.
8. Declara limitaciones CODEX.
