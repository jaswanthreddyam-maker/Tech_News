# ==============================================================================
# Tech News Today - Stack & Process Cleanup Orchestrator (stop.ps1)
# ==============================================================================

param (
    [switch]$Volumes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

$config = Get-DevConfig
Show-VersionBanner -Config $config -ActiveMode "STOP"

Write-ToolkitInfo "Shutting down all stack containers..."

if ($Volumes) {
    Write-ToolkitWarn "Option -Volumes specified: Removing Docker persistent volume stores..."
    docker compose down -v
} else {
    docker compose down
}

# Cleanup orphaned host processes if any
Write-ToolkitInfo "Checking for orphaned host processes..."
foreach ($portKey in $config.ports.Keys) {
    $port = [int]$config.ports[$portKey]
    $proc = Get-ProcessOnPort -Port $port
    if ($proc) {
        Write-ToolkitWarn "Stopping process $($proc.ProcessName) (PID $($proc.Id)) on port $port..."
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-ToolkitSuccess "`nAll containers and processes stopped cleanly."
exit $script:EXIT_SUCCESS
