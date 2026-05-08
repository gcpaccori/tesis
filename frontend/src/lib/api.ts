export type Dashboard = {
  summary: Record<string, number | boolean>
  alerts: Array<{ code: string; severity: "info" | "warning" | "error"; message: string }>
  methodology: {
    metodologia_locked: boolean
    test_locked: boolean
    ground_truth_ready: boolean
    paired_ready: boolean
  }
}

export type ImageItem = {
  id: number
  codigo_imagen: string
  codigo_lote: string
  ruta_archivo: string
  width: number
  height: number
  split_dataset: "train" | "val" | "test"
  estado_auditoria: string
  labels_count: number
  has_ground_truth: boolean
  duplicate_warning: boolean
}

export type LabelItem = {
  id: number
  image_id: number
  class_id: number
  class_name: string
  x_center: number
  y_center: number
  width: number
  height: number
  estado: string
  fuente: string
  observacion?: string
}

export type HumanEvaluation = {
  id: number
  codigo_imagen: string
  evaluador: string
  etiqueta_final_humana: string
  decision_humana: string
  tiempo_segundos: number
  estado: string
}

export type GroundTruth = {
  id: number
  codigo_imagen: string
  clase_principal_real: string
  decision_real: string
  auditor: string
  nivel_confianza: string
  locked: boolean
}

export type ModelItem = {
  id: number
  modelo_version: string
  dataset_version: string
  epochs: number
  imgsz: number
  map50: number
  map5095: number
  model_hash_sha256: string
}

export type InferenceRun = {
  run_id: string
  modelo_version: string
  total_imagenes: number
  imagenes_procesadas: number
  confidence_threshold: number
  iou_threshold: number
  tiempo_promedio_ms: number
  results: Array<{
    codigo_imagen: string
    clase_principal_modelo: string
    decision_modelo: string
    detecciones_total: number
    tiempo_inferencia_ms: number
  }>
}

export type Comparison = {
  experiment_id: string
  rows: Array<{
    codigo_imagen: string
    ground_truth: string
    humano: string
    ia: string
    humano_correcto: boolean
    ia_correcto: boolean
    tiempo_humano: number
    tiempo_ia: number
  }>
  metrics: {
    total: number
    accuracy_humano: number
    accuracy_modelo: number
    kappa_humano: number
    kappa_modelo: number
    mcnemar: { a: number; b: number; c: number; d: number; statistic: number; p_value: number }
    tiempos: {
      promedio_humano: number
      promedio_ia: number
      factor_velocidad: number
      diferencia_promedio: number
    }
    per_class_model: Record<string, { precision: number; recall: number; f1: number; support: number }>
    map50: number
    map5095: number
  }
  warnings: string[]
}

export type ThesisRun = {
  run: {
    id: string
    name?: string
    status: "ejecutada" | string
    executed_at: string
    model_version: string
    cooperative: string
    thesis_title: string
    verdict: string
    data_origin: string
  }
  dataset: {
    total_images: number
    annotated_images: number
    unlabeled_images: number
    total_detections: number
    class_distribution: Record<string, number>
    evaluated_images: number
    human_evaluations: number
    paired_rows: number
  }
  technical: {
    precision_global_modelo: number
    recall_global_modelo: number
    f1_global_modelo: number
    precision_global_humano: number
    recall_global_humano: number
    f1_global_humano: number
  }
  metrics: Comparison["metrics"] & {
    labels: string[]
    per_class_human: Record<string, { precision: number; recall: number; f1: number; support: number }>
  }
  per_class: Array<{
    class_name: string
    class_display: string
    support: number
    model_precision: number
    model_recall: number
    model_f1: number
    human_precision: number
    human_recall: number
    human_f1: number
  }>
  errors: {
    human_total: number
    model_total: number
    human_by_class: Array<{ class_name: string; class_display: string; errores: number; participacion: number }>
    model_by_class: Array<{ class_name: string; class_display: string; errores: number; participacion: number }>
  }
  hypotheses: Array<{ codigo: string; hipotesis: string; estado: string; resultado: string }>
  questions: Array<{ pregunta: string; respuesta: string }>
  cases: Array<{
    tipo: string
    hallazgo: string
    codigo_imagen: string
    archivo_imagen: string
    url: string
    ground_truth: string
    humano: string
    ia: string
    tiempo_humano: number
    tiempo_ia_ms: number
    confianza_modelo: number
    detecciones_especialista: number
  }>
  limitations: Array<{ limitacion: string; como_se_declara: string }>
  downloads: Record<string, string>
}

export type ThesisRunSummary = {
  id: string
  name: string
  status: string
  executed_at: string
  model_version: string
  data_origin: string
  evaluated_images: number
  accuracy_modelo: number
  accuracy_humano: number
  mcnemar_p: number
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ""

export function apiUrl(path: string) {
  return `${API_BASE}${path}`
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Error HTTP ${response.status}`)
  }

  return response.json() as Promise<T>
}

export type SpecialistDetection = {
  class_id: number
  class_name: string
  class_display: string
  points: Array<{ x: number; y: number }>
  bbox: {
    x_min: number
    y_min: number
    x_max: number
    y_max: number
    width: number
    height: number
  }
}

export type SpecialistImage = {
  codigo_imagen: string
  file: string
  url: string
  width: number
  height: number
  split: string
  detections: SpecialistDetection[]
  detections_count: number
  primary_class: string
  primary_display: string
  decision_codex_proxy: string
  annotated: boolean
}

export type SpecialistDetectionsResponse = {
  dataset: {
    name: string
    task: string
    url: string
    class_names: Record<string, string>
    class_display: Record<string, string>
  }
  cooperative: string
  summary: {
    total_images: number
    annotated_images: number
    unlabeled_images: number
    total_detections: number
    class_distribution: Record<string, number>
  }
  limit: number
  offset: number
  total_filtered: number
  images: SpecialistImage[]
}

export type ThesisInstrument = {
  code: string
  name: string
  purpose: string
  validates: string
  does_not_validate: string
  evidence: string
  status: "listo" | "parcial" | "pendiente"
  download: string
  suggested_capture: string
}

export type InstrumentsResponse = {
  cooperative: string
  instruments: ThesisInstrument[]
  validation_state: Array<{
    item: string
    status: "listo" | "parcial" | "pendiente"
    evidence: string
    block_if_missing: boolean
  }>
  traceability: Array<{
    objetivo: string
    instrumento: string
    insumo: string
    salida: string
    metrica: string
    captura_sugerida: string
  }>
}
