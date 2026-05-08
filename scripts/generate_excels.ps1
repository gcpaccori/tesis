$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Exports = Join-Path $Root "exports"
New-Item -ItemType Directory -Force -Path $Exports | Out-Null

Set-Location $Backend
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
}

.\.venv\Scripts\python -m pip install -r requirements.txt
$TempScript = Join-Path $Backend "_generate_excels_tmp.py"
@"
import pandas as pd
from pathlib import Path
from app.services.ndjson_dataset import human_rows_from_specialist_labels, ground_truth_rows_from_specialist_labels
from app.services.instruments import export_all_instruments
from app.services.thesis_run import export_thesis_docx, export_thesis_run

exports = Path(r"$Exports")
pd.DataFrame(human_rows_from_specialist_labels(evaluators=3)).to_excel(exports / "evaluacion_humana_simulada_casaec.xlsx", index=False)
pd.DataFrame(ground_truth_rows_from_specialist_labels()).to_excel(exports / "ground_truth_especialistas_casaec.xlsx", index=False)
export_all_instruments(exports / "instrumentos_validacion_tesis_casaec.xlsx")
export_thesis_run(exports / "resultados_validacion_tesis_casaec.xlsx")
export_thesis_docx(exports / "informe_sustentacion_tesis_casaec.docx")
print(exports)
"@ | Set-Content -Encoding UTF8 -LiteralPath $TempScript
.\.venv\Scripts\python $TempScript
Remove-Item -LiteralPath $TempScript -Force
