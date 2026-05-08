# QA metodologico

## Cubierto en pruebas automaticas

- Casos invalidos YOLO:
  - clase fuera de rango
  - coordenada fuera de rango
  - ancho/alto cero o negativo
  - clase no numerica
- Accuracy del caso de aceptacion.
- Tabla McNemar del caso de aceptacion.
- Promedios y factor de velocidad.

## Cubierto en logica backend

- El Excel humano se inserta solo en `evaluaciones_humanas`.
- Las metricas se calculan solo con interseccion valida:
  - imagen
  - ground truth
  - evaluacion humana
  - resultado modelo
  - tiempos
- La configuracion metodologica y el test tienen banderas de bloqueo.
- Cada corrida de IA conserva version de modelo, thresholds y `run_id`.

## Pendiente para datos reales

- Conectar carga fisica de imagenes.
- Conectar Ultralytics con `best.pt`.
- Implementar roles de usuario para modificar ground truth bloqueado.
- Exportar XLSX/PDF ademas de Markdown/CSV.
