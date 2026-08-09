# ==============================================================================
# Tech News Today - Container Log Streamer (logs.ps1)
# ==============================================================================

param (
    [string]$Service = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

$config = Get-DevConfig
Show-VersionBanner -Config $config -ActiveMode "LOGS"

if ([string]::IsNullOrWhiteSpace($Service)) {
    Write-ToolkitInfo "Streaming logs for ALL active stack containers (Press Ctrl+C to quit)...`n"
    docker compose logs -f
} else {
    Write-ToolkitInfo "Streaming logs for target service '$Service' (Press Ctrl+C to quit)...`n"
    docker compose logs -f $Service
}
