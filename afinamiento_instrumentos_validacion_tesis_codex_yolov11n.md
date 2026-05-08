# Afinamiento de instrumentos y pantallas de validaciÃ³n para la tesis YOLOv11n + CODEX

**Proyecto:** Desarrollo y validaciÃ³n de un modelo de visiÃ³n artificial basado en YOLOv11n para la clasificaciÃ³n de hongos comestibles desecados segÃºn el CODEX STAN 39-1981 en la Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec, Cusco y ApurÃ­mac.

**PropÃ³sito de este documento:** convertir los instrumentos de la tesis en pantallas, resultados, validaciones y capturas listas para sustentar. La app ya puede funcionar tÃ©cnicamente, pero ahora debe mostrar de forma explÃ­cita **quÃ© parte de la tesis estÃ¡ siendo validada**, **con quÃ© instrumento**, **contra quÃ© referencia**, **con quÃ© resultado** y **quÃ© evidencia visual se exporta**.

---

## 0. CorrecciÃ³n central de la lÃ³gica de tesis

La herramienta no debe presentar la validaciÃ³n como una pelea simple:

```text
Humano vs IA
```

La forma metodolÃ³gicamente correcta es:

```text
CODEX STAN 39-1981
        â†“
OperacionalizaciÃ³n visual de defectos
        â†“
GuÃ­a de anotaciÃ³n / codebook
        â†“
Ground truth auditado
        â†“
ComparaciÃ³n pareada:
    - Humano vs ground truth
    - IA vs ground truth
    - Humano vs IA como anÃ¡lisis adicional
        â†“
MÃ©tricas, hipÃ³tesis y discusiÃ³n
```

**Regla irrenunciable:** el Excel de trabajadores no es la verdad absoluta. El Excel es el **instrumento de evaluaciÃ³n humana**. La verdad de referencia debe venir de etiquetas auditadas, consenso experto o revisiÃ³n del investigador basada en la guÃ­a CODEX operacionalizada.

---

## 1. QuÃ© valida realmente la tesis

La tesis valida principalmente cuatro dimensiones:

| DimensiÃ³n | QuÃ© se valida | CÃ³mo se evidencia |
|---|---|---|
| Validez del criterio CODEX convertido a imagen | Que los defectos del CODEX se tradujeron a clases visuales observables | Codebook, guÃ­a de anotaciÃ³n, V de Aiken, ejemplos visuales |
| Confiabilidad del etiquetado | Que las etiquetas usadas como referencia no son arbitrarias | AuditorÃ­a de etiquetas, kappa/anÃ¡lisis de acuerdo, tasa de correcciÃ³n |
| DesempeÃ±o del modelo YOLOv11n | Que el modelo detecta/clasifica defectos visibles | Precision, recall, F1, mAP, matriz de confusiÃ³n, errores por clase |
| ComparaciÃ³n con trabajadores humanos | Que el modelo se compara con clasificaciÃ³n manual en las mismas imÃ¡genes | Excel humano, tabla pareada, McNemar, kappa, tiempos por imagen |

---

## 2. QuÃ© NO valida la tesis

Esto debe estar claro en la app y en el informe para que no te cuestionen.

| Elemento | Â¿Se valida? | ExplicaciÃ³n |
|---|---:|---|
| Contenido de agua del hongo | No | El CODEX habla de contenido mÃ¡ximo de agua, pero eso requiere mÃ©todo fÃ­sico/quÃ­mico, no RGB. |
| Impureza mineral analÃ­tica por residuo insoluble en Ã¡cido | No completamente | Solo puede registrarse si es visible en imagen. No reemplaza ensayo de laboratorio. |
| Porcentaje m/m exacto | No exactamente | La imagen produce proxy visual por conteo/Ã¡rea, no masa real. |
| Calidad microbiolÃ³gica | No | Fuera del alcance visual. |
| Todo el CODEX completo | No | Solo defectos e impurezas visibles operacionalizadas para imagen. |
| Productividad industrial completa | Parcial | Se mide tiempo por imagen/lote en condiciones controladas, no toda la cadena productiva. |

**Texto recomendado para la app:**

```text
Alcance del sistema: validaciÃ³n visual de defectos observables en imÃ¡genes. El sistema no reemplaza anÃ¡lisis fÃ­sico-quÃ­micos, microbiolÃ³gicos ni determinaciÃ³n de masa m/m. Las tolerancias CODEX se usan como criterio de clasificaciÃ³n visual operacionalizada y, cuando corresponda, como proxy por conteo o Ã¡rea relativa.
```

---

## 3. Mapa de instrumentos de la tesis

La tesis menciona o exige estos instrumentos/procesos:

| CÃ³digo | Instrumento | Existe en la tesis | Debe existir en la app | Finalidad |
|---|---|---:|---:|---|
| I1 | Protocolo de captura | SÃ­ | SÃ­ | Controlar calidad de imÃ¡genes |
| I2 | GuÃ­a de anotaciÃ³n CODEX-YOLO | SÃ­ | SÃ­ | Traducir CODEX a etiquetas visuales |
| I3 | Ficha de evaluaciÃ³n humana | SÃ­ | SÃ­ | Registrar clasificaciÃ³n manual por imagen |
| I4 | BitÃ¡cora de entrenamiento | SÃ­ | SÃ­ | Dar trazabilidad al entrenamiento YOLOv11n |
| I5 | Registro de tiempos | SÃ­ | SÃ­ | Comparar eficiencia humano vs modelo |
| I6 | Planilla de validez de contenido | ImplÃ­cita/descrita | SÃ­ | Validar guÃ­a/ficha con expertos mediante V de Aiken |
| I7 | Planilla de concordancia | SÃ­ | SÃ­ | Medir kappa humano o interanotador |
| I8 | Ground truth auditado | MetodolÃ³gicamente necesario | Obligatorio | Tener referencia para comparar humano e IA |
| I9 | Reporte de inferencia IA | Necesario por evaluaciÃ³n tÃ©cnica | Obligatorio | Guardar salida del modelo |
| I10 | Reporte estadÃ­stico final | SÃ­ | Obligatorio | Probar hipÃ³tesis y sustentar resultados |

---

# 4. Instrumento I1: Protocolo de captura

## Finalidad

Garantizar que las imÃ¡genes usadas para entrenamiento, prueba y comparaciÃ³n tengan condiciones controladas: iluminaciÃ³n, fondo, distancia, escala y ausencia de sombras fuertes.

## QuÃ© valida

Valida la **calidad de adquisiciÃ³n de datos**. Sirve para defender que el modelo y los trabajadores evaluaron imÃ¡genes bajo condiciones comparables.

## QuÃ© NO valida

No valida que el modelo sea bueno. No valida que el trabajador clasifique bien. Solo valida que la entrada visual no estÃ© contaminada por mala captura.

## Campos mÃ­nimos

| Campo | Tipo | Ejemplo |
|---|---|---|
| codigo_sesion | texto | SES_2026_001 |
| fecha | fecha | 2026-05-07 |
| responsable | texto | GC001 |
| origen | texto | Cusco / ApurÃ­mac |
| lote | texto | LOTE_001 |
| tipo_producto | texto | entero / lonja / sombrerete |
| fondo_uniforme | sÃ­/no | SÃ­ |
| iluminacion_difusa | sÃ­/no | SÃ­ |
| distancia_fija | sÃ­/no | SÃ­ |
| escala_visible | sÃ­/no | SÃ­ |
| sombras_controladas | sÃ­/no | SÃ­ |
| imagenes_validas | nÃºmero | 450 |
| imagenes_excluidas | nÃºmero | 12 |
| motivo_exclusion | texto | borrosa, sombra, fuera de foco |

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I1: PROTOCOLO DE CAPTURA                        â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ SesiÃ³n: SES_2026_001      Lote: LOTE_001                    â”‚
â”‚ Fecha: 2026-05-07        Origen: Cusco                      â”‚
â”‚ Responsable: GC001       Tipo: Hongo desecado / lonja       â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Checklist de captura                                         â”‚
â”‚ [âœ“] Fondo uniforme                                           â”‚
â”‚ [âœ“] IluminaciÃ³n difusa                                       â”‚
â”‚ [âœ“] Distancia fija                                           â”‚
â”‚ [âœ“] Escala visible                                           â”‚
â”‚ [âœ“] Sombras controladas                                      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ ImÃ¡genes capturadas: 462                                     â”‚
â”‚ ImÃ¡genes vÃ¡lidas: 450                                        â”‚
â”‚ ImÃ¡genes excluidas: 12                                       â”‚
â”‚ Motivos principales: desenfoque, sombra fuerte               â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Estado del instrumento: VALIDADO PARA DATASET                â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. Registro del protocolo de captura aplicado al lote de imÃ¡genes de evaluaciÃ³n.
```

Debe mostrar el checklist y el conteo de imÃ¡genes vÃ¡lidas/excluidas.

---

# 5. Instrumento I2: GuÃ­a de anotaciÃ³n CODEX-YOLO

## Finalidad

Convertir las definiciones del CODEX STAN 39-1981 en clases visuales que YOLO pueda aprender y detectar.

## QuÃ© valida

Valida la **operacionalizaciÃ³n del estÃ¡ndar CODEX**. Es decir, demuestra cÃ³mo pasas de una norma escrita a etiquetas visuales medibles.

## QuÃ© NO valida

No valida por sÃ­ sola el desempeÃ±o del modelo. Tampoco demuestra que las etiquetas estÃ©n bien aplicadas en todas las imÃ¡genes. Para eso se necesita auditorÃ­a y ground truth.

## Clases internas

| ID | Clase | Origen CODEX / criterio visual | Unidad de anotaciÃ³n |
|---:|---|---|---|
| 0 | normal | Sin defecto visible relevante | Hongo completo |
| 1 | danado | PÃ©rdida de parte del sombrerete o superficie | Pieza daÃ±ada |
| 2 | carbonizado | Vestigios de carbonizaciÃ³n superficial | Zona o pieza |
| 3 | aplastado | Fragmento/deformaciÃ³n compatible con aplastamiento | Fragmento o pieza |
| 4 | larvas | Agujeros compatibles con larvas | Zona o pieza |
| 5 | impureza_vegetal | Hojas, agujas, tallos u otra materia vegetal | Impureza |
| 6 | impureza_mineral | Tierra, arena o piedra visible | Impureza visible |
| 7 | pie_desprendido | Pie separado del sombrerete | Pie suelto |

## Reglas visuales obligatorias

```text
- Toda clase debe tener definiciÃ³n operacional.
- Toda clase debe tener criterio de inclusiÃ³n.
- Toda clase debe tener criterio de exclusiÃ³n.
- Toda clase debe tener ejemplo correcto.
- Toda clase debe tener ejemplo frontera.
- Toda clase debe tener ejemplo incorrecto.
- Toda caja YOLO debe poder justificarse con una regla CODEX operacionalizada.
```

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I2: GUÃA DE ANOTACIÃ“N CODEX-YOLO                â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Clase seleccionada: 4 - larvas                              â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ DefiniciÃ³n CODEX operacionalizada:                          â”‚
â”‚ Agujeros visibles compatibles con daÃ±o por larvas.           â”‚
â”‚                                                             â”‚
â”‚ Incluir cuando:                                              â”‚
â”‚ - Existan orificios visibles en la pieza.                    â”‚
â”‚ - El patrÃ³n sea compatible con daÃ±o biolÃ³gico.               â”‚
â”‚                                                             â”‚
â”‚ Excluir cuando:                                              â”‚
â”‚ - Sea una rotura mecÃ¡nica clara.                             â”‚
â”‚ - Sea sombra o textura natural.                              â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ [Imagen ejemplo correcto] [Imagen caso frontera] [Error]     â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Estado: APROBADA POR GUÃA / REQUIERE REVISIÃ“N EXPERTA        â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. Interfaz de guÃ­a de anotaciÃ³n para la clase larvas, basada en criterios visuales del CODEX STAN 39-1981.
```

---

# 6. Instrumento I3: Ficha de evaluaciÃ³n humana

## Finalidad

Registrar cÃ³mo clasifican los trabajadores cada imagen, cuÃ¡nto demoran y quÃ© decisiÃ³n final emiten.

## QuÃ© valida

Valida el **mÃ©todo manual** como objeto de comparaciÃ³n. Permite medir desempeÃ±o humano contra ground truth.

## QuÃ© NO valida

No valida el ground truth. No valida la IA. No debe tratarse como verdad absoluta.

## Columnas mÃ­nimas del Excel humano

| Columna | Obligatoria | Ejemplo |
|---|---:|---|
| codigo_imagen | SÃ­ | IMG_0001.jpg |
| evaluador | SÃ­ | TRAB_01 |
| lote | SÃ­ | LOTE_001 |
| tipo_presentacion | SÃ­ | lonja |
| defecto_danado | SÃ­ | SI/NO |
| defecto_carbonizado | SÃ­ | SI/NO |
| defecto_aplastado | SÃ­ | SI/NO |
| defecto_larvas | SÃ­ | NO/LEVE/SEVERO |
| impureza_vegetal | SÃ­ | SI/NO |
| impureza_mineral | SÃ­ | SI/NO |
| pie_desprendido_cantidad | SÃ­ | 0/1/2 |
| etiqueta_final_humana | SÃ­ | larvas |
| decision_humana | SÃ­ | apto/no_apto/observado |
| tiempo_segundos | SÃ­ | 12.4 |
| observaciones | No | duda por sombra |

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I3: EVALUACIÃ“N HUMANA IMPORTADA                 â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Archivo: evaluacion_trabajadores.xlsx                       â”‚
â”‚ Filas leÃ­das: 500                                            â”‚
â”‚ Filas vÃ¡lidas: 492                                           â”‚
â”‚ Filas con observaciÃ³n: 8                                     â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ ValidaciÃ³n de estructura                                     â”‚
â”‚ [âœ“] codigo_imagen existe                                     â”‚
â”‚ [âœ“] evaluador existe                                         â”‚
â”‚ [âœ“] etiqueta_final_humana vÃ¡lida                             â”‚
â”‚ [âœ“] tiempo_segundos numÃ©rico                                 â”‚
â”‚ [!] 8 imÃ¡genes tienen etiqueta fuera del codebook             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Resumen humano                                               â”‚
â”‚ Evaluadores: 3                                               â”‚
â”‚ Tiempo promedio: 11.8 s / imagen                             â”‚
â”‚ Clase mÃ¡s marcada: danado                                    â”‚
â”‚ Casos observados: 21                                         â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. ValidaciÃ³n de estructura de la ficha de evaluaciÃ³n humana importada desde Excel.
```

---

# 7. Instrumento I4: BitÃ¡cora de entrenamiento YOLOv11n

## Finalidad

Documentar el entrenamiento del modelo y permitir reproducibilidad.

## QuÃ© valida

Valida la **trazabilidad del entrenamiento**. Permite demostrar con quÃ© configuraciÃ³n se obtuvo el modelo evaluado.

## QuÃ© NO valida

No valida por sÃ­ sola que el modelo sea correcto. La calidad del modelo se valida con test y mÃ©tricas.

## Campos obligatorios

| Campo | Ejemplo |
|---|---|
| modelo_base | YOLOv11n |
| dataset_version | dataset_codex_v1 |
| train_images | 3150 |
| val_images | 900 |
| test_images | 450 |
| epochs | 100 |
| imgsz | 640 |
| batch | 16 |
| optimizer | auto/SGD/AdamW |
| patience | 20 |
| augmentation | activado/controlado |
| best_model | best.pt |
| fecha_entrenamiento | 2026-05-07 |
| equipo | CPU/GPU/Colab/servidor |
| ultralytics_version | versiÃ³n usada |

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I4: BITÃCORA DE ENTRENAMIENTO YOLOv11n          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Modelo base: YOLOv11n                                       â”‚
â”‚ VersiÃ³n dataset: dataset_codex_v1                           â”‚
â”‚ Pesos finales: best.pt                                      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ ParticiÃ³n del dataset                                       â”‚
â”‚ Train: 70%     Val: 20%     Test: 10%                       â”‚
â”‚ Control: particiÃ³n por lote/sesiÃ³n                          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ HiperparÃ¡metros                                             â”‚
â”‚ epochs: 100 | imgsz: 640 | batch: 16 | patience: 20          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ MÃ©trica de selecciÃ³n: mejor desempeÃ±o en validaciÃ³n          â”‚
â”‚ Estado: ENTRENAMIENTO DOCUMENTADO                           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. BitÃ¡cora de entrenamiento del modelo YOLOv11n utilizado en la evaluaciÃ³n final.
```

---

# 8. Instrumento I5: Registro de tiempos

## Finalidad

Comparar eficiencia entre clasificaciÃ³n humana e inferencia del modelo.

## QuÃ© valida

Valida la dimensiÃ³n de **eficiencia temporal**.

## QuÃ© NO valida

No valida exactitud. Un mÃ©todo puede ser mÃ¡s rÃ¡pido pero menos correcto.

## Regla metodolÃ³gica

Los tiempos deben compararse sobre las mismas imÃ¡genes o sobre el mismo lote de prueba.

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I5: COMPARACIÃ“N DE TIEMPOS                      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ ImÃ¡genes comparadas: 450                                    â”‚
â”‚ Tiempo promedio humano: 11.8 s                              â”‚
â”‚ Tiempo promedio IA: 0.041 s                                 â”‚
â”‚ ReducciÃ³n estimada: 99.65 %                                 â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ MÃ©todo       Media       Mediana      Min      Max           â”‚
â”‚ Humano       11.8 s      10.9 s       6.2 s    25.4 s        â”‚
â”‚ IA           0.041 s     0.039 s      0.031 s  0.070 s       â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Prueba pareada: t pareada / Wilcoxon segÃºn distribuciÃ³n      â”‚
â”‚ p-valor: mostrar resultado                                  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. ComparaciÃ³n del tiempo promedio de inspecciÃ³n entre evaluaciÃ³n humana e inferencia YOLOv11n.
```

---

# 9. Instrumento I6: Validez de contenido mediante V de Aiken

## Finalidad

Demostrar que expertos revisaron la guÃ­a de anotaciÃ³n y la ficha humana.

## QuÃ© valida

Valida que los Ã­tems del instrumento son pertinentes, claros y coherentes con CODEX.

## QuÃ© NO valida

No valida resultados del modelo ni desempeÃ±o humano. Solo valida que el instrumento tiene contenido aceptable.

## Ãtems que deben calificarse

| Ãtem | QuÃ© evalÃºa |
|---|---|
| Claridad de la clase normal | Si se entiende cuÃ¡ndo un hongo es normal |
| Claridad de clase danado | Si el criterio de pÃ©rdida de superficie es aplicable |
| Claridad de carbonizado | Si se diferencia de sombra/mancha |
| Claridad de aplastado | Si el proxy visual es aceptable |
| Claridad de larvas | Si el criterio de agujeros es aplicable |
| Claridad de impureza vegetal | Si no se confunde con parte del hongo |
| Claridad de impureza mineral | Si se declara la limitaciÃ³n visual |
| Claridad de pie_desprendido | Si el conteo es claro |
| Coherencia de la ficha humana | Si el trabajador puede marcar sin ambigÃ¼edad |
| Coherencia de decisiÃ³n apto/no apto | Si se entiende la decisiÃ³n final |

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I6: VALIDEZ DE CONTENIDO - V DE AIKEN           â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Expertos participantes: 3                                   â”‚
â”‚ Escala: 1 a 5                                                â”‚
â”‚ Criterios: claridad, pertinencia, coherencia                 â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Ãtem                         V Aiken       Estado           â”‚
â”‚ Clase larvas                 0.92          Aceptado         â”‚
â”‚ Clase carbonizado            0.86          Aceptado         â”‚
â”‚ Clase aplastado              0.71          Revisar          â”‚
â”‚ Impureza mineral visible     0.68          Declarar lÃ­mite  â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Resultado: guÃ­a validada con observaciones controladas       â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. Resultado de validez de contenido de la guÃ­a de anotaciÃ³n y ficha de evaluaciÃ³n mediante V de Aiken.
```

---

# 10. Instrumento I7: Concordancia / kappa

## Finalidad

Medir si los evaluadores humanos o anotadores coinciden mÃ¡s allÃ¡ del azar.

## QuÃ© valida

Valida la **confiabilidad del mÃ©todo humano** o la consistencia del rotulado.

## QuÃ© NO valida

No dice automÃ¡ticamente cuÃ¡l evaluador tiene razÃ³n. Solo mide acuerdo.

## Dos usos posibles

| Uso | ComparaciÃ³n | Resultado |
|---|---|---|
| Kappa interevaluador humano | trabajador 1 vs trabajador 2 vs trabajador 3 | variabilidad humana |
| Kappa interanotador | anotador A vs anotador B sobre etiquetas | confiabilidad del dataset |

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I7: CONCORDANCIA HUMANA / KAPPA                 â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Evaluadores: TRAB_01, TRAB_02, TRAB_03                      â”‚
â”‚ ImÃ¡genes comunes evaluadas: 450                             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Acuerdo observado: 0.78                                     â”‚
â”‚ Kappa Fleiss: 0.62                                          â”‚
â”‚ InterpretaciÃ³n: acuerdo moderado/sustancial segÃºn criterio   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Clases con menor acuerdo:                                   â”‚
â”‚ - aplastado                                                  â”‚
â”‚ - carbonizado                                                â”‚
â”‚ - impureza_mineral                                           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. Concordancia entre evaluadores humanos mediante kappa sobre el conjunto de prueba.
```

---

# 11. Instrumento I8: Ground truth CODEX auditado

## Finalidad

Definir la verdad de referencia contra la cual se comparan humano e IA.

## QuÃ© valida

Valida el punto central de la tesis: que existe una referencia CODEX operacionalizada para medir aciertos y errores.

## QuÃ© NO valida

No valida por sÃ­ solo al humano ni al modelo. Sirve como base de contraste.

## Reglas obligatorias

```text
- Cada imagen del test debe tener ground truth.
- El ground truth debe estar basado en la guÃ­a CODEX-YOLO.
- Debe indicar fuente: experto, consenso, auditorÃ­a o investigador con guÃ­a validada.
- Debe conservar observaciÃ³n de casos frontera.
- Debe congelarse antes de la comparaciÃ³n final.
```

## Campos mÃ­nimos

| Campo | Ejemplo |
|---|---|
| codigo_imagen | IMG_0001.jpg |
| clase_real | larvas |
| decision_real | no_apto |
| fuente_ground_truth | consenso_experto |
| auditor | EXP_01 |
| fecha_auditoria | 2026-05-07 |
| observacion | agujeros visibles, severidad leve |

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I8: GROUND TRUTH CODEX AUDITADO                 â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Imagen: IMG_0001.jpg                                        â”‚
â”‚ Clase real: larvas                                          â”‚
â”‚ DecisiÃ³n real: no_apto                                      â”‚
â”‚ Fuente: consenso experto                                    â”‚
â”‚ Auditor: EXP_01                                             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Evidencia visual                                             â”‚
â”‚ [Imagen con etiqueta auditada]                              â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ JustificaciÃ³n CODEX:                                         â”‚
â”‚ Presencia de agujeros visibles compatibles con daÃ±o por      â”‚
â”‚ larvas. Se etiqueta como defecto visible operacionalizado.   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Estado: GROUND TRUTH CONGELADO PARA TEST                    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. Registro de ground truth auditado segÃºn guÃ­a CODEX-YOLO para una imagen del conjunto de prueba.
```

---

# 12. Instrumento I9: Reporte de inferencia IA

## Finalidad

Registrar exactamente quÃ© detectÃ³ el modelo en cada imagen, con confianza, clase, bounding box y tiempo.

## QuÃ© valida

Permite evaluar el modelo contra ground truth.

## QuÃ© NO valida

Una detecciÃ³n visual bonita no prueba la tesis si no se compara contra ground truth.

## Campos mÃ­nimos

| Campo | Ejemplo |
|---|---|
| codigo_imagen | IMG_0001.jpg |
| modelo_version | yolov11n_codex_v1 |
| clase_detectada | larvas |
| confianza | 0.87 |
| bbox | x1,y1,x2,y2 |
| tiempo_ms | 41 |
| etiqueta_final_modelo | larvas |
| decision_modelo | no_apto |

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ INSTRUMENTO I9: INFERENCIA DEL MODELO YOLOv11n              â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Imagen: IMG_0001.jpg                                        â”‚
â”‚ Modelo: yolov11n_codex_v1                                   â”‚
â”‚ Tiempo inferencia: 41 ms                                    â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Detecciones                                                  â”‚
â”‚ Clase        Confianza      Coordenadas                      â”‚
â”‚ larvas       0.87           120,80,220,180                   â”‚
â”‚ carbonizado  0.76           300,90,370,160                   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Resultado final del modelo: larvas / no_apto                 â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ [Imagen original]       [Imagen con detecciones IA]          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. VisualizaciÃ³n de inferencia YOLOv11n sobre una imagen del conjunto de prueba.
```

---

# 13. Instrumento I10: Reporte estadÃ­stico final

## Finalidad

Convertir los datos en evidencia de hipÃ³tesis.

## QuÃ© valida

Valida directamente los objetivos e hipÃ³tesis.

## Debe responder estas preguntas

| Pregunta de tesis | Pantalla/resultado que responde |
|---|---|
| Â¿QuÃ© desempeÃ±o logra YOLOv11n por clase? | Tabla precision, recall, F1, mAP |
| Â¿CÃ³mo se compara frente al humano? | Tabla humano vs IA vs ground truth |
| Â¿Existe diferencia significativa? | McNemar |
| Â¿QuÃ© tan variable es el humano? | Kappa entre evaluadores |
| Â¿CuÃ¡l es la diferencia de tiempo? | ComparaciÃ³n de tiempos |

## CÃ³mo debe verse en la app

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ REPORTE FINAL DE VALIDACIÃ“N DE TESIS                        â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Dataset test: 450 imÃ¡genes                                  â”‚
â”‚ Ground truth: 450/450 completo                              â”‚
â”‚ EvaluaciÃ³n humana: 450/450 vÃ¡lida                           â”‚
â”‚ Inferencia IA: 450/450 procesada                            â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ HipÃ³tesis H1 - DesempeÃ±o del modelo                         â”‚
â”‚ mAP@0.5: 0.89 | Precision global: 0.87 | Recall: 0.84       â”‚
â”‚ Estado: SOPORTADA / NO SOPORTADA segÃºn umbral definido       â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ HipÃ³tesis H2 - Variabilidad humana                          â”‚
â”‚ Kappa humano: 0.62                                           â”‚
â”‚ Estado: EXISTE VARIABILIDAD MEDIBLE                         â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ HipÃ³tesis H3 - Diferencia humano vs IA                      â”‚
â”‚ McNemar p-valor: 0.03                                       â”‚
â”‚ Estado: DIFERENCIA SIGNIFICATIVA / NO SIGNIFICATIVA          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Eficiencia temporal                                          â”‚
â”‚ Humano: 11.8 s/img | IA: 0.041 s/img                        â”‚
â”‚ ReducciÃ³n: 99.65 %                                           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. Panel final de validaciÃ³n de hipÃ³tesis y mÃ©tricas comparativas entre evaluaciÃ³n humana y YOLOv11n.
```

---

# 14. Tabla maestra de contraste entre instrumentos

Esta tabla debe existir en la app como pantalla â€œTrazabilidad de tesisâ€.

| Objetivo especÃ­fico | Instrumento | Insumo | Salida | Evidencia visual |
|---|---|---|---|---|
| Definir clases CODEX | GuÃ­a de anotaciÃ³n | CODEX + criterios visuales | Codebook YOLO | Pantalla de clases |
| DiseÃ±ar protocolo de captura | Protocolo de captura | SesiÃ³n/lote/imÃ¡genes | ImÃ¡genes vÃ¡lidas | Checklist captura |
| Construir dataset etiquetado | Visor/auditorÃ­a YOLO | ImÃ¡genes + labels | Dataset auditado | Imagen con cajas |
| Entrenar YOLOv11n | BitÃ¡cora entrenamiento | Dataset train/val | best.pt + mÃ©tricas val | BitÃ¡cora |
| Evaluar desempeÃ±o | Reporte IA | best.pt + test | precision/recall/mAP | Tabla mÃ©tricas |
| Comparar con humanos | Excel humano + ground truth | Test comÃºn | McNemar/kappa/tiempos | Panel final |

---

# 15. Pantalla obligatoria: â€œEstado de validaciÃ³n de tesisâ€

Esta pantalla debe resolver tu problema actual: que la app funciona, pero no se ve si la tesis se estÃ¡ validando.

## Wireframe

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ ESTADO DE VALIDACIÃ“N DE TESIS                               â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Tesis: YOLOv11n + CODEX STAN 39-1981                         â”‚
â”‚ Estado general: EN VALIDACIÃ“N / VALIDACIÃ“N COMPLETA          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ 1. Protocolo de captura                 [VALIDADO]           â”‚
â”‚ 2. GuÃ­a de anotaciÃ³n CODEX-YOLO          [VALIDADO]           â”‚
â”‚ 3. Dataset etiquetado/auditado           [PENDIENTE 82%]      â”‚
â”‚ 4. Ground truth test                     [PENDIENTE 65%]      â”‚
â”‚ 5. Excel humano importado                [VALIDADO]           â”‚
â”‚ 6. Modelo YOLOv11n cargado               [VALIDADO]           â”‚
â”‚ 7. Inferencia IA ejecutada               [VALIDADO]           â”‚
â”‚ 8. MÃ©tricas calculadas                   [PENDIENTE]          â”‚
â”‚ 9. HipÃ³tesis evaluadas                   [PENDIENTE]          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Bloqueos metodolÃ³gicos                                      â”‚
â”‚ [!] Faltan 35 imÃ¡genes test con ground truth auditado         â”‚
â”‚ [!] No se calculÃ³ kappa humano porque solo hay 1 evaluador    â”‚
â”‚ [!] McNemar requiere humano e IA sobre las mismas imÃ¡genes    â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ PrÃ³xima acciÃ³n recomendada                                  â”‚
â”‚ Completar ground truth del test antes de generar mÃ©tricas     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Resultado esperado

La app debe decir claramente:

```text
La tesis aÃºn no estÃ¡ validada porque falta X.
```

o:

```text
La tesis tiene evidencia suficiente para sustentar H1, H2 y H3.
```

---

# 16. Pantalla obligatoria: â€œValidaciÃ³n por hipÃ³tesisâ€

## H1

**HipÃ³tesis:** El modelo alcanzarÃ¡ valores altos de precision, recall y mAP en las clases visibles definidas.

Pantalla:

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ H1: DESEMPEÃ‘O DEL MODELO YOLOv11n                           â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Clase              Precision   Recall   F1     AP@0.5       â”‚
â”‚ normal             0.91        0.89     0.90   0.92         â”‚
â”‚ danado             0.84        0.80     0.82   0.86         â”‚
â”‚ carbonizado        0.79        0.75     0.77   0.81         â”‚
â”‚ aplastado          0.72        0.68     0.70   0.74         â”‚
â”‚ larvas             0.88        0.85     0.86   0.90         â”‚
â”‚ impureza_vegetal   0.83        0.79     0.81   0.84         â”‚
â”‚ impureza_mineral   0.65        0.52     0.58   0.60         â”‚
â”‚ pie_desprendido    0.86        0.82     0.84   0.87         â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Resultado H1: SOPORTADA PARCIALMENTE                         â”‚
â”‚ ObservaciÃ³n: impureza_mineral tiene bajo recall por lÃ­mite   â”‚
â”‚ visual declarado en el alcance.                              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## H2

**HipÃ³tesis:** La clasificaciÃ³n humana presenta variabilidad medible.

Pantalla:

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ H2: CONCORDANCIA INTEREVALUADOR HUMANA                      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Evaluadores: 3                                               â”‚
â”‚ ImÃ¡genes comunes: 450                                        â”‚
â”‚ Kappa Fleiss: 0.62                                           â”‚
â”‚ Acuerdo observado: 78%                                       â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Clases con mayor desacuerdo:                                 â”‚
â”‚ 1. aplastado                                                 â”‚
â”‚ 2. carbonizado                                               â”‚
â”‚ 3. impureza_mineral                                          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Resultado H2: SOPORTADA                                      â”‚
â”‚ La variabilidad humana es medible y se concentra en casos    â”‚
â”‚ frontera o clases visualmente ambiguas.                      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## H3

**HipÃ³tesis:** Existe diferencia significativa en proporciÃ³n de aciertos entre humano y modelo.

Pantalla:

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ H3: MCNEMAR - HUMANO VS MODELO                              â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Tabla pareada contra ground truth                            â”‚
â”‚                                                             â”‚
â”‚                         Modelo acierta   Modelo falla        â”‚
â”‚ Humano acierta              320              35              â”‚
â”‚ Humano falla                 60              35              â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ b = humano acierta / modelo falla: 35                        â”‚
â”‚ c = humano falla / modelo acierta: 60                        â”‚
â”‚ McNemar p-valor: 0.014                                       â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Resultado H3: DIFERENCIA SIGNIFICATIVA                       â”‚
â”‚ InterpretaciÃ³n: el modelo corrige mÃ¡s casos donde el humano  â”‚
â”‚ falla que al revÃ©s, bajo el conjunto evaluado.               â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

# 17. Pantalla obligatoria: â€œCaso por imagenâ€

Esta pantalla sirve para capturas fuertes en sustentaciÃ³n.

## Wireframe

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ CASO INDIVIDUAL DE VALIDACIÃ“N                               â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Imagen: IMG_0001.jpg       Lote: LOTE_001                   â”‚
â”‚ Split: test                Estado: evaluada                 â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ [Imagen con ground truth]        [Imagen con detecciÃ³n IA]   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Ground truth CODEX: larvas / no_apto                         â”‚
â”‚ Humano:             normal / apto         Resultado: FALLA   â”‚
â”‚ IA:                 larvas / no_apto      Resultado: ACIERTA â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Tiempo humano: 13.2 s                                        â”‚
â”‚ Tiempo IA: 0.041 s                                           â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ JustificaciÃ³n:                                               â”‚
â”‚ La imagen presenta orificios visibles compatibles con daÃ±o   â”‚
â”‚ por larvas segÃºn la guÃ­a CODEX-YOLO.                         â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Captura para tesis

Nombre recomendado:

```text
Figura X. ComparaciÃ³n por caso entre ground truth CODEX, evaluaciÃ³n humana e inferencia YOLOv11n.
```

---

# 18. Pantalla obligatoria: â€œErrores y discusiÃ³nâ€

La tesis no debe ocultar errores. Debe mostrarlos para discutirlos.

## QuÃ© debe mostrar

| Tipo de error | Ejemplo | InterpretaciÃ³n |
|---|---|---|
| Falso positivo IA | detecta carbonizado donde era sombra | problema de iluminaciÃ³n o clase ambigua |
| Falso negativo IA | no detecta impureza pequeÃ±a | objeto pequeÃ±o o baja resoluciÃ³n |
| Error humano | trabajador marca normal donde habÃ­a larvas | fatiga, criterio visual, caso frontera |
| Desacuerdo ground truth | dos auditores discrepan | clase necesita regla mÃ¡s clara |

## Wireframe

```text
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ ANÃLISIS DE ERRORES                                         â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Clase con mÃ¡s falsos negativos IA: impureza_mineral          â”‚
â”‚ Clase con mÃ¡s falsos positivos IA: carbonizado               â”‚
â”‚ Clase con mÃ¡s error humano: aplastado                        â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ Imagen       GT          Humano      IA        Tipo error    â”‚
â”‚ IMG_0102     carbonizado normal      normal    FN IA + H     â”‚
â”‚ IMG_0201     normal      danado      normal    FP humano     â”‚
â”‚ IMG_0330     larvas      normal      larvas    error humano  â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ DiscusiÃ³n sugerida:                                         â”‚
â”‚ Los errores se concentran en clases donde el criterio visual â”‚
â”‚ se aproxima a una mediciÃ³n fÃ­sica o donde hay casos frontera.â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

# 19. Reglas para que la app sÃ­ â€œmuestre tesisâ€

La app debe dejar de ser solo una herramienta de carga/procesamiento. Debe comportarse como un **tablero de validaciÃ³n metodolÃ³gica**.

## Reglas obligatorias

```text
1. Cada pantalla debe indicar quÃ© instrumento representa.
2. Cada instrumento debe indicar quÃ© variable/objetivo valida.
3. Cada resultado debe indicar si sirve para H1, H2, H3 o eficiencia.
4. Ninguna mÃ©trica debe calcularse sin ground truth completo.
5. NingÃºn Excel humano debe asumirse como verdad.
6. Toda imagen comparada debe existir en los tres lados:
   - ground truth
   - humano
   - IA
7. La app debe mostrar bloqueos metodolÃ³gicos cuando falten datos.
8. La app debe exportar capturas/tablas con nombres listos para tesis.
```

---

# 20. Criterios de aceptaciÃ³n para la segunda etapa del agente

Copia esto al agente:

```md
Implementar la segunda etapa de afinamiento de la aplicaciÃ³n para que no solo procese imÃ¡genes, sino que evidencie la validaciÃ³n de la tesis.

La app debe agregar una capa metodolÃ³gica con estos tableros:

1. Estado de validaciÃ³n de tesis
- Mostrar si estÃ¡n completos: protocolo de captura, guÃ­a de anotaciÃ³n, dataset auditado, ground truth, Excel humano, modelo cargado, inferencia IA, mÃ©tricas e hipÃ³tesis.
- Mostrar bloqueos metodolÃ³gicos, por ejemplo: falta ground truth, falta kappa, falta McNemar, imÃ¡genes no coinciden entre humano e IA.

2. Instrumentos de tesis
- Crear una pantalla por instrumento:
  I1 Protocolo de captura
  I2 GuÃ­a de anotaciÃ³n CODEX-YOLO
  I3 Ficha de evaluaciÃ³n humana
  I4 BitÃ¡cora de entrenamiento
  I5 Registro de tiempos
  I6 V de Aiken / validez de contenido
  I7 Kappa / concordancia
  I8 Ground truth CODEX auditado
  I9 Reporte de inferencia IA
  I10 Reporte estadÃ­stico final

3. Trazabilidad objetivo-instrumento-resultado
- Mostrar tabla que relacione cada objetivo especÃ­fico de la tesis con su instrumento, insumo, salida, mÃ©trica y captura sugerida.

4. ValidaciÃ³n por hipÃ³tesis
- H1: mostrar precision, recall, F1 y mAP por clase.
- H2: mostrar kappa/acuerdo entre evaluadores humanos o anotadores.
- H3: mostrar tabla de McNemar usando aciertos/fallos pareados humano vs modelo contra ground truth.
- Eficiencia: mostrar tiempo promedio humano vs IA y prueba pareada si aplica.

5. Caso individual de validaciÃ³n
- Para cada imagen debe verse: ground truth CODEX, evaluaciÃ³n humana, inferencia IA, acierto/fallo de cada mÃ©todo, tiempos y justificaciÃ³n CODEX.

6. AnÃ¡lisis de errores
- Mostrar falsos positivos, falsos negativos, errores humanos, desacuerdos y clases mÃ¡s problemÃ¡ticas.

7. Exportables para tesis
- Exportar tablas CSV/Excel y capturas o vistas listas para copiar a tesis:
  - protocolo de captura
  - guÃ­a de anotaciÃ³n
  - validaciÃ³n Excel humano
  - ground truth auditado
  - inferencia IA
  - matriz de confusiÃ³n
  - kappa
  - McNemar
  - comparaciÃ³n de tiempos
  - tablero final de hipÃ³tesis

Regla principal:
El Excel humano no es ground truth. El ground truth debe venir de auditorÃ­a/consenso experto usando la guÃ­a CODEX-YOLO. La comparaciÃ³n final debe ser humano vs ground truth e IA vs ground truth sobre las mismas imÃ¡genes.
```

---

# 21. QuÃ© debes revisar ahora en tu app funcional

Usa esta lista para saber si tu app ya valida la tesis o solo procesa datos.

| Pregunta | Si responde â€œnoâ€, falta tesis |
|---|---|
| Â¿La app muestra quÃ© objetivo especÃ­fico se estÃ¡ validando? | Falta trazabilidad |
| Â¿La app diferencia Excel humano de ground truth? | Falta lÃ³gica metodolÃ³gica |
| Â¿La app bloquea mÃ©tricas si falta ground truth? | Falta control cientÃ­fico |
| Â¿La app muestra kappa? | Falta H2 |
| Â¿La app muestra McNemar? | Falta H3 |
| Â¿La app muestra mAP/precision/recall por clase? | Falta H1 |
| Â¿La app muestra tiempos humano vs IA? | Falta eficiencia |
| Â¿La app muestra errores por clase? | Falta discusiÃ³n |
| Â¿La app exporta tablas/capturas para tesis? | Falta sustentaciÃ³n |
| Â¿La app declara limitaciones CODEX visuales? | Falta defensa metodolÃ³gica |

---

# 22. Resultado final esperado

Al terminar esta segunda etapa, la app debe poder decir:

```text
La tesis estÃ¡ validada operativamente porque:

1. Las clases fueron definidas desde CODEX STAN 39-1981.
2. La guÃ­a de anotaciÃ³n fue revisada/validada.
3. El dataset tiene etiquetas auditadas.
4. El test tiene ground truth congelado.
5. Los trabajadores evaluaron las mismas imÃ¡genes.
6. El modelo YOLOv11n procesÃ³ las mismas imÃ¡genes.
7. Se calcularon mÃ©tricas tÃ©cnicas del modelo.
8. Se calculÃ³ concordancia humana.
9. Se aplicÃ³ McNemar sobre aciertos pareados.
10. Se comparÃ³ el tiempo humano contra el tiempo IA.
11. Se identificaron errores y limitaciones por clase.
```

Esa es la diferencia entre una app que â€œcorre YOLOâ€ y una herramienta que **sustenta una tesis**.


