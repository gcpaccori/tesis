PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS lotes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo_lote TEXT NOT NULL UNIQUE,
  origen TEXT,
  fecha_captura TEXT,
  descripcion TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS imagenes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lote_id INTEGER,
  codigo_imagen TEXT NOT NULL UNIQUE,
  ruta_archivo TEXT NOT NULL,
  width INTEGER,
  height INTEGER,
  tipo_presentacion TEXT,
  sesion_captura TEXT,
  split_dataset TEXT CHECK (split_dataset IN ('train', 'val', 'test')),
  estado_auditoria TEXT NOT NULL DEFAULT 'pendiente',
  hash_archivo TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (lote_id) REFERENCES lotes(id)
);

CREATE TABLE IF NOT EXISTS etiquetas_yolo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  imagen_id INTEGER NOT NULL,
  class_id INTEGER NOT NULL,
  class_name TEXT NOT NULL,
  x_center REAL NOT NULL,
  y_center REAL NOT NULL,
  width REAL NOT NULL,
  height REAL NOT NULL,
  fuente TEXT NOT NULL DEFAULT 'manual',
  anotador TEXT,
  estado TEXT NOT NULL DEFAULT 'pendiente',
  observacion TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (imagen_id) REFERENCES imagenes(id)
);

CREATE TABLE IF NOT EXISTS auditoria_etiquetas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  imagen_id INTEGER NOT NULL,
  etiqueta_id INTEGER,
  usuario TEXT NOT NULL,
  accion TEXT NOT NULL,
  valor_anterior TEXT,
  valor_nuevo TEXT,
  motivo TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (imagen_id) REFERENCES imagenes(id),
  FOREIGN KEY (etiqueta_id) REFERENCES etiquetas_yolo(id)
);

CREATE TABLE IF NOT EXISTS evaluaciones_humanas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  imagen_id INTEGER NOT NULL,
  evaluador TEXT NOT NULL,
  defecto_danado INTEGER DEFAULT 0,
  defecto_carbonizado INTEGER DEFAULT 0,
  defecto_aplastado INTEGER DEFAULT 0,
  defecto_larvas TEXT,
  impureza_vegetal INTEGER DEFAULT 0,
  impureza_mineral INTEGER DEFAULT 0,
  pie_desprendido_cantidad INTEGER DEFAULT 0,
  etiqueta_final_humana TEXT NOT NULL,
  decision_humana TEXT NOT NULL,
  tiempo_segundos REAL NOT NULL,
  observaciones TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (imagen_id, evaluador),
  FOREIGN KEY (imagen_id) REFERENCES imagenes(id)
);

CREATE TABLE IF NOT EXISTS modelos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  modelo_version TEXT NOT NULL UNIQUE,
  model_path TEXT NOT NULL,
  model_hash_sha256 TEXT,
  dataset_version TEXT,
  epochs INTEGER,
  imgsz INTEGER,
  batch_size INTEGER,
  optimizer TEXT,
  ultralytics_version TEXT,
  fecha_entrenamiento TEXT,
  metricas_validacion TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resultados_modelo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  imagen_id INTEGER NOT NULL,
  modelo_id INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  clase_principal_modelo TEXT,
  decision_modelo TEXT,
  detecciones_total INTEGER,
  tiempo_inferencia_ms REAL,
  confidence_threshold REAL,
  iou_threshold REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (imagen_id) REFERENCES imagenes(id),
  FOREIGN KEY (modelo_id) REFERENCES modelos(id)
);

CREATE TABLE IF NOT EXISTS detecciones_modelo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  resultado_modelo_id INTEGER NOT NULL,
  class_id INTEGER NOT NULL,
  class_name TEXT NOT NULL,
  confidence REAL NOT NULL,
  x1 REAL NOT NULL,
  y1 REAL NOT NULL,
  x2 REAL NOT NULL,
  y2 REAL NOT NULL,
  bbox_area_px REAL,
  FOREIGN KEY (resultado_modelo_id) REFERENCES resultados_modelo(id)
);

CREATE TABLE IF NOT EXISTS ground_truth (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  imagen_id INTEGER NOT NULL UNIQUE,
  clase_principal_real TEXT NOT NULL,
  decision_real TEXT NOT NULL,
  defectos_reales_multietiqueta TEXT,
  severidad_larvas TEXT,
  fuente_ground_truth TEXT NOT NULL,
  auditor TEXT NOT NULL,
  nivel_confianza TEXT,
  observacion TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (imagen_id) REFERENCES imagenes(id)
);

CREATE TABLE IF NOT EXISTS metricas_experimento (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  experimento TEXT NOT NULL,
  modelo_id INTEGER NOT NULL,
  total_imagenes INTEGER,
  accuracy_humano REAL,
  accuracy_modelo REAL,
  precision_global REAL,
  recall_global REAL,
  f1_global REAL,
  map50 REAL,
  map5095 REAL,
  kappa_humano REAL,
  kappa_modelo REAL,
  mcnemar_stat REAL,
  mcnemar_p_value REAL,
  tiempo_promedio_humano REAL,
  tiempo_promedio_modelo REAL,
  resultados_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (modelo_id) REFERENCES modelos(id)
);

CREATE TABLE IF NOT EXISTS configuracion_metodologica (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  metodologia_locked INTEGER NOT NULL DEFAULT 0,
  test_locked INTEGER NOT NULL DEFAULT 0,
  class_priority TEXT NOT NULL,
  decision_rules TEXT NOT NULL,
  confidence_default REAL NOT NULL DEFAULT 0.25,
  iou_default REAL NOT NULL DEFAULT 0.50,
  split_policy TEXT NOT NULL DEFAULT '70/20/10',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
