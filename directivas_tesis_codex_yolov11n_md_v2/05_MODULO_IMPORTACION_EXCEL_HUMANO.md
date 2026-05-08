# Módulo de importación de Excel humano

## Objetivo

Importar la evaluación manual realizada por trabajadores entrenados para compararla contra ground truth CODEX y contra el modelo YOLOv11n.

## Principio clave

El Excel humano NO es ground truth.

El Excel humano es una fuente de datos experimental:

```text
metodo = humano
evaluador = trabajador
resultado = etiqueta/decisión manual
```

## Formato mínimo del Excel

Hoja sugerida:

```text
evaluacion_humana
```

Columnas:

| Columna | Obligatoria | Tipo |
|---|---|---|
| codigo_imagen | Sí | texto |
| codigo_lote | Sí | texto |
| fecha_evaluacion | Sí | fecha |
| evaluador | Sí | texto/código |
| tipo_presentacion | Sí | catálogo |
| defecto_danado | Sí | SI/NO |
| defecto_carbonizado | Sí | SI/NO |
| defecto_aplastado | Sí | SI/NO |
| defecto_larvas | Sí | NO/LEVE/SEVERO |
| impureza_vegetal | Sí | SI/NO |
| impureza_mineral | Sí | SI/NO |
| pie_desprendido_cantidad | Sí | entero |
| etiqueta_final_humana | Sí | catálogo de clases |
| decision_humana | Sí | apto/no_apto/observado |
| tiempo_inicio | No | datetime |
| tiempo_fin | No | datetime |
| tiempo_segundos | Sí | numérico |
| observaciones | No | texto |

## Catálogos

### tipo_presentacion

```text
entero
sombrerete_sin_pie
lonja
otro
```

### etiqueta_final_humana

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

### decision_humana

```text
apto
no_apto
observado
```

## Validaciones de importación

El sistema debe rechazar o marcar errores cuando:

```text
codigo_imagen está vacío.
codigo_imagen no existe en imágenes.
evaluador está vacío.
etiqueta_final_humana no pertenece al catálogo.
decision_humana no pertenece al catálogo.
tiempo_segundos no es numérico.
tiempo_segundos <= 0.
Existe duplicado de codigo_imagen + evaluador.
La misma imagen fue evaluada después de ver resultados IA.
```

## Normalización

Convertir automáticamente:

```text
Sí, SI, si, x, 1 -> SI
No, NO, no, 0, vacío -> NO
Dañado, dañado, danado -> danado
Impureza vegetal -> impureza_vegetal
Pie desprendido -> pie_desprendido
```

## Manejo de varios evaluadores

Si hay varios trabajadores evaluando la misma imagen:

```text
codigo_imagen
evaluador_1
evaluador_2
evaluador_3
```

El sistema debe permitir:

1. Calcular kappa entre evaluadores.
2. Mostrar desacuerdos.
3. Calcular voto mayoritario humano.
4. Comparar cada evaluador contra ground truth.
5. Comparar consenso humano contra ground truth.

## Consenso humano

El consenso humano se puede calcular por:

```text
mayoría simple
decisión de experto
revisión posterior
```

Pero debe guardarse separado:

```text
evaluacion_individual != consenso_humano != ground_truth
```

## Tabla de errores de importación

Cada carga de Excel debe generar:

| Fila | Columna | Error | Valor recibido | Acción |
|---:|---|---|---|---|
| 15 | etiqueta_final_humana | valor inválido | quemado | corregir a carbonizado |
| 22 | tiempo_segundos | vacío | | completar |
| 30 | codigo_imagen | no existe | IMG_999 | revisar archivo |

## Salidas del módulo

```json
{
  "archivo": "evaluacion_humana_lote_001.xlsx",
  "filas_leidas": 500,
  "filas_validas": 492,
  "filas_con_error": 8,
  "evaluadores": ["E01", "E02", "E03"],
  "imagenes_unicas": 500,
  "fecha_importacion": "2026-05-07"
}
```

## Criterios de aceptación

El módulo está correcto si:

1. Importa Excel.
2. Valida columnas.
3. Detecta errores.
4. Normaliza etiquetas.
5. Relaciona cada fila con imagen existente.
6. Calcula tiempo humano.
7. Permite varios evaluadores.
8. No confunde Excel humano con ground truth.
