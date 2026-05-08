param(
    [int]$LocalPort = 8001,
    [string]$HostName = "10.1.1.60",
    [string]$RemoteUser = "u23u",
    [string]$KeyPath = "$HOME\.ssh\id_ed25519_elsecluster5_continue"
)

$ErrorActionPreference = "Stop"

$sshExe = (Get-Command ssh).Source
if (-not (Test-Path $KeyPath)) {
    throw "No encontre la llave SSH en $KeyPath"
}

$remotePortCommand = "bash /home/u23u/orquesta/bin/get_kimi_port.sh"
$remotePortRaw = & $sshExe -i $KeyPath -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$RemoteUser@$HostName" $remotePortCommand 2>$null | Out-String
$remotePort = $remotePortRaw.Trim()
if (-not $remotePort) {
    throw "No encontre un llama-server activo para Kimi en $HostName. Carga Kimi en Unsloth Studio y vuelve a correr este script."
}

$existing = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq "ssh.exe" -and
        $_.CommandLine -match "-L\s+$LocalPort`:127\.0\.0\.1:" -and
        $_.CommandLine -match [regex]::Escape("$RemoteUser@$HostName")
    }

foreach ($proc in $existing) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

$forwardSpec = "${LocalPort}:127.0.0.1:$remotePort"
$arguments = @(
    "-i", $KeyPath,
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=accept-new",
    "-N",
    "-L", $forwardSpec,
    "$RemoteUser@$HostName"
)

$proc = Start-Process -FilePath $sshExe -ArgumentList $arguments -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 3

try {
    $null = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$LocalPort/v1/models" -TimeoutSec 15
} catch {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    throw "Levante el tunel, pero no pude validar http://127.0.0.1:$LocalPort/v1/models. Error: $($_.Exception.Message)"
}

Write-Host "Tunel Kimi listo en http://127.0.0.1:$LocalPort/v1"
Write-Host "Puerto remoto actual de Kimi: $remotePort"
Write-Host "PID del tunel SSH: $($proc.Id)"
