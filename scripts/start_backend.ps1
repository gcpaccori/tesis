$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $Root "backend")
$Port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  python -m venv .venv
}

.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port $Port
