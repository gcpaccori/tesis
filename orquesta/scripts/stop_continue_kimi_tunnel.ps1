param(
    [int]$LocalPort = 8001,
    [string]$HostName = "10.1.1.60",
    [string]$RemoteUser = "u23u"
)

$ErrorActionPreference = "Stop"

$matching = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq "ssh.exe" -and
        $_.CommandLine -match "-L\s+$LocalPort`:127\.0\.0\.1:" -and
        $_.CommandLine -match [regex]::Escape("$RemoteUser@$HostName")
    }

if (-not $matching) {
    Write-Host "No encontre un tunel activo para $RemoteUser@$HostName en el puerto local $LocalPort."
    exit 0
}

foreach ($proc in $matching) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "Tunel detenido. PID: $($proc.ProcessId)"
}
