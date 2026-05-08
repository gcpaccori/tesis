# Métricas y estadística de validación

## Objetivo

Calcular las métricas necesarias para validar la tesis: desempeño técnico, comparación humano vs modelo, concordancia y eficiencia temporal.

## Datos mínimos requeridos

Por imagen:

```text
codigo_imagen
ground_truth_clase
ground_truth_decision
humano_clase
humano_decision
modelo_clase
modelo_decision
tiempo_humano_segundos
tiempo_modelo_segundos
```

## Métricas de detección del modelo

Estas usan cajas YOLO:

```text
precision por clase
recall por clase
F1 por clase
mAP@0.5
mAP@0.5:0.95
matriz de confusión por clase
falsos positivos
falsos negativos
```

## Métricas de clasificación por imagen

Estas usan clase principal por imagen:

```text
accuracy_modelo
accuracy_humano
precision_modelo_por_clase
precision_humano_por_clase
recall_modelo_por_clase
recall_humano_por_clase
F1_modelo_por_clase
F1_humano_por_clase
```

## Fórmulas básicas

```text
accuracy = aciertos / total

precision = TP / (TP + FP)

recall = TP / (TP + FN)

F1 = 2 * precision * recall / (precision + recall)
```

## Matriz de confusión

Generar dos matrices:

```text
ground_truth vs humano
ground_truth vs modelo
```

Clases:

```text
normal
danado
carbonizado
aplastado
larvas
impureza_vegetal
impureza_mineral
pie_desprendido
```

## McNemar

Usar para comparar proporción de aciertos entre humano e IA sobre las mismas imágenes.

Crear variables:

```text
humano_correcto = humano_clase == ground_truth_clase
modelo_correcto = modelo_clase == ground_truth_clase
```

Tabla:

| | Modelo correcto | Modelo incorrecto |
|---|---:|---:|
| Humano correcto | a | b |
| Humano incorrecto | c | d |

Interpretación:

```text
b = casos donde humano acierta y modelo falla
c = casos donde humano falla y modelo acierta
```

Si `p < 0.05`, hay diferencia estadísticamente significativa.

## Kappa

Usar kappa para medir acuerdo.

Tipos:

```text
Cohen kappa: 2 evaluadores.
Fleiss kappa: más de 2 evaluadores.
```

Aplicaciones:

1. Acuerdo entre trabajadores.
2. Acuerdo humano vs ground truth.
3. Acuerdo modelo vs ground truth.
4. Acuerdo humano vs modelo, solo como indicador complementario.

No reemplaza accuracy contra ground truth.

## Comparación de tiempos

Por imagen:

```text
tiempo_humano_segundos
tiempo_modelo_segundos
```

Métricas:

```text
promedio
mediana
desviación estándar
mínimo
máximo
percentil 95
```

Contraste:

```text
Si distribución normal:
    t pareada

Si no normal:
    Wilcoxon signed-rank
```

Resultado:

```text
diferencia_promedio = tiempo_humano_promedio - tiempo_modelo_promedio
factor_velocidad = tiempo_humano_promedio / tiempo_modelo_promedio
```

## Reporte mínimo de resultados

El sistema debe exportar:

```text
Tabla 1: resumen de dataset
Tabla 2: etiquetas por clase
Tabla 3: métricas YOLO por clase
Tabla 4: matriz de confusión modelo
Tabla 5: matriz de confusión humano
Tabla 6: comparación de aciertos
Tabla 7: McNemar
Tabla 8: kappa
Tabla 9: tiempos
Tabla 10: errores frecuentes por clase
```

## Errores por clase

El sistema debe identificar:

```text
clases con bajo recall
clases con bajo precision
clases confundidas entre sí
falsos negativos críticos
falsos positivos críticos
casos frontera
```

## Criterio de conclusión

La tesis puede afirmar superioridad/comparabilidad solo si se reporta:

```text
desempeño por clase
desempeño global
significancia o no significancia de McNemar
diferencia de tiempos
limitaciones de proxy visual
```

## Exportación

Formatos:

```text
metrics_summary.json
metrics_summary.xlsx
confusion_matrix_model.csv
confusion_matrix_human.csv
mcnemar_table.csv
kappa_report.csv
time_comparison.csv
tesis_report.md
```

## Criterios de aceptación

El módulo está completo si:

1. Calcula métricas del modelo.
2. Calcula métricas humanas.
3. Calcula McNemar.
4. Calcula kappa.
5. Compara tiempos.
6. Genera matrices de confusión.
7. Exporta reportes.
8. No oculta clases con bajo rendimiento.
