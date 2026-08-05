# Free a TCP Listen port on Windows (ChemClaw dev helpers).
# Ctrl+C often leaves node (Vite) or python (openworker-server) holding the port.
#
# Usage:
#   powershell -File scripts/kill-port.ps1 -Port 1420
#   powershell -File scripts/kill-port.ps1 -Port 8765
#   powershell -File scripts/kill-port.ps1 -Port 8765,1420

param(
    [Parameter(Mandatory = $false)]
    [int[]]$Port = @(8765)
)

$ErrorActionPreference = "Continue"
$failed = $false

foreach ($p in $Port) {
    $pids = @(
        Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    if (-not $pids -or $pids.Count -eq 0) {
        Write-Host "Port $p is free (nothing in Listen state)."
    } else {
        foreach ($procId in $pids) {
            if (-not $procId -or $procId -eq 0) { continue }
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "Killing PID $procId ($($proc.ProcessName)) on port $p"
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

# Backend launcher leftover (may not still hold Listen).
if ($Port -contains 8765) {
    Get-Process openworker-server -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "Killing leftover openworker-server PID $($_.Id)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

Start-Sleep -Seconds 1

foreach ($p in $Port) {
    $still = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($still) {
        Write-Host "WARN: port $p still in Listen:"
        $still | Format-Table LocalAddress, LocalPort, OwningProcess -AutoSize
        $failed = $true
    } else {
        Write-Host "OK: port $p is free."
    }
}

if ($failed) { exit 1 }
exit 0
