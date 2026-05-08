# Codebook CODEX-YOLO para hongos comestibles desecados

## Objetivo

Definir las clases de anotación y reglas operativas para etiquetar imágenes de hongos comestibles desecados usando formato YOLO.

## Clases internas

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

## Reglas generales de anotación

1. Dibujar caja mínima alrededor del objeto o defecto visible.
2. No incluir fondo innecesario.
3. No etiquetar sombras como defecto.
4. No etiquetar impureza si es parte del propio hongo.
5. Si hay duda, marcar la imagen como `observada`.
6. Si coexisten varios defectos, registrar todas las detecciones, pero definir una clase principal para análisis por imagen.
7. Las reglas basadas en masa o laboratorio se declaran como proxy visual.

## Clase 0: normal

### Definición operativa

Hongo sin defectos visibles relevantes según las clases del estudio.

### Incluir

- Piezas sin agujeros visibles.
- Sin carbonización.
- Sin deformación crítica.
- Sin impurezas visibles.
- Sin pie desprendido visible como defecto.

### Excluir

- Cualquier pieza con defecto visible.
- Casos dudosos.
- Piezas parcialmente tapadas que impidan evaluar.

### Caja

Caja sobre el hongo completo.

---

## Clase 1: danado

### Definición operativa

Pérdida visible de material o daño estructural relevante.

### Criterio sugerido

- Enteros: falta mayor a 1/4 del sombrerete.
- Lonjas: falta mayor a 1/3 de la superficie visible.

### Incluir

- Bordes rotos con pérdida fuerte.
- Sombreretes incompletos.
- Fragmentos con daño estructural evidente.

### Excluir

- Variación natural de forma.
- Cortes normales de procesamiento.
- Pequeñas roturas no significativas.

### Caja

Preferible caja sobre la pieza completa dañada.

---

## Clase 2: carbonizado

### Definición operativa

Vestigios oscuros compatibles con carbonización en la superficie del hongo.

### Incluir

- Manchas negras o marrón oscuro propias del tejido.
- Zonas quemadas visibles.
- Superficie con apariencia carbonizada.

### Excluir

- Sombras.
- Fondo oscuro.
- Diferencias naturales de color.
- Baja iluminación.

### Caja

Dos estrategias posibles. Elegir una y mantenerla:

```text
Estrategia A: caja sobre pieza completa carbonizada.
Estrategia B: caja sobre zona carbonizada.
```

Recomendación para tesis: usar estrategia A si la decisión es por pieza; usar B si se quiere medir área proxy.

---

## Clase 3: aplastado

### Definición operativa

Deformación visible por presión, compactación o rotura.

### Nota CODEX

El estándar se relaciona con partes que pasan por tamiz de malla 5x5 mm. Como la imagen no mide tamiz directamente, se usa proxy visual con escala.

### Incluir

- Fragmentos muy pequeños.
- Piezas compactadas.
- Trozos deformados por presión.
- Partículas que visualmente se aproximen a la regla de tamaño definida.

### Excluir

- Variación natural.
- Piezas planas por forma normal.
- Lonjas normales.

### Caja

Caja sobre fragmento o pieza aplastada.

---

## Clase 4: larvas

### Definición operativa

Agujeros visibles compatibles con daño por larvas.

### Subcriterio de severidad

Aunque la clase interna sea `larvas`, guardar severidad adicional:

```text
leve: 1 a 3 agujeros visibles
severo: 4 o más agujeros visibles
```

### Incluir

- Agujeros circulares o patrones compatibles con larvas.
- Daño repetido por perforación.

### Excluir

- Rotura mecánica evidente.
- Huecos de corte.
- Sombras internas.

### Caja

Preferible caja sobre la pieza afectada. Si se quiere análisis fino, también guardar región de agujeros como metadato secundario.

---

## Clase 5: impureza_vegetal

### Definición operativa

Material vegetal ajeno al hongo.

### Incluir

- Hojas.
- Agujas de pino.
- Tallos.
- Restos vegetales no pertenecientes al hongo.

### Excluir

- Partes normales del hongo.
- Pies desprendidos, porque tienen clase propia.
- Fondo o restos no identificables.

### Caja

Caja solo sobre la impureza.

---

## Clase 6: impureza_mineral

### Definición operativa

Tierra, arena o piedras visibles.

### Limitación

La impureza mineral definida por análisis de residuo insoluble no se infiere plenamente desde RGB. En la herramienta solo se registra evidencia visual.

### Incluir

- Tierra visible.
- Arena visible.
- Piedra visible.
- Partículas minerales claramente distinguibles.

### Excluir

- Sombra.
- Polvo no verificable.
- Fondo con textura.

### Caja

Caja solo sobre la partícula o zona mineral visible.

---

## Clase 7: pie_desprendido

### Definición operativa

Pie separado del sombrerete visible como unidad independiente.

### Incluir

- Pie suelto.
- Tallo separado.
- Pie sin sombrerete.

### Excluir

- Pie todavía unido al sombrerete.
- Fragmento de hongo no identificable como pie.
- Impureza vegetal.

### Caja

Caja sobre el pie desprendido.

## Prioridad para clase principal por imagen

Cuando una imagen tenga varias clases, guardar todas las detecciones pero calcular una clase principal para comparación humana.

Prioridad sugerida:

```text
impureza_mineral
impureza_vegetal
larvas severo
carbonizado
danado
aplastado
pie_desprendido
larvas leve
normal
```

Esta prioridad puede ajustarse, pero debe quedar congelada antes de evaluación final.

## Decisión de conformidad

No mezclar automáticamente clase con conformidad. La clase describe el defecto; la conformidad decide si la muestra es apta, no apta u observada.

```text
clase_detectada -> regla CODEX operacionalizada -> decision_final
```

## Salidas requeridas por imagen

```json
{
  "codigo_imagen": "LOTE_001_IMG_0001",
  "clases_detectadas": ["larvas", "carbonizado"],
  "clase_principal": "larvas",
  "severidad_larvas": "leve",
  "decision_codex_proxy": "observado",
  "observacion": "Agujeros visibles; requiere revisión si se usa severidad."
}
```
