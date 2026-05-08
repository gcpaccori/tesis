export const CLASSES = [
  "normal",
  "danado",
  "carbonizado",
  "aplastado",
  "larvas",
  "impureza_vegetal",
  "impureza_mineral",
  "pie_desprendido",
  "contaminante",
  "pluma",
] as const

export const CLASS_LABELS: Record<(typeof CLASSES)[number], string> = {
  normal: "Normal",
  danado: "Danado",
  carbonizado: "Carbonizado",
  aplastado: "Aplastado",
  larvas: "Larvas",
  impureza_vegetal: "Impureza vegetal",
  impureza_mineral: "Impureza mineral",
  pie_desprendido: "Pie desprendido",
  contaminante: "Contaminante",
  pluma: "Pluma",
}
