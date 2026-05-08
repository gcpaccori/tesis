$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $Root "frontend")
$Port = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "5173" }

if (-not (Test-Path ".\node_modules")) {
  npm install
}

node .\node_modules\vite\bin\vite.js --host=127.0.0.1 --port=$Port
