# One-shot ChemClaw browser-dev restart (Windows):
#   1) free ports 8765 + 1420
#   2) start backend in a new PowerShell window
#   3) wait until /v1/health is OK
#   4) start Vite GUI in another new PowerShell window
#
# Usage (from anywhere):
#   powershell -File D:\OpenWorker\openworker\.worktrees\chemclaw-clean\scripts\restart-chemclaw-dev.ps1
#   powershell -File .\scripts\restart-chemclaw-dev.ps1
#
# Optional:
#   -StateDir  D:\OpenWorker\.chemclaw-dev\state
#   -ApiPort   8765
#   -VitePort  1420
#   -SkipGui   # only restart backend

param(
    [string]$StateDir = "D:\OpenWorker\.chemclaw-dev\state",
    [int]$ApiPort = 8765,
    [int]$VitePort = 1420,
    [switch]$SkipGui,
    [int]$HealthTimeoutSec = 45
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ServerExe = Join-Path $RepoRoot ".venv\Scripts\openworker-server.exe"
$GuiDir = Join-Path $RepoRoot "surfaces\gui"

if (-not (Test-Path -LiteralPath $ServerExe)) {
    Write-Error "Missing backend: $ServerExe (create .venv / install first)."
}
if (-not $SkipGui -and -not (Test-Path -LiteralPath (Join-Path $GuiDir "package.json"))) {
    Write-Error "Missing GUI dir: $GuiDir"
}

Write-Host "==> Freeing ports $ApiPort + $VitePort ..."
& "$PSScriptRoot\kill-port.ps1" -Port $ApiPort, $VitePort
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to free ports (exit $LASTEXITCODE)."
}

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

Write-Host "==> Starting backend on 127.0.0.1:$ApiPort ..."
$backendCmd = @"
`$Host.UI.RawUI.WindowTitle = 'ChemClaw backend :$ApiPort'
Set-Location -LiteralPath '$RepoRoot'
`$env:COWORKER_STATE_DIR = '$StateDir'
Write-Host "COWORKER_STATE_DIR=`$env:COWORKER_STATE_DIR"
& '$ServerExe' --host 127.0.0.1 --port $ApiPort
"@
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", $backendCmd
) | Out-Null

$healthUrl = "http://127.0.0.1:$ApiPort/v1/health"
Write-Host "==> Waiting for $healthUrl (timeout ${HealthTimeoutSec}s) ..."
$deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($null -ne $resp) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $ready) {
    Write-Error "Backend did not become healthy in time. Check the 'ChemClaw backend' window."
}
Write-Host "OK: backend healthy."

if ($SkipGui) {
    Write-Host "SkipGui set — not starting Vite."
    Write-Host "API:  http://127.0.0.1:$ApiPort"
    exit 0
}

Write-Host "==> Starting Vite GUI on port $VitePort ..."
$guiCmd = @"
`$Host.UI.RawUI.WindowTitle = 'ChemClaw GUI :$VitePort'
Set-Location -LiteralPath '$GuiDir'
`$env:COWORKER_STATE_DIR = '$StateDir'
Write-Host "COWORKER_STATE_DIR=`$env:COWORKER_STATE_DIR"
npm.cmd run dev -- --port $VitePort
"@
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", $guiCmd
) | Out-Null

Write-Host ""
Write-Host "Started in two new windows."
Write-Host "  API:  http://127.0.0.1:$ApiPort"
Write-Host "  GUI:  http://localhost:$VitePort"
Write-Host "Open the GUI with localhost (not 127.0.0.1) on this Windows setup."
exit 0
