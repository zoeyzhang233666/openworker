# Free both ChemClaw browser-dev ports (backend 8765 + Vite 1420).
# Usage:
#   powershell -File scripts/kill-chemclaw-dev-ports.ps1
& "$PSScriptRoot\kill-port.ps1" -Port 8765, 1420
exit $LASTEXITCODE
