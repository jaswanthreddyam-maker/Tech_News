# ==============================================================================
# Tech News Today - RC4 Tiered Health Diagnostic Probe (health.ps1)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

$config = Get-DevConfig
Show-VersionBanner -Config $config -ActiveMode "HEALTH"

Write-Host "==============================================================================" -ForegroundColor DarkCyan
Write-Host " MULTI-TIER SYSTEM HEALTH DIAGNOSTIC REPORT" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor DarkCyan

$unhealthyCount = 0
$degradedCount  = 0

# Tier 1: Infrastructure
Write-Host "`n[TIER 1: INFRASTRUCTURE]" -ForegroundColor Gray
Write-Host -NoNewline "  PostgreSQL (Port $($config.ports.postgres)) ...... "
if (Test-PortListening -Port $config.ports.postgres) {
    Write-Host "ONLINE" -ForegroundColor Green
} else {
    Write-Host "OFFLINE" -ForegroundColor Red
    $unhealthyCount++
}

Write-Host -NoNewline "  Redis (Port $($config.ports.redis)) ........... "
if (Test-PortListening -Port $config.ports.redis) {
    Write-Host "ONLINE" -ForegroundColor Green
} else {
    Write-Host "OFFLINE" -ForegroundColor Red
    $unhealthyCount++
}

# Tier 2: Backend Gateway
Write-Host "`n[TIER 2: BACKEND API GATEWAY]" -ForegroundColor Gray
$beReadinessUrl = "http://localhost:$($config.ports.backend)$($config.healthCheckEndpoints.readiness)"
Write-Host -NoNewline "  FastAPI Readiness (/health/ready) .. "
$beRes = Invoke-HealthEndpoint -Url $beReadinessUrl
if ($beRes.Success -and $beRes.StatusCode -eq 200) {
    $pgLat = $beRes.Data.data.dependencies.postgres.latency_ms
    $rdLat = $beRes.Data.data.dependencies.redis.latency_ms
    Write-Host "HEALTHY (Postgres: ${pgLat}ms, Redis: ${rdLat}ms)" -ForegroundColor Green
} else {
    Write-Host "UNHEALTHY" -ForegroundColor Red
    $unhealthyCount++
}

# Tier 3: CQRS & Asynchronous Pipeline
Write-Host "`n[TIER 3: ASYNCHRONOUS PIPELINE & CQRS]" -ForegroundColor Gray
$cqrsUrl = "http://localhost:$($config.ports.backend)$($config.healthCheckEndpoints.cqrs)"
Write-Host -NoNewline "  CQRS Projection Sync (/health/cqrs) . "
$cqrsRes = Invoke-HealthEndpoint -Url $cqrsUrl
if ($cqrsRes.Success) {
    $lag = $cqrsRes.Data.data.projection_lag
    $rate = $cqrsRes.Data.data.projection_success_rate
    if ($lag -eq 0) {
        Write-Host "HEALTHY (Lag: 0, Rate: $rate)" -ForegroundColor Green
    } else {
        Write-Host "DEGRADED (Lag: $lag pending)" -ForegroundColor Yellow
        $degradedCount++
    }
} else {
    Write-Host "UNHEALTHY" -ForegroundColor Red
    $degradedCount++
}

# Tier 4: Frontend UI
Write-Host "`n[TIER 4: FRONTEND USER INTERFACE]" -ForegroundColor Gray
Write-Host -NoNewline "  Next.js Server (Port $($config.ports.frontend)) ..... "
if (Test-PortListening -Port $config.ports.frontend) {
    Write-Host "ONLINE" -ForegroundColor Green
} else {
    Write-Host "OFFLINE" -ForegroundColor Red
    $unhealthyCount++
}

Write-Host "`n==============================================================================" -ForegroundColor DarkCyan

if ($unhealthyCount -gt 0) {
    Write-ToolkitError "Health assessment: UNHEALTHY ($unhealthyCount component(s) down)."
    exit $script:EXIT_FATAL_ERROR
} elseif ($degradedCount -gt 0) {
    Write-ToolkitWarn "Health assessment: DEGRADED ($degradedCount issue(s) detected)."
    exit $script:EXIT_WARNING
} else {
    Write-ToolkitSuccess "Health assessment: 100% HEALTHY & OPERATIONAL."
    exit $script:EXIT_SUCCESS
}
