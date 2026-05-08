import {
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  Brain,
  CheckCircle2,
  ClipboardList,
  Clock3,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  GitCompare,
  Images,
  Layers3,
  LayoutDashboard,
  Lock,
  Microscope,
  PlayCircle,
  Save,
  ScanLine,
  Settings2,
  ShieldCheck,
  Target,
  Trophy,
  Upload,
  UserRoundCheck,
  XCircle,
} from "lucide-react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { type CSSProperties, useMemo, useState } from "react"
import {
  api,
  apiUrl,
  type Comparison,
  type Dashboard,
  type GroundTruth,
  type HumanEvaluation,
  type ImageItem,
  type InferenceRun,
  type InstrumentsResponse,
  type LabelItem,
  type ModelItem,
  type SpecialistDetectionsResponse,
  type SpecialistImage,
  type ThesisRun,
  type ThesisRunSummary,
} from "@/lib/api"
import { CLASS_LABELS } from "@/lib/constants"
import { useAppStore, type ModuleId } from "@/store/useAppStore"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const navigation: Array<{ id: ModuleId; label: string; icon: typeof LayoutDashboard }> = [
  { id: "thesis", label: "Resultados", icon: Trophy },
  { id: "runs", label: "Corridas", icon: Upload },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "detections", label: "Detecciones", icon: Layers3 },
  { id: "instruments", label: "Instrumentos", icon: ClipboardList },
  { id: "dataset", label: "Dataset", icon: Database },
  { id: "labeling", label: "Etiquetado", icon: ScanLine },
  { id: "audit", label: "Auditoria", icon: ShieldCheck },
  { id: "human", label: "Humano", icon: UserRoundCheck },
  { id: "groundTruth", label: "Ground truth", icon: Microscope },
  { id: "models", label: "Modelos IA", icon: Brain },
  { id: "inference", label: "Inferencia", icon: PlayCircle },
  { id: "comparison", label: "Comparacion", icon: GitCompare },
  { id: "reports", label: "Reportes", icon: FileText },
  { id: "config", label: "Configuracion", icon: Settings2 },
]

function classLabel(value: string) {
  return CLASS_LABELS[value as keyof typeof CLASS_LABELS] ?? value
}

function pct(value: number) {
  return `${Math.round(value * 1000) / 10}%`
}

function decimal(value: number) {
  return Number.isFinite(value) ? value.toFixed(3) : "0.000"
}

function seconds(value: number) {
  return `${value.toFixed(3)} s`
}

function statusVariant(status: string) {
  if (status.includes("soportada") || status.includes("sustancial") || status === "ejecutada") {
    return "default" as const
  }
  if (status.includes("rechazada")) {
    return "destructive" as const
  }
  return "warning" as const
}

function Sidebar() {
  const activeModule = useAppStore((state) => state.activeModule)
  const setActiveModule = useAppStore((state) => state.setActiveModule)

  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-20 border-r bg-background/95 p-3 backdrop-blur md:flex md:flex-col">
      <div className="mb-4 flex h-11 items-center justify-center rounded-lg border bg-card">
        <BadgeCheck className="h-5 w-5 text-primary" />
      </div>
      <nav className="flex flex-1 flex-col gap-2">
        {navigation.map((item) => {
          const Icon = item.icon
          return (
            <Tooltip key={item.id}>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant={activeModule === item.id ? "secondary" : "ghost"}
                  size="icon"
                  aria-label={item.label}
                  onClick={() => setActiveModule(item.id)}
                >
                  <Icon className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">{item.label}</TooltipContent>
            </Tooltip>
          )
        })}
      </nav>
    </aside>
  )
}

function MobileNav() {
  const activeModule = useAppStore((state) => state.activeModule)
  const setActiveModule = useAppStore((state) => state.setActiveModule)

  return (
    <div className="sticky top-0 z-20 border-b bg-background/95 p-3 backdrop-blur md:hidden">
      <div className="flex gap-2 overflow-x-auto">
        {navigation.map((item) => (
          <Button
            key={item.id}
            type="button"
            variant={activeModule === item.id ? "secondary" : "outline"}
            size="sm"
            onClick={() => setActiveModule(item.id)}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Button>
        ))}
      </div>
    </div>
  )
}

function Header({ dashboard }: { dashboard?: Dashboard }) {
  const activeModule = useAppStore((state) => state.activeModule)
  const current = navigation.find((item) => item.id === activeModule) ?? navigation[0]

  return (
    <header className="flex flex-col gap-4 border-b px-5 py-4 md:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">
            Cooperativa Agraria Sumaq Agro Ecologico Cusco - Casaec - CODEX STAN 39-1981
          </p>
          <h1 className="mt-1 text-2xl font-semibold">{current.label}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={dashboard?.methodology.metodologia_locked ? "default" : "warning"}>
            {dashboard?.methodology.metodologia_locked ? "Metodologia cerrada" : "Metodologia abierta"}
          </Badge>
          <Badge variant={dashboard?.methodology.test_locked ? "default" : "destructive"}>
            {dashboard?.methodology.test_locked ? "Test bloqueado" : "Test abierto"}
          </Badge>
          <Badge variant={dashboard?.methodology.ground_truth_ready ? "default" : "outline"}>
            Ground truth {dashboard?.methodology.ground_truth_ready ? "completo" : "pendiente"}
          </Badge>
        </div>
      </div>
    </header>
  )
}

const detectionPalette: Record<string, string> = {
  danado: "#f97316",
  carbonizado: "#ef4444",
  aplastado: "#eab308",
  larvas: "#22c55e",
  impureza_vegetal: "#14b8a6",
  impureza_mineral: "#38bdf8",
  pie_desprendido: "#a78bfa",
  contaminante: "#fb7185",
  pluma: "#f8fafc",
}

function SpecialistOverlay({ image }: { image?: SpecialistImage }) {
  if (!image) {
    return (
      <div className="flex aspect-[16/10] items-center justify-center rounded-lg border bg-muted/30 text-sm text-muted-foreground">
        Sin imagen seleccionada
      </div>
    )
  }

  const focus = image.detections[0]?.bbox
  const focusX = focus ? ((focus.x_min + focus.x_max) / 2) * 100 : 50
  const focusY = focus ? ((focus.y_min + focus.y_max) / 2) * 100 : 50
  const zoom = focus ? Math.min(10, Math.max(3, 0.36 / Math.max(focus.width, focus.height))) : 3
  const zoomStyle = {
    transformOrigin: `${focusX}% ${focusY}%`,
    transform: `scale(${zoom})`,
  }
  const isPortrait = image.height > image.width
  const canvasStyle: CSSProperties = {
    aspectRatio: `${image.width} / ${image.height}`,
    ...(isPortrait
      ? { height: "min(72vh, 720px)", width: "auto", maxWidth: "100%" }
      : { width: "100%" }),
  }

  const renderPolygonLayer = (showLabels = true) => image.detections.map((detection, index) => {
    const color = detectionPalette[detection.class_name] ?? "#facc15"
    const points = detection.points.map((point) => `${point.x * 100},${point.y * 100}`).join(" ")
    const labelX = detection.bbox.x_min * 100
    const labelY = Math.max(4, detection.bbox.y_min * 100 - 1)
    return (
      <g key={`${detection.class_name}-${index}`}>
        <polygon points={points} fill={`${color}33`} stroke={color} strokeWidth="0.45" vectorEffect="non-scaling-stroke" />
        {showLabels ? (
          <>
            <rect
              x={labelX}
              y={labelY - 3}
              width={Math.min(28, Math.max(10, detection.class_display.length * 1.3))}
              height="3.8"
              fill="rgba(0,0,0,0.72)"
              rx="0.8"
            />
            <text x={labelX + 0.8} y={labelY - 0.5} fill={color} fontSize="2.6" fontWeight="700">
              {detection.class_display}
            </text>
          </>
        ) : null}
      </g>
    )
  })

  return (
    <div className="relative mx-auto overflow-hidden rounded-lg border bg-muted/30" style={canvasStyle}>
      <img
        src={image.url}
        alt={image.file}
        className="absolute inset-0 h-full w-full object-fill"
        loading="eager"
      />
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
        {renderPolygonLayer()}
      </svg>
      <div className="absolute left-3 top-3 rounded-md border bg-background/90 px-2 py-1 text-xs font-mono">
        {image.file}
      </div>
      {focus ? (
        <div className="absolute right-3 top-3 hidden h-40 w-64 overflow-hidden rounded-md border bg-background/85 shadow-lg lg:block">
          <div className="relative h-full w-full">
            <img src={image.url} alt="" className="absolute inset-0 h-full w-full object-contain" style={zoomStyle} />
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full" style={zoomStyle}>
              {renderPolygonLayer(false)}
            </svg>
          </div>
          <div className="absolute bottom-2 left-2 rounded border bg-background/90 px-2 py-0.5 text-xs">
            Zoom deteccion principal
          </div>
        </div>
      ) : null}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-2">
        <Badge variant="secondary">{image.split}</Badge>
        <Badge variant="warning">{image.detections_count} detecciones</Badge>
        <Badge>{image.primary_display}</Badge>
      </div>
    </div>
  )
}

function ThesisResultsPage({
  data,
  specialist,
  runs,
  selectedRunId,
  onRunChange,
}: {
  data?: ThesisRun
  specialist?: SpecialistDetectionsResponse
  runs: ThesisRunSummary[]
  selectedRunId?: string
  onRunChange: (runId: string) => void
}) {
  const [selectedCaseCode, setSelectedCaseCode] = useState<string | undefined>(undefined)
  const setActiveModule = useAppStore((state) => state.setActiveModule)
  const cases = data?.cases ?? []
  const selectedCase = cases.find((item) => item.codigo_imagen === selectedCaseCode) ?? cases[0]
  const overlayImage = specialist?.images.find((image) => image.codigo_imagen === selectedCase?.codigo_imagen)

  if (!data) {
    return (
      <Alert>
        <AlertTitle>Resultados cargando</AlertTitle>
        <AlertDescription>La corrida de validacion aun no devolvio datos.</AlertDescription>
      </Alert>
    )
  }

  const mcnemar = data.metrics.mcnemar
  const topHumanErrors = data.errors.human_by_class.slice(0, 5)
  const topModelErrors = data.errors.model_by_class.slice(0, 5)

  return (
    <div className="space-y-5">
      <Card className="border-primary/35 bg-card/95">
        <CardHeader className="flex-row items-start justify-between gap-4">
          <div className="max-w-5xl">
            <div className="mb-3 flex flex-wrap gap-2">
              <Badge variant="default">Prueba ya corrida</Badge>
              <Badge variant={statusVariant(data.run.status)}>{data.run.status}</Badge>
              <Badge variant="secondary">{data.run.executed_at}</Badge>
            </div>
            <CardTitle className="text-2xl">Validacion YOLOv11n vs humano contra ground truth especialista</CardTitle>
            <CardDescription className="mt-2 text-sm leading-6">
              {data.run.cooperative} - {data.run.data_origin}
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={selectedRunId ?? data.run.id}
              onChange={(event) => onRunChange(event.target.value)}
              aria-label="Seleccionar corrida"
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.name} - {run.evaluated_images} img
                </option>
              ))}
            </select>
            <Button type="button" variant="outline" onClick={() => setActiveModule("runs")}>
              <Upload className="h-4 w-4" />
              Nueva corrida
            </Button>
            <Button type="button" onClick={() => window.open(apiUrl(data.downloads.thesis_results), "_blank")}>
              <FileSpreadsheet className="h-4 w-4" />
              Excel impecable
            </Button>
            <Button type="button" variant="outline" onClick={() => window.open(apiUrl(data.downloads.thesis_word), "_blank")}>
              <FileText className="h-4 w-4" />
              Word sustentacion
            </Button>
            <Button type="button" variant="outline" onClick={() => window.open(apiUrl(data.downloads.instruments), "_blank")}>
              <Download className="h-4 w-4" />
              Instrumentos
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-lg border border-primary/20 bg-primary/10 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-primary">
              <Trophy className="h-4 w-4" />
              Veredicto metodologico
            </div>
            <p className="text-lg font-semibold leading-7">{data.run.verdict}</p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              La comparacion usa las mismas {data.dataset.evaluated_images} imagenes etiquetadas por especialistas,
              con tabla pareada humano/IA y tiempos por imagen.
            </p>
          </div>
          <div className="rounded-lg border p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <Target className="h-4 w-4 text-accent" />
              Cadena de evidencia ejecutada
            </div>
            <div className="grid gap-2 text-sm">
              {[
                "Imagen estandarizada",
                "Ground truth especialista NDJSON",
                "Evaluacion humana pareada",
                "Inferencia YOLOv11n",
                "McNemar, kappa, F1, mAP y tiempos",
                "Excel defendible para anexos",
              ].map((step) => (
                <div key={step} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid metric-grid gap-4">
        <MetricCard label="Imagenes evaluadas" value={`${data.dataset.evaluated_images}/${data.dataset.total_images}`} icon={Images} />
        <MetricCard label="Detecciones especialista" value={data.dataset.total_detections} icon={ShieldCheck} />
        <MetricCard label="Accuracy modelo" value={pct(data.metrics.accuracy_modelo)} icon={Brain} />
        <MetricCard label="Accuracy humano" value={pct(data.metrics.accuracy_humano)} icon={UserRoundCheck} />
        <MetricCard label="McNemar p" value={decimal(mcnemar.p_value)} icon={BarChart3} />
        <MetricCard label="Velocidad IA" value={`${data.metrics.tiempos.factor_velocidad.toFixed(1)}x`} icon={Clock3} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
        <Card>
          <CardHeader>
            <CardTitle>Hipotesis contrastadas</CardTitle>
            <CardDescription>Resultado estadistico y tecnico de la corrida funcional.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.hypotheses.map((item) => (
              <div key={item.codigo} className="rounded-lg border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-medium">{item.codigo} - {item.hipotesis}</div>
                  <Badge variant={statusVariant(item.estado)}>{item.estado.replaceAll("_", " ")}</Badge>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.resultado}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Comparacion pareada</CardTitle>
            <CardDescription>Tabla McNemar sobre aciertos frente al especialista.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-md border p-3">
                <div className="text-muted-foreground">Ambos correctos</div>
                <div className="mt-1 text-2xl font-semibold">{mcnemar.a}</div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-muted-foreground">Solo humano</div>
                <div className="mt-1 text-2xl font-semibold">{mcnemar.b}</div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-muted-foreground">Solo modelo</div>
                <div className="mt-1 text-2xl font-semibold">{mcnemar.c}</div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-muted-foreground">Ambos fallan</div>
                <div className="mt-1 text-2xl font-semibold">{mcnemar.d}</div>
              </div>
            </div>
            <Separator />
            <div className="space-y-3">
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Accuracy modelo</span>
                  <span>{pct(data.metrics.accuracy_modelo)}</span>
                </div>
                <Progress value={data.metrics.accuracy_modelo * 100} />
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Accuracy humano</span>
                  <span>{pct(data.metrics.accuracy_humano)}</span>
                </div>
                <Progress value={data.metrics.accuracy_humano * 100} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Donde falla cada metodo</CardTitle>
            <CardDescription>Errores agrupados por clase real del especialista.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <div className="flex items-center gap-2 font-medium">
                <UserRoundCheck className="h-4 w-4 text-accent" />
                Humano: {data.errors.human_total} errores
              </div>
              {topHumanErrors.map((item) => (
                <div key={item.class_name} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>{item.class_display}</span>
                    <span>{item.errores}</span>
                  </div>
                  <Progress value={item.participacion * 100} />
                </div>
              ))}
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2 font-medium">
                <Brain className="h-4 w-4 text-primary" />
                Modelo: {data.errors.model_total} errores
              </div>
              {topModelErrors.map((item) => (
                <div key={item.class_name} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>{item.class_display}</span>
                    <span>{item.errores}</span>
                  </div>
                  <Progress value={item.participacion * 100} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Desempeno por clase</CardTitle>
            <CardDescription>F1 del modelo y del humano por clase CODEX/proxy visual.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Clase</TableHead>
                  <TableHead>Soporte</TableHead>
                  <TableHead>F1 modelo</TableHead>
                  <TableHead>F1 humano</TableHead>
                  <TableHead>Recall modelo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.per_class.map((row) => (
                  <TableRow key={row.class_name}>
                    <TableCell>{row.class_display}</TableCell>
                    <TableCell>{row.support}</TableCell>
                    <TableCell>{pct(row.model_f1)}</TableCell>
                    <TableCell>{pct(row.human_f1)}</TableCell>
                    <TableCell>{pct(row.model_recall)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-4">
            <div>
              <CardTitle>Caso visual de la corrida</CardTitle>
              <CardDescription>Ejemplo real del NDJSON con resultado humano/modelo.</CardDescription>
            </div>
            <Button type="button" variant="outline" onClick={() => setActiveModule("detections")}>
              <Images className="h-4 w-4" />
              Ver detecciones
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {overlayImage ? (
              <SpecialistOverlay image={overlayImage} />
            ) : selectedCase ? (
              <div className="relative overflow-hidden rounded-lg border bg-muted/30">
                <img src={selectedCase.url} alt={selectedCase.archivo_imagen} className="max-h-[520px] w-full object-contain" />
              </div>
            ) : null}
            {selectedCase ? (
              <div className="grid gap-3 text-sm md:grid-cols-4">
                <div className="rounded-md border p-3">
                  <div className="text-muted-foreground">Ground truth</div>
                  <div className="mt-1 font-medium">{classLabel(selectedCase.ground_truth)}</div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="text-muted-foreground">Humano</div>
                  <div className="mt-1 flex items-center gap-2 font-medium">
                    {selectedCase.humano === selectedCase.ground_truth ? <CheckCircle2 className="h-4 w-4 text-primary" /> : <XCircle className="h-4 w-4 text-destructive" />}
                    {classLabel(selectedCase.humano)}
                  </div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="text-muted-foreground">Modelo</div>
                  <div className="mt-1 flex items-center gap-2 font-medium">
                    {selectedCase.ia === selectedCase.ground_truth ? <CheckCircle2 className="h-4 w-4 text-primary" /> : <XCircle className="h-4 w-4 text-destructive" />}
                    {classLabel(selectedCase.ia)}
                  </div>
                </div>
                <div className="rounded-md border p-3">
                  <div className="text-muted-foreground">Tiempo IA</div>
                  <div className="mt-1 font-medium">{seconds(selectedCase.tiempo_ia_ms / 1000)}</div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Casos de evidencia</CardTitle>
              <CardDescription>Fallas humanas, fallas del modelo y coincidencias.</CardDescription>
            </CardHeader>
            <CardContent className="max-h-[650px] space-y-2 overflow-auto">
              {cases.map((item) => (
                <Button
                  key={item.codigo_imagen}
                  type="button"
                  variant={selectedCase?.codigo_imagen === item.codigo_imagen ? "secondary" : "ghost"}
                  className="h-auto w-full justify-start px-2 py-2"
                  onClick={() => setSelectedCaseCode(item.codigo_imagen)}
                >
                  <div className="min-w-0 text-left">
                    <div className="truncate font-mono text-xs">{item.archivo_imagen}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{item.hallazgo}</div>
                  </div>
                </Button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Preguntas respondidas</CardTitle>
              <CardDescription>Lectura directa para el capitulo de resultados.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.questions.map((item) => (
                <div key={item.pregunta} className="rounded-md border p-3 text-sm">
                  <div className="font-medium">{item.pregunta}</div>
                  <div className="mt-1 leading-5 text-muted-foreground">{item.respuesta}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      <Alert className="border-accent/50">
        <AlertTriangle className="h-4 w-4 text-accent" />
        <AlertTitle>Limite CODEX declarado</AlertTitle>
        <AlertDescription>
          La vision artificial se reporta como proxy visual: no mide humedad, residuo insoluble en acido,
          masa m/m ni microbiologia desde una imagen RGB.
        </AlertDescription>
      </Alert>
    </div>
  )
}

function RunsPage({ runs }: { runs: ThesisRunSummary[] }) {
  const [runName, setRunName] = useState("Corrida nueva Casaec")
  const [modelVersion, setModelVersion] = useState("YOLOv11n-CODEX-CASAEC-demo-reproducible")
  const [expertFile, setExpertFile] = useState<File | null>(null)
  const [imagesFile, setImagesFile] = useState<File | null>(null)
  const setActiveModule = useAppStore((state) => state.setActiveModule)
  const setActiveRunId = useAppStore((state) => state.setActiveRunId)
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!expertFile) {
        throw new Error("Sube un Excel, CSV o NDJSON con resultados expertos.")
      }
      const formData = new FormData()
      formData.append("run_name", runName)
      formData.append("model_version", modelVersion)
      formData.append("expert_file", expertFile)
      if (imagesFile) {
        formData.append("images_file", imagesFile)
      }
      const response = await fetch(apiUrl("/api/thesis-runs/upload"), {
        method: "POST",
        body: formData,
      })
      if (!response.ok) {
        throw new Error(await response.text())
      }
      return response.json() as Promise<ThesisRun>
    },
    onSuccess: async (payload) => {
      setActiveRunId(payload.run.id)
      await queryClient.invalidateQueries({ queryKey: ["thesisRuns"] })
      await queryClient.invalidateQueries({ queryKey: ["thesisRun"] })
      setActiveModule("thesis")
    },
  })

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
      <Card>
        <CardHeader>
          <CardTitle>Crear nueva corrida de validacion</CardTitle>
          <CardDescription>
            Carga las imagenes y la referencia experta para comparar el modelo contra el ground truth de esa corrida.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label>Nombre de corrida</Label>
            <Input value={runName} onChange={(event) => setRunName(event.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label>Version del modelo</Label>
            <Input value={modelVersion} onChange={(event) => setModelVersion(event.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label>Resultados expertos / ground truth</Label>
            <Input
              type="file"
              accept=".xlsx,.xls,.csv,.ndjson"
              onChange={(event) => setExpertFile(event.target.files?.[0] ?? null)}
            />
            <p className="text-xs leading-5 text-muted-foreground">
              Columnas aceptadas: codigo_imagen, clase_principal_real o ground_truth; opcional humano, ia,
              tiempo_segundos y tiempo_inferencia_ms.
            </p>
          </div>
          <div className="grid gap-2">
            <Label>Imagenes de la corrida</Label>
            <Input type="file" accept=".zip,.ndjson" onChange={(event) => setImagesFile(event.target.files?.[0] ?? null)} />
            <p className="text-xs leading-5 text-muted-foreground">
              Puedes adjuntar un ZIP de imagenes o un NDJSON con URLs. Si solo subes Excel, igual se calculan metricas y exportes.
            </p>
          </div>
          {uploadMutation.isError ? (
            <Alert className="border-destructive/50">
              <AlertTitle>No se pudo crear la corrida</AlertTitle>
              <AlertDescription>{String(uploadMutation.error.message)}</AlertDescription>
            </Alert>
          ) : null}
          <Button type="button" onClick={() => uploadMutation.mutate()} disabled={uploadMutation.isPending}>
            <Upload className="h-4 w-4" />
            {uploadMutation.isPending ? "Procesando..." : "Procesar corrida"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Corridas disponibles</CardTitle>
          <CardDescription>Cada respuesta de tesis debe salir de una corrida seleccionada.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {runs.map((run) => (
            <button
              key={run.id}
              type="button"
              className="w-full rounded-lg border p-3 text-left hover:bg-secondary/60"
              onClick={() => {
                setActiveRunId(run.id)
                setActiveModule("thesis")
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{run.name}</span>
                <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <span>{run.evaluated_images} imagenes</span>
                <span>Modelo {pct(run.accuracy_modelo)}</span>
                <span>Humano {pct(run.accuracy_humano)}</span>
                <span>p {decimal(run.mcnemar_p)}</span>
              </div>
            </button>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function SpecialistDetectionsPage({ data }: { data?: SpecialistDetectionsResponse }) {
  const [selectedCode, setSelectedCode] = useState<string | undefined>(undefined)
  const images = data?.images ?? []
  const selected = images.find((image) => image.codigo_imagen === selectedCode) ?? images[0]
  const distribution = Object.entries(data?.summary.class_distribution ?? {}).sort((a, b) => b[1] - a[1])

  return (
    <div className="space-y-4">
      <div className="grid metric-grid gap-4">
        <MetricCard label="Imagenes NDJSON" value={data?.summary.total_images ?? 0} icon={Images} />
        <MetricCard label="Etiquetadas por especialistas" value={data?.summary.annotated_images ?? 0} icon={ShieldCheck} />
        <MetricCard label="Pendientes sin etiqueta" value={data?.summary.unlabeled_images ?? 0} icon={AlertTriangle} />
        <MetricCard label="Poligonos detectados" value={data?.summary.total_detections ?? 0} icon={Layers3} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Dataset {data?.dataset.name ?? "hongos-suillus"}</h2>
          <p className="text-sm text-muted-foreground">{data?.cooperative}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={() => window.open(apiUrl("/api/specialist-detections/export-ground-truth-excel"), "_blank")}>
            <Download className="h-4 w-4" />
            Ground truth XLSX
          </Button>
          <Button type="button" onClick={() => window.open(apiUrl("/api/specialist-detections/export-human-excel?evaluators=3"), "_blank")}>
            <FileSpreadsheet className="h-4 w-4" />
            Excel humano
          </Button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Ejemplos etiquetados</CardTitle>
            <CardDescription>Primeros ejemplos con poligonos del NDJSON.</CardDescription>
          </CardHeader>
          <CardContent className="max-h-[650px] space-y-2 overflow-auto">
            {images.map((image) => (
              <Button
                key={image.codigo_imagen}
                type="button"
                variant={selected?.codigo_imagen === image.codigo_imagen ? "secondary" : "ghost"}
                className="h-auto w-full justify-start px-2 py-2"
                onClick={() => setSelectedCode(image.codigo_imagen)}
              >
                <div className="min-w-0 text-left">
                  <div className="truncate font-mono text-xs">{image.file}</div>
                  <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                    <span>{image.primary_display}</span>
                    <span>{image.detections_count} det.</span>
                  </div>
                </div>
              </Button>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <SpecialistOverlay image={selected} />
          <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
            <Card>
              <CardHeader>
                <CardTitle>Detecciones del especialista</CardTitle>
                <CardDescription>Poligonos normalizados convertidos desde `annotations.segments`.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Clase</TableHead>
                      <TableHead>BBox normalizada</TableHead>
                      <TableHead>Puntos</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(selected?.detections ?? []).map((detection, index) => (
                      <TableRow key={`${detection.class_name}-${index}`}>
                        <TableCell>
                          <span className="inline-flex items-center gap-2">
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{ backgroundColor: detectionPalette[detection.class_name] ?? "#facc15" }}
                            />
                            {detection.class_display}
                          </span>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {detection.bbox.x_min.toFixed(3)}, {detection.bbox.y_min.toFixed(3)},{" "}
                          {detection.bbox.width.toFixed(3)}, {detection.bbox.height.toFixed(3)}
                        </TableCell>
                        <TableCell>{detection.points.length}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Distribucion</CardTitle>
                <CardDescription>Conteo de poligonos por clase especialista.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {distribution.map(([className, count]) => (
                  <div key={className} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{classLabel(className)}</span>
                      <span>{count}</span>
                    </div>
                    <Progress value={(count / Math.max(data?.summary.total_detections ?? 1, 1)) * 100} />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

function InstrumentsPage({ data }: { data?: InstrumentsResponse }) {
  const instruments = data?.instruments ?? []
  const ready = instruments.filter((instrument) => instrument.status === "listo").length

  return (
    <div className="space-y-5">
      <div className="grid metric-grid gap-4">
        <MetricCard label="Instrumentos de tesis" value={instruments.length} icon={ClipboardList} />
        <MetricCard label="Listos" value={ready} icon={BadgeCheck} />
        <MetricCard label="Parciales" value={instruments.filter((item) => item.status === "parcial").length} icon={AlertTriangle} />
        <MetricCard label="Pendientes" value={instruments.filter((item) => item.status === "pendiente").length} icon={FileText} />
      </div>

      <Card>
        <CardHeader className="flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Paquete de instrumentos de validacion</CardTitle>
            <CardDescription>
              Descarga I1-I10 con estado metodologico, trazabilidad objetivo-instrumento-resultado y plantillas.
            </CardDescription>
          </div>
          <Button type="button" onClick={() => window.open(apiUrl("/api/instruments/export-all"), "_blank")}>
            <Download className="h-4 w-4" />
            Descargar todo XLSX
          </Button>
        </CardHeader>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader>
            <CardTitle>Instrumentos I1-I10</CardTitle>
            <CardDescription>Cada instrumento indica que valida, que no valida y que evidencia produce.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Codigo</TableHead>
                  <TableHead>Instrumento</TableHead>
                  <TableHead>Valida</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Descarga</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {instruments.map((instrument) => (
                  <TableRow key={instrument.code}>
                    <TableCell className="font-mono text-xs">{instrument.code}</TableCell>
                    <TableCell>
                      <div className="font-medium">{instrument.name}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{instrument.purpose}</div>
                    </TableCell>
                    <TableCell className="max-w-sm text-sm">{instrument.validates}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          instrument.status === "listo"
                            ? "default"
                            : instrument.status === "parcial"
                              ? "warning"
                              : "destructive"
                        }
                      >
                        {instrument.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button type="button" size="sm" variant="outline" onClick={() => window.open(apiUrl(instrument.download), "_blank")}>
                        <Download className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Estado de validacion</CardTitle>
              <CardDescription>Bloqueos y evidencias segun el documento de afinamiento.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {(data?.validation_state ?? []).map((item) => (
                <Alert key={item.item} className={item.block_if_missing ? "border-accent/40" : ""}>
                  <AlertTitle className="flex items-center justify-between gap-2">
                    <span>{item.item}</span>
                    <Badge
                      variant={
                        item.status === "listo" ? "default" : item.status === "parcial" ? "warning" : "destructive"
                      }
                    >
                      {item.status}
                    </Badge>
                  </AlertTitle>
                  <AlertDescription>{item.evidence}</AlertDescription>
                </Alert>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Trazabilidad</CardTitle>
              <CardDescription>Objetivo, instrumento, salida, metrica y captura sugerida.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {(data?.traceability ?? []).map((row) => (
                <div key={row.objetivo} className="rounded-md border p-3 text-sm">
                  <div className="font-medium">{row.objetivo}</div>
                  <div className="mt-2 text-muted-foreground">{row.instrumento} - {row.metrica}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{row.captura_sugerida}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: typeof Images }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3 space-y-0 pb-2">
        <CardDescription>{label}</CardDescription>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
      </CardContent>
    </Card>
  )
}

function DashboardPage({ dashboard, comparison }: { dashboard?: Dashboard; comparison?: Comparison }) {
  const summary = dashboard?.summary ?? {}
  const gtProgress =
    Number(summary.ground_truth_completo ?? 0) && Number(summary.imagenes_totales ?? 1)
      ? (Number(summary.ground_truth_completo) / Number(summary.imagenes_totales)) * 100
      : 0

  return (
    <div className="space-y-6">
      <div className="grid metric-grid gap-4">
        <MetricCard label="Imagenes totales" value={Number(summary.imagenes_totales ?? 0)} icon={Images} />
        <MetricCard label="Etiquetas YOLO" value={Number(summary.etiquetas_totales ?? 0)} icon={ScanLine} />
        <MetricCard label="Auditadas" value={Number(summary.imagenes_auditadas ?? 0)} icon={ShieldCheck} />
        <MetricCard label="Ground truth" value={Number(summary.ground_truth_completo ?? 0)} icon={Microscope} />
        <MetricCard label="Evaluaciones" value={Number(summary.evaluaciones_humanas ?? 0)} icon={UserRoundCheck} />
        <MetricCard label="Inferencias" value={Number(summary.inferencias_realizadas ?? 0)} icon={Brain} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>Estado metodologico</CardTitle>
            <CardDescription>Dataset, verdad auditada, evaluacion humana e inferencia pareada.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Ground truth auditado</span>
                <span>{Math.round(gtProgress)}%</span>
              </div>
              <Progress value={gtProgress} />
            </div>
            {comparison ? (
              <div className="grid gap-3 sm:grid-cols-4">
                <MetricCard label="Accuracy humano" value={pct(comparison.metrics.accuracy_humano)} icon={UserRoundCheck} />
                <MetricCard label="Accuracy IA" value={pct(comparison.metrics.accuracy_modelo)} icon={Brain} />
                <MetricCard label="Kappa IA" value={decimal(comparison.metrics.kappa_modelo)} icon={BarChart3} />
                <MetricCard label="Factor velocidad" value={`${comparison.metrics.tiempos.factor_velocidad.toFixed(1)}x`} icon={PlayCircle} />
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Alertas</CardTitle>
            <CardDescription>Controles que evitan sesgos en la tesis.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(dashboard?.alerts ?? []).map((alert) => (
              <Alert key={alert.code} className={alert.severity === "error" ? "border-destructive/50" : ""}>
                <AlertTriangle className="mb-2 h-4 w-4 text-accent" />
                <AlertTitle>{alert.code}</AlertTitle>
                <AlertDescription>{alert.message}</AlertDescription>
              </Alert>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function DatasetPage({ images }: { images: ImageItem[] }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <Button type="button">
            <Upload className="h-4 w-4" />
            Imagenes
          </Button>
          <Button type="button" variant="outline">
            <Lock className="h-4 w-4" />
            Bloquear test
          </Button>
        </div>
        <Input className="max-w-xs" placeholder="Buscar codigo de imagen" />
      </div>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Imagen</TableHead>
                <TableHead>Lote</TableHead>
                <TableHead>Split</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Etiquetas</TableHead>
                <TableHead>Ground truth</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {images.map((image) => (
                <TableRow key={image.id}>
                  <TableCell className="font-mono text-xs">{image.codigo_imagen}</TableCell>
                  <TableCell>{image.codigo_lote}</TableCell>
                  <TableCell>
                    <Badge variant={image.split_dataset === "test" ? "warning" : "secondary"}>{image.split_dataset}</Badge>
                  </TableCell>
                  <TableCell>{image.estado_auditoria}</TableCell>
                  <TableCell>{image.labels_count}</TableCell>
                  <TableCell>
                    <Badge variant={image.has_ground_truth ? "default" : "outline"}>
                      {image.has_ground_truth ? "si" : "no"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function AnnotationPreview({ image, labels }: { image?: ImageItem; labels: LabelItem[] }) {
  return (
    <div className="relative overflow-hidden rounded-lg border bg-muted/30">
      <svg viewBox="0 0 100 64" className="aspect-[16/10] w-full">
        <defs>
          <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.24" />
          </filter>
        </defs>
        <rect width="100" height="64" fill="oklch(0.23 0.01 110)" />
        <ellipse cx="48" cy="33" rx="31" ry="17" fill="oklch(0.77 0.07 77)" filter="url(#softShadow)" />
        <ellipse cx="40" cy="29" rx="12" ry="6" fill="oklch(0.62 0.08 70)" opacity="0.55" />
        <circle cx="60" cy="34" r="3.2" fill="oklch(0.20 0.03 55)" />
        <circle cx="66" cy="38" r="2.4" fill="oklch(0.20 0.03 55)" />
        <path d="M32 43 C45 50, 58 50, 70 43" stroke="oklch(0.55 0.07 80)" strokeWidth="3" fill="none" />
        {labels.map((label) => {
          const x = (label.x_center - label.width / 2) * 100
          const y = (label.y_center - label.height / 2) * 64
          const width = label.width * 100
          const height = label.height * 64
          return (
            <g key={label.id}>
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill="none"
                stroke="oklch(0.79 0.12 82)"
                strokeWidth="0.8"
              />
              <text x={x} y={Math.max(y - 1.5, 5)} fill="oklch(0.95 0.02 80)" fontSize="3.5">
                {classLabel(label.class_name)}
              </text>
            </g>
          )
        })}
      </svg>
      <div className="absolute left-3 top-3 rounded-md border bg-background/85 px-2 py-1 text-xs font-mono">
        {image?.codigo_imagen ?? "sin imagen"}
      </div>
    </div>
  )
}

function LabelingPage({ images }: { images: ImageItem[] }) {
  const [selectedId, setSelectedId] = useState(images[0]?.id ?? 1)
  const selected = images.find((image) => image.id === selectedId)
  const labelsQuery = useQuery({
    queryKey: ["labels", selectedId],
    queryFn: () => api<LabelItem[]>(`/api/images/${selectedId}/labels`),
    enabled: Boolean(selectedId),
  })
  const labels = labelsQuery.data ?? []

  return (
    <div className="grid gap-4 lg:data-grid">
      <Card>
        <CardHeader>
          <CardTitle>Imagenes</CardTitle>
          <CardDescription>Revision de cajas YOLO y estados de auditoria.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {images.map((image) => (
            <Button
              key={image.id}
              type="button"
              variant={image.id === selectedId ? "secondary" : "ghost"}
              className="w-full justify-start font-mono text-xs"
              onClick={() => setSelectedId(image.id)}
            >
              {image.codigo_imagen}
            </Button>
          ))}
        </CardContent>
      </Card>
      <div className="space-y-4">
        <AnnotationPreview image={selected} labels={labels} />
        <Card>
          <CardHeader>
            <CardTitle>Etiquetas</CardTitle>
            <CardDescription>Validacion de clase y coordenadas normalizadas.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Clase</TableHead>
                  <TableHead>Fuente</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>YOLO</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {labels.map((label) => (
                  <TableRow key={label.id}>
                    <TableCell>{classLabel(label.class_name)}</TableCell>
                    <TableCell>{label.fuente}</TableCell>
                    <TableCell>
                      <Badge variant={label.estado === "auditada" ? "default" : "warning"}>{label.estado}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {label.class_id} {label.x_center.toFixed(3)} {label.y_center.toFixed(3)} {label.width.toFixed(3)}{" "}
                      {label.height.toFixed(3)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function HumanPage({ evaluations }: { evaluations: HumanEvaluation[] }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button type="button">
          <FileSpreadsheet className="h-4 w-4" />
          Importar Excel
        </Button>
        <Button type="button" variant="outline">
          <BarChart3 className="h-4 w-4" />
          Kappa evaluadores
        </Button>
      </div>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Imagen</TableHead>
                <TableHead>Evaluador</TableHead>
                <TableHead>Clase humana</TableHead>
                <TableHead>Decision</TableHead>
                <TableHead>Tiempo</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {evaluations.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="font-mono text-xs">{row.codigo_imagen}</TableCell>
                  <TableCell>{row.evaluador}</TableCell>
                  <TableCell>{classLabel(row.etiqueta_final_humana)}</TableCell>
                  <TableCell>{row.decision_humana}</TableCell>
                  <TableCell>{row.tiempo_segundos.toFixed(2)} s</TableCell>
                  <TableCell>
                    <Badge variant="outline">{row.estado}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function GroundTruthPage({ groundTruth }: { groundTruth: GroundTruth[] }) {
  return (
    <Tabs defaultValue="blind">
      <TabsList>
        <TabsTrigger value="blind">Modo ciego</TabsTrigger>
        <TabsTrigger value="table">Tabla auditada</TabsTrigger>
      </TabsList>
      <TabsContent value="blind">
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <AnnotationPreview image={undefined} labels={[]} />
          <Card>
            <CardHeader>
              <CardTitle>Registro CODEX</CardTitle>
              <CardDescription>Verdad de referencia separada de humano e IA.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-2">
                <Label>Clase principal real</Label>
                <Input defaultValue="larvas" />
              </div>
              <div className="grid gap-2">
                <Label>Decision real</Label>
                <Input defaultValue="observado" />
              </div>
              <div className="grid gap-2">
                <Label>Observacion</Label>
                <Textarea defaultValue="Agujeros visibles compatibles con dano por larvas." />
              </div>
              <Button type="button">
                <Save className="h-4 w-4" />
                Guardar
              </Button>
            </CardContent>
          </Card>
        </div>
      </TabsContent>
      <TabsContent value="table">
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Imagen</TableHead>
                  <TableHead>Clase real</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Auditor</TableHead>
                  <TableHead>Confianza</TableHead>
                  <TableHead>Bloqueo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {groundTruth.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="font-mono text-xs">{row.codigo_imagen}</TableCell>
                    <TableCell>{classLabel(row.clase_principal_real)}</TableCell>
                    <TableCell>{row.decision_real}</TableCell>
                    <TableCell>{row.auditor}</TableCell>
                    <TableCell>{row.nivel_confianza}</TableCell>
                    <TableCell>
                      <Badge variant={row.locked ? "default" : "warning"}>{row.locked ? "bloqueado" : "abierto"}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}

function ModelsPage({ models }: { models: ModelItem[] }) {
  return (
    <div className="space-y-4">
      <Button type="button">
        <Brain className="h-4 w-4" />
        Registrar modelo
      </Button>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Version</TableHead>
                <TableHead>Dataset</TableHead>
                <TableHead>Epochs</TableHead>
                <TableHead>mAP50</TableHead>
                <TableHead>mAP50-95</TableHead>
                <TableHead>Hash</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {models.map((model) => (
                <TableRow key={model.id}>
                  <TableCell>{model.modelo_version}</TableCell>
                  <TableCell>{model.dataset_version}</TableCell>
                  <TableCell>{model.epochs}</TableCell>
                  <TableCell>{pct(model.map50)}</TableCell>
                  <TableCell>{pct(model.map5095)}</TableCell>
                  <TableCell className="font-mono text-xs">{model.model_hash_sha256.slice(0, 12)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function InferencePage({ run }: { run?: InferenceRun }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: () =>
      api<InferenceRun>("/api/inference/run", {
        method: "POST",
        body: JSON.stringify({
          modelo_version: "yolov11n_codex_v1",
          confidence_threshold: 0.25,
          iou_threshold: 0.5,
          device: "cpu",
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inference"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["comparison"] })
    },
  })

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Corrida reproducible</CardTitle>
          <CardDescription>Modelo, thresholds, device, run_id y tiempos quedan versionados.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          <div className="grid gap-2 md:col-span-2">
            <Label>Modelo</Label>
            <Input defaultValue="yolov11n_codex_v1" />
          </div>
          <div className="grid gap-2">
            <Label>Confidence</Label>
            <Input defaultValue="0.25" />
          </div>
          <div className="grid gap-2">
            <Label>IoU</Label>
            <Input defaultValue="0.50" />
          </div>
          <div className="flex items-end">
            <Button type="button" className="w-full" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
              <PlayCircle className="h-4 w-4" />
              Ejecutar
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{run?.run_id ?? "Sin corrida"}</CardTitle>
          <CardDescription>
            {run ? `${run.imagenes_procesadas}/${run.total_imagenes} imagenes - ${run.tiempo_promedio_ms.toFixed(2)} ms promedio` : "Ejecuta la inferencia demo."}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Imagen</TableHead>
                <TableHead>Clase modelo</TableHead>
                <TableHead>Decision</TableHead>
                <TableHead>Detecciones</TableHead>
                <TableHead>Tiempo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(run?.results ?? []).map((row) => (
                <TableRow key={row.codigo_imagen}>
                  <TableCell className="font-mono text-xs">{row.codigo_imagen}</TableCell>
                  <TableCell>{classLabel(row.clase_principal_modelo)}</TableCell>
                  <TableCell>{row.decision_modelo}</TableCell>
                  <TableCell>{row.detecciones_total}</TableCell>
                  <TableCell>{row.tiempo_inferencia_ms.toFixed(2)} ms</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function ComparisonPage({ comparison }: { comparison?: Comparison }) {
  if (!comparison) {
    return <Alert><AlertTitle>Comparacion pendiente</AlertTitle><AlertDescription>La API aun no devolvio metricas.</AlertDescription></Alert>
  }

  const mcnemar = comparison.metrics.mcnemar

  return (
    <div className="space-y-4">
      {comparison.warnings.map((warning) => (
        <Alert key={warning} className="border-accent/50">
          <AlertTitle>Advertencia metodologica</AlertTitle>
          <AlertDescription>{warning}</AlertDescription>
        </Alert>
      ))}
      <div className="grid metric-grid gap-4">
        <MetricCard label="Accuracy humano" value={pct(comparison.metrics.accuracy_humano)} icon={UserRoundCheck} />
        <MetricCard label="Accuracy IA" value={pct(comparison.metrics.accuracy_modelo)} icon={Brain} />
        <MetricCard label="McNemar p" value={decimal(mcnemar.p_value)} icon={BarChart3} />
        <MetricCard label="Velocidad IA" value={`${comparison.metrics.tiempos.factor_velocidad.toFixed(1)}x`} icon={PlayCircle} />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Tabla pareada central</CardTitle>
          <CardDescription>Humano e IA se comparan contra el mismo ground truth auditado.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Imagen</TableHead>
                <TableHead>Ground truth</TableHead>
                <TableHead>Humano</TableHead>
                <TableHead>IA</TableHead>
                <TableHead>Humano correcto</TableHead>
                <TableHead>IA correcta</TableHead>
                <TableHead>Tiempo humano</TableHead>
                <TableHead>Tiempo IA</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {comparison.rows.map((row) => (
                <TableRow key={row.codigo_imagen}>
                  <TableCell className="font-mono text-xs">{row.codigo_imagen}</TableCell>
                  <TableCell>{classLabel(row.ground_truth)}</TableCell>
                  <TableCell>{classLabel(row.humano)}</TableCell>
                  <TableCell>{classLabel(row.ia)}</TableCell>
                  <TableCell>
                    <Badge variant={row.humano_correcto ? "default" : "destructive"}>
                      {row.humano_correcto ? "si" : "no"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={row.ia_correcto ? "default" : "destructive"}>{row.ia_correcto ? "si" : "no"}</Badge>
                  </TableCell>
                  <TableCell>{row.tiempo_humano.toFixed(2)} s</TableCell>
                  <TableCell>{(row.tiempo_ia / 1000).toFixed(3)} s</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function AuditPage({ images }: { images: ImageItem[] }) {
  const audited = images.filter((image) => image.estado_auditoria === "auditada").length
  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Filtros</CardTitle>
          <CardDescription>Clase, estado, lote, split y anotador.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input placeholder="Clase o error" />
          <Input placeholder="Lote" />
          <Button type="button" variant="outline" className="w-full">
            Aplicar
          </Button>
          <Separator />
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Auditadas</span>
              <span>{audited}</span>
            </div>
            <Progress value={(audited / Math.max(images.length, 1)) * 100} />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Historial de auditoria</CardTitle>
          <CardDescription>Cada correccion conserva usuario, motivo y valores.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Imagen</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Split</TableHead>
                <TableHead>Control</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {images.map((image) => (
                <TableRow key={image.id}>
                  <TableCell className="font-mono text-xs">{image.codigo_imagen}</TableCell>
                  <TableCell>{image.estado_auditoria}</TableCell>
                  <TableCell>{image.split_dataset}</TableCell>
                  <TableCell>
                    <Button type="button" size="sm" variant="outline">Aprobar</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function ReportsPage() {
  const reports = [
    ["Excel sustentacion corrida base", "/api/thesis-runs/validacion_casaec_ndjson_2026_05_07/export-excel"],
    ["Word sustentacion corrida base", "/api/thesis-runs/validacion_casaec_ndjson_2026_05_07/export-word"],
    ["Instrumentos I1-I10", "/api/instruments/export-all"],
    ["Reporte dataset", "/api/experiments/demo/export?format=dataset"],
    ["Reporte auditoria", "/api/experiments/demo/export?format=audit"],
    ["Reporte humano", "/api/experiments/demo/export?format=human"],
    ["Reporte modelo", "/api/experiments/demo/export?format=model"],
    ["Reporte comparativo", "/api/experiments/demo/export?format=comparison"],
    ["Reporte tesis Markdown", "/api/experiments/demo/export?format=md"],
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {reports.map(([label, href]) => (
        <Card key={label}>
          <CardHeader>
            <CardTitle>{label}</CardTitle>
            <CardDescription>Evidencia reproducible para anexos y resultados.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" variant="outline" className="w-full" onClick={() => window.open(apiUrl(href), "_blank")}>
              <FileText className="h-4 w-4" />
              Exportar
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function ConfigPage({ dashboard }: { dashboard?: Dashboard }) {
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader>
          <CardTitle>Configuracion metodologica</CardTitle>
          <CardDescription>Reglas congelables antes de evaluacion final.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label>Prioridad de clase principal</Label>
            <Textarea defaultValue="impureza_mineral&#10;impureza_vegetal&#10;larvas&#10;carbonizado&#10;danado&#10;aplastado&#10;pie_desprendido&#10;normal" />
          </div>
          <div className="grid gap-2">
            <Label>Reglas CODEX proxy</Label>
            <Textarea defaultValue="normal -> apto&#10;larvas leve -> observado&#10;larvas severo -> no_apto&#10;impurezas visibles -> observado" />
          </div>
          <div className="grid gap-2">
            <Label>Confidence default</Label>
            <Input defaultValue="0.25" />
          </div>
          <div className="grid gap-2">
            <Label>Split train/val/test</Label>
            <Input defaultValue="70/20/10" />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Bloqueos</CardTitle>
          <CardDescription>Ningun reporte final sale con metodologia abierta.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Badge variant={dashboard?.methodology.metodologia_locked ? "default" : "warning"}>
            {dashboard?.methodology.metodologia_locked ? "Metodologia bloqueada" : "Metodologia editable"}
          </Badge>
          <Button type="button" className="w-full">
            <Lock className="h-4 w-4" />
            Cerrar metodologia
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export function App() {
  const activeModule = useAppStore((state) => state.activeModule)
  const activeRunId = useAppStore((state) => state.activeRunId)
  const setActiveRunId = useAppStore((state) => state.setActiveRunId)
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/api/dashboard") })
  const imagesQuery = useQuery({ queryKey: ["images"], queryFn: () => api<ImageItem[]>("/api/images") })
  const specialistQuery = useQuery({
    queryKey: ["specialistDetections"],
    queryFn: () => api<SpecialistDetectionsResponse>("/api/specialist-detections?limit=80&annotated_only=true"),
  })
  const thesisRunsQuery = useQuery({
    queryKey: ["thesisRuns"],
    queryFn: () => api<ThesisRunSummary[]>("/api/thesis-runs"),
  })
  const runs = thesisRunsQuery.data ?? []
  const selectedRunId = activeRunId ?? runs[0]?.id
  const thesisRunQuery = useQuery({
    queryKey: ["thesisRun", selectedRunId],
    queryFn: () => api<ThesisRun>(`/api/thesis-runs/${selectedRunId}`),
    enabled: Boolean(selectedRunId),
  })
  const instrumentsQuery = useQuery({
    queryKey: ["instruments"],
    queryFn: () => api<InstrumentsResponse>("/api/instruments"),
  })
  const humanQuery = useQuery({
    queryKey: ["human"],
    queryFn: () => api<HumanEvaluation[]>("/api/human-evaluations"),
  })
  const groundTruthQuery = useQuery({
    queryKey: ["groundTruth"],
    queryFn: () => api<GroundTruth[]>("/api/ground-truth"),
  })
  const modelsQuery = useQuery({ queryKey: ["models"], queryFn: () => api<ModelItem[]>("/api/models") })
  const inferenceQuery = useQuery({
    queryKey: ["inference"],
    queryFn: () => api<InferenceRun>("/api/inference/runs/demo_run_001"),
  })
  const comparisonQuery = useQuery({
    queryKey: ["comparison"],
    queryFn: () => api<Comparison>("/api/experiments/compare", { method: "POST", body: JSON.stringify({}) }),
  })

  const images = imagesQuery.data ?? []
  const selectedThesisData = thesisRunQuery.data
  const content = useMemo(() => {
    switch (activeModule) {
      case "thesis":
        return (
          <ThesisResultsPage
            data={selectedThesisData}
            specialist={specialistQuery.data}
            runs={runs}
            selectedRunId={selectedRunId}
            onRunChange={setActiveRunId}
          />
        )
      case "runs":
        return <RunsPage runs={runs} />
      case "detections":
        return <SpecialistDetectionsPage data={specialistQuery.data} />
      case "instruments":
        return <InstrumentsPage data={instrumentsQuery.data} />
      case "dataset":
        return <DatasetPage images={images} />
      case "labeling":
        return <LabelingPage images={images} />
      case "audit":
        return <AuditPage images={images} />
      case "human":
        return <HumanPage evaluations={humanQuery.data ?? []} />
      case "groundTruth":
        return <GroundTruthPage groundTruth={groundTruthQuery.data ?? []} />
      case "models":
        return <ModelsPage models={modelsQuery.data ?? []} />
      case "inference":
        return <InferencePage run={inferenceQuery.data} />
      case "comparison":
        return <ComparisonPage comparison={comparisonQuery.data} />
      case "reports":
        return <ReportsPage />
      case "config":
        return <ConfigPage dashboard={dashboardQuery.data} />
      default:
        return <DashboardPage dashboard={dashboardQuery.data} comparison={comparisonQuery.data} />
    }
  }, [
    activeModule,
    comparisonQuery.data,
    dashboardQuery.data,
    groundTruthQuery.data,
    humanQuery.data,
    images,
    instrumentsQuery.data,
    inferenceQuery.data,
    modelsQuery.data,
    specialistQuery.data,
    runs,
    selectedRunId,
    selectedThesisData,
    setActiveRunId,
  ])

  const isLoading =
    dashboardQuery.isLoading ||
    imagesQuery.isLoading ||
    thesisRunsQuery.isLoading ||
    (Boolean(selectedRunId) && thesisRunQuery.isLoading)

  return (
    <div className="min-h-screen">
      <Sidebar />
      <MobileNav />
      <div className="md:pl-20">
        <Header dashboard={dashboardQuery.data} />
        <main className="px-5 py-5 md:px-8">
          {isLoading ? (
            <Card>
              <CardContent className="p-6 text-sm text-muted-foreground">Cargando datos metodologicos...</CardContent>
            </Card>
          ) : (
            content
          )}
        </main>
      </div>
    </div>
  )
}
