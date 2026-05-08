$ErrorActionPreference = "Stop"

$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519_elsecluster5_continue"
$Remote = "u23u@10.1.1.60"
$LocalPort = 8089
$RemotePort = 8089

$npmPath = Join-Path $env:APPDATA "npm"
if ($env:PATH -notlike "*$npmPath*") {
    $env:PATH = "$npmPath;$env:PATH"
}

if (-not (Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "ssh.exe" -ArgumentList @(
        "-i", $KeyPath,
        "-N",
        "-L", "$LocalPort`:127.0.0.1:$RemotePort",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "StrictHostKeyChecking=no",
        $Remote
    ) -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

$health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$LocalPort/v1/models" -TimeoutSec 15
if ($health.StatusCode -ne 200) {
    throw "Kimi Q4 proxy no responde en http://127.0.0.1:$LocalPort/v1/models"
}

Write-Host "Kimi Q4 listo para OpenCode en http://127.0.0.1:$LocalPort/v1"
Write-Host "Modelo: kimi-local/kimi-k2.6-q4"
opencode . --model kimi-local/kimi-k2.6-q4 --agent build
