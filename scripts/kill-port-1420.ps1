# Convenience wrapper: free ChemClaw Vite GUI port 1420.
# Prefer: powershell -File scripts/kill-port.ps1 -Port 1420
& "$PSScriptRoot\kill-port.ps1" -Port 1420
exit $LASTEXITCODE
