import { create } from "zustand"

export const MODULES = [
  "thesis",
  "runs",
  "dashboard",
  "detections",
  "instruments",
  "dataset",
  "labeling",
  "audit",
  "human",
  "groundTruth",
  "models",
  "inference",
  "comparison",
  "reports",
  "config",
] as const

export type ModuleId = (typeof MODULES)[number]

type AppState = {
  activeModule: ModuleId
  activeRunId?: string
  setActiveModule: (module: ModuleId) => void
  setActiveRunId: (runId: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeModule: "thesis",
  activeRunId: undefined,
  setActiveModule: (activeModule) => set({ activeModule }),
  setActiveRunId: (activeRunId) => set({ activeRunId }),
}))
