# ==============================================================================
# Tech News Today - Background Self-Healing & Watch Daemon (watch.ps1)
# ==============================================================================

param (
    [int]$IntervalSeconds = 20
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

$config = Get-DevConfig
Show-VersionBanner -Config $config -ActiveMode "WATCH"

Write-ToolkitHeader "BACKGROUND SELF-HEALING & MONITORING DAEMON ACTIVE"
Write-ToolkitInfo "Monitoring stack health every $IntervalSeconds seconds (Press Ctrl+C to stop)...`n"

# Track restart attempts to prevent infinite restart loops (Rule 6)
$restartTracker = @{
    "worker"  = 0
    "backend" = 0
    "beat"    = 0
}

$iteration = 0

while ($true) {
    $iteration++
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [TICK #$iteration] Performing background system health probe..." -ForegroundColor DarkGray

    # 1. Infrastructure Checks
    if (-not (Test-PortListening -Port $config.ports.postgres)) {
        Write-ToolkitError "[$timestamp] PostgreSQL (5433) is OFFLINE!"
    }
    if (-not (Test-PortListening -Port $config.ports.redis)) {
        Write-ToolkitError "[$timestamp] Redis (6379) is OFFLINE!"
    }

    # 2. Backend Gateway Health Check
    $beUrl = "http://localhost:$($config.ports.backend)$($config.healthCheckEndpoints.readiness)"
    $beRes = Invoke-HealthEndpoint -Url $beUrl
    if (-not $beRes.Success) {
        Write-ToolkitWarn "[$timestamp] Backend API Gateway failed readiness probe."
        if ($restartTracker["backend"] -lt 1) {
            $restartTracker["backend"]++
            Write-ToolkitWarn "[$timestamp] Controlled auto-recovery: Restarting backend container (Attempt 1/1)..."
            docker compose restart backend
            Start-Sleep -Seconds 5
        } else {
            Write-ToolkitError "[$timestamp] Backend API Gateway remains unhealthy after max 1 restart attempt."
        }
    } else {
        $restartTracker["backend"] = 0
    }

    # 3. Worker Container Health Check
    $workerState = Get-DockerContainerState -ContainerName $config.containers.worker
    if ($workerState -ne "running") {
        Write-ToolkitWarn "[$timestamp] Celery Worker container state is '$workerState'."
        if ($restartTracker["worker"] -lt 1) {
            $restartTracker["worker"]++
            Write-ToolkitWarn "[$timestamp] Controlled auto-recovery: Restarting worker container (Attempt 1/1)..."
            docker compose restart worker
            Start-Sleep -Seconds 5
        } else {
            Write-ToolkitError "[$timestamp] Celery Worker container failed to recover after max 1 restart attempt."
        }
    } else {
        $restartTracker["worker"] = 0
    }

    # 4. CQRS Projection Lag Check
    $cqrsUrl = "http://localhost:$($config.ports.backend)$($config.healthCheckEndpoints.cqrs)"
    $cqrsRes = Invoke-HealthEndpoint -Url $cqrsUrl
    if ($cqrsRes.Success) {
        $lag = $cqrsRes.Data.data.projection_lag
        if ($lag -gt 10) {
            Write-ToolkitWarn "[$timestamp] CQRS Projection Lag Spike Detected: $lag events pending in outbox!"
        }
    }

    Start-Sleep -Seconds $IntervalSeconds
}
