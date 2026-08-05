# Convenience wrapper: free ChemClaw backend port 8765.
# Prefer: powershell -File scripts/kill-port.ps1 -Port 8765
& "$PSScriptRoot\kill-port.ps1" -Port 8765
exit $LASTEXITCODE
