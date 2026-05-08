# Módulo de ground truth CODEX

## Objetivo

Construir y administrar la verdad de referencia contra la cual se comparan humano e IA.

## Por qué es necesario

Sin ground truth, la investigación solo mediría coincidencia entre humano e IA. Eso no prueba desempeño.

Con ground truth, se puede medir:

```text
humano correcto / incorrecto
modelo correcto / incorrecto
```

## Fuentes válidas de ground truth

El sistema debe permitir registrar una fuente:

```text
auditoria_experta
consenso_expertos
etiqueta_yolo_auditada
doble_revision
resolucion_caso_frontera
```

## Fuentes no válidas como verdad automática

```text
prediccion_ia
excel_trabajador_sin_auditar
voto_mayoritario_sin_revision
```

Pueden usarse como apoyo, pero no como verdad directa.

## Campos de ground truth

```text
codigo_imagen
clase_real
decision_real
defectos_reales_multietiqueta
severidad_larvas
cantidad_pies_desprendidos
proxy_area_defectuosa
proxy_conteo_defectos
fuente_ground_truth
auditor
fecha_auditoria
nivel_confianza
observacion
```

## Catálogo clase_real

```text
normal
danado
carbonizado
aplastado
larvas
impureza_vegetal
impureza_mineral
pie_desprendido
mixto
no_evaluable
```

## Cuándo usar `mixto`

Usar `mixto` cuando una imagen tenga varios defectos relevantes y no sea justo reducirla a una sola clase.

Pero para McNemar se necesita una decisión binaria o clase principal. Por eso guardar:

```text
defectos_reales_multietiqueta = ["larvas", "carbonizado"]
clase_principal_real = "larvas"
decision_real = "no_apto"
```

## Decisión CODEX proxy

Valores:

```text
apto
no_apto
observado
no_evaluable
```

## Reglas de decisión sugeridas

Estas reglas deben congelarse antes de evaluación final.

```text
Si clase_real = normal:
    decision_real = apto

Si hay impureza_mineral visible:
    decision_real = observado o no_apto según severidad visual

Si hay impureza_vegetal visible:
    decision_real = observado o no_apto según proxy definido

Si hay larvas severo:
    decision_real = no_apto

Si hay larvas leve:
    decision_real = observado

Si hay carbonizado:
    decision_real = observado o no_apto según proporción visual

Si hay danado fuerte:
    decision_real = observado o no_apto según proporción visual

Si hay aplastado:
    decision_real = observado o no_apto según proxy de tamaño/fragmentación

Si hay pie_desprendido:
    decision_real = observado o no_apto según regla de relación pies:sombreretes
```

## Resolución de discrepancias

Si dos expertos no coinciden:

1. Marcar imagen como `discrepante`.
2. Registrar ambas evaluaciones.
3. Hacer sesión de consenso.
4. Guardar decisión final y motivo.
5. No borrar las evaluaciones anteriores.

## Casos no evaluables

Marcar `no_evaluable` cuando:

```text
imagen borrosa
imagen con sombra extrema
pieza tapada
objeto fuera de foco
fondo impide distinguir impureza
archivo corrupto
```

Estas imágenes no deben entrar en test final.

## Pantalla de ground truth

Debe mostrar:

```text
Imagen
Etiquetas YOLO auditadas
Evaluaciones humanas ocultables
Predicción IA ocultable
Formulario CODEX
Historial de auditoría
Botón aprobar ground truth
```

Para evitar sesgo, la pantalla debe permitir modo ciego:

```text
modo_ground_truth_ciego = no mostrar predicción IA ni evaluación humana
```

## Criterios de aceptación

El módulo está completo si:

1. Registra ground truth por imagen.
2. Distingue ground truth de evaluación humana.
3. Permite consenso experto.
4. Permite casos mixtos.
5. Permite casos no evaluables.
6. Guarda trazabilidad.
7. Congela ground truth final.
8. Exporta tabla final para comparación.
