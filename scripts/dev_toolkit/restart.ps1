# ==============================================================================
# Tech News Today - Graceful Stack Restart Orchestrator (restart.ps1)
# ==============================================================================

param (
    [string]$Mode = "full",
    [switch]$OpenBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

$config = Get-DevConfig
Show-VersionBanner -Config $config -ActiveMode "RESTART"

Write-ToolkitInfo "Executing graceful restart sequence..."

# 1. Stop Stack
& (Join-Path $scriptDir "stop.ps1")

Start-Sleep -Seconds 2

# 2. Start Stack
$startArgs = @("-Mode", $Mode)
if ($OpenBrowser) { $startArgs += "-OpenBrowser" }

& (Join-Path $scriptDir "start.ps1") @startArgs
