# Módulo de etiquetado y auditoría

## Objetivo

Crear la primera interfaz de la herramienta: visor de imágenes con etiquetas YOLO, corrección de cajas, auditoría y exportación de dataset limpio.

Este módulo es prioritario porque la tesis depende de la calidad del dataset.

## Funciones principales

1. Cargar imágenes.
2. Cargar etiquetas YOLO `.txt`.
3. Visualizar cajas sobre imágenes.
4. Filtrar por clase, lote, sesión y estado.
5. Corregir clases y coordenadas.
6. Marcar observaciones.
7. Aprobar etiquetas auditadas.
8. Excluir imágenes no válidas.
9. Exportar dataset YOLO limpio.
10. Generar reporte de calidad de etiquetas.

## Estados de imagen

```text
pendiente
etiquetada
observada
corregida
auditada
excluida
test_bloqueado
```

## Dashboard del dataset

Debe mostrar:

| Indicador | Descripción |
|---|---|
| Total imágenes | Todas las imágenes cargadas |
| Total etiquetas | Todas las cajas YOLO |
| Imágenes sin etiqueta | Posibles normales o errores |
| Imágenes con etiqueta vacía | Archivo txt vacío |
| Imágenes observadas | Requieren corrección |
| Imágenes auditadas | Aprobadas para dataset |
| Distribución por clase | Balance de datos |
| Distribución train/val/test | Control de partición |
| Errores YOLO | Coordenadas inválidas o clase inválida |
| Duplicados | Imagen repetida entre splits |

## Visor de imagen

Layout sugerido:

```text
┌───────────────────────┬─────────────────────────────┬────────────────────────┐
│ Lista de imágenes     │ Imagen con cajas YOLO        │ Panel de etiquetas     │
│ - filtros             │ - zoom                       │ - clase                │
│ - búsqueda            │ - pan                        │ - coordenadas          │
│ - estados             │ - mostrar/ocultar clases     │ - auditoría            │
└───────────────────────┴─────────────────────────────┴────────────────────────┘
```

## Validaciones automáticas

El sistema debe revisar cada `.txt` YOLO.

Formato válido:

```text
class_id x_center y_center width height
```

Reglas:

```text
class_id entero entre 0 y 7.
x_center entre 0 y 1.
y_center entre 0 y 1.
width entre 0 y 1.
height entre 0 y 1.
width > 0.
height > 0.
La caja no debe salir del área de imagen.
El archivo .txt debe tener el mismo nombre base que la imagen.
La imagen no debe estar en más de un split.
```

## Errores automáticos

```text
ERR_CLASS_OUT_OF_RANGE
ERR_BOX_OUT_OF_RANGE
ERR_BOX_ZERO_SIZE
ERR_LABEL_WITHOUT_IMAGE
ERR_IMAGE_WITHOUT_LABEL
ERR_DUPLICATE_IMAGE_SPLIT
ERR_EMPTY_LABEL_FILE
ERR_NORMAL_WITH_OTHER_DEFECT
ERR_UNSUPPORTED_IMAGE_FORMAT
ERR_IMAGE_CORRUPTED
```

## Reglas para imagen normal

Hay dos opciones. Elegir una y documentarla.

### Opción A: normal como clase YOLO

La imagen normal tiene caja sobre el hongo completo con clase `normal`.

Ventaja:

- permite entrenar detección de hongo normal.

Desventaja:

- puede mezclar detección de objeto con clasificación de defecto.

### Opción B: normal sin caja

La imagen normal no tiene defectos, por tanto su `.txt` puede estar vacío.

Ventaja:

- más natural para detección de defectos.

Desventaja:

- la clasificación por imagen necesita lógica adicional.

### Recomendación

Para esta tesis, si se requiere comparar clase final `normal` contra humano, se puede guardar `normal` a nivel de imagen aunque el archivo YOLO esté vacío.

Separar:

```text
detecciones_yolo = cajas de defectos/objetos
etiqueta_imagen = normal/danado/carbonizado/etc.
```

## Auditoría

Cada cambio debe registrar:

```text
imagen_id
etiqueta_id
usuario
accion
valor_anterior
valor_nuevo
fecha_hora
motivo
```

Acciones:

```text
crear_etiqueta
editar_clase
editar_caja
eliminar_etiqueta
marcar_observada
aprobar_auditoria
excluir_imagen
bloquear_test
```

## Exportación YOLO

Estructura:

```text
dataset/
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
  data.yaml
  dataset_report.json
```

`data.yaml`:

```yaml
path: ./dataset
train: images/train
val: images/val
test: images/test

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

## Reporte de auditoría

Debe exportar:

```text
total_imagenes
total_etiquetas
imagenes_auditadas
imagenes_observadas
imagenes_excluidas
errores_por_tipo
etiquetas_por_clase
porcentaje_correccion
fecha_exportacion
responsable
```

## Criterios de aceptación

El módulo está completo si:

1. Carga imágenes y etiquetas.
2. Pinta cajas correctamente.
3. Detecta errores de formato YOLO.
4. Permite corregir y auditar.
5. Exporta dataset limpio.
6. Genera reporte de auditoría.
7. Bloquea el test final.
