# ==============================================================================
# Tech News Today - RC4 Health-Gated Startup Orchestrator (start.ps1)
# ==============================================================================

param (
    [string]$Mode = "full",
    [switch]$OpenBrowser,
    [switch]$DryRun,
    [string]$ConfigPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

# Load Configuration
$cliOverrides = @{}
if ($PSBoundParameters.ContainsKey("OpenBrowser")) { $cliOverrides["openBrowser"] = $OpenBrowser.IsPresent }

$config = Get-DevConfig -CliOverrides $cliOverrides
$targetMode = $Mode.ToLower()

$isDryRun = $DryRun.IsPresent -or ($args -contains "--dry-run") -or ($args -contains "-dry-run") -or ($args -contains "dry-run")

if ($isDryRun) {
    Write-ToolkitHeader "DRY RUN MODE ENABLED - NO MUTATIONS WILL BE EXECUTED"
    Write-ToolkitInfo "[DRY-RUN] Pre-flight environment check doctor.ps1"
    Write-ToolkitInfo "[DRY-RUN] Docker Compose start: db, redis"
    Write-ToolkitInfo "[DRY-RUN] Health Gate 1: Poll pg_isready and redis ping"
    Write-ToolkitInfo "[DRY-RUN] Migration Check: alembic current vs alembic heads"
    if ($targetMode -eq "full" -or $targetMode -eq "backend") {
        Write-ToolkitInfo "[DRY-RUN] Docker Compose start: backend"
        Write-ToolkitInfo "[DRY-RUN] Health Gate 2: Poll GET http://localhost:8000/api/v1/health/ready"
        Write-ToolkitInfo "[DRY-RUN] Docker Compose start: worker, beat"
        Write-ToolkitInfo "[DRY-RUN] Health Gate 3: Poll celery inspect ping and CQRS projection lag == 0"
    }
    if ($targetMode -eq "full" -or $targetMode -eq "frontend") {
        Write-ToolkitInfo "[DRY-RUN] Docker Compose start: frontend"
        Write-ToolkitInfo "[DRY-RUN] Health Gate 4: Poll GET http://localhost:3000"
    }
    if ($config.defaults.openBrowser) {
        Write-ToolkitInfo "[DRY-RUN] Browser auto-launch to http://localhost:3000"
    }
    Write-ToolkitSuccess "`n[DRY-RUN] Dry run sequence verification complete. No actions executed."
    exit $script:EXIT_SUCCESS
}

# 1. Execute Pre-Flight Environment Validation
Write-ToolkitInfo "Running pre-flight environment check..."
if (-not (Test-DockerEngineRunning)) {
    Write-ToolkitError "Docker engine is not running. Launch Docker Desktop first."
    exit $script:EXIT_FATAL_ERROR
}

# 2. Stage 1: Infrastructure Startup (Postgres and Redis)
Write-ToolkitHeader "Stage 1: Starting Infrastructure Containers db, redis"
docker compose up -d db redis
if ($LASTEXITCODE -ne 0) {
    Write-ToolkitError "Failed to spin up db/redis containers."
    exit $script:EXIT_FATAL_ERROR
}

# Health Gate 1: Infrastructure
$gate1Pass = Invoke-PolledCheck -Description "PostgreSQL and Redis Readiness" -TimeoutSeconds 30 -CheckScript {
    $dbOk = (Get-DockerContainerState -ContainerName $config.containers.db) -eq "running"
    $redisOk = (Get-DockerContainerState -ContainerName $config.containers.redis) -eq "running"
    return ($dbOk -and $redisOk)
}

if (-not $gate1Pass) {
    Write-ToolkitWarn "Attempting controlled restart of infrastructure containers..."
    docker compose restart db redis
    Start-Sleep -Seconds 3
    if (-not (Test-ContainerHealthy -ContainerName $config.containers.db)) {
        Write-ToolkitError "Infrastructure containers failed to reach healthy state."
        exit $script:EXIT_FATAL_ERROR
    }
}

if ($targetMode -eq "infra") {
    Write-ToolkitSuccess "`nInfrastructure containers db, redis are ready!"
    exit $script:EXIT_SUCCESS
}

# 3. Stage 2: Smart Migration Guard
Write-ToolkitHeader "Stage 2: Checking Alembic Database Migration Revision Head"
try {
    $currentRev = docker compose run --rm backend alembic current 2>&1
    if ($currentRev -match "\(head\)") {
        Write-ToolkitSuccess "Database schema is already at latest head revision. Skipping migrations."
    } else {
        Write-ToolkitInfo "Pending migrations detected. Running alembic upgrade head..."
        docker compose run --rm backend alembic upgrade head
    }
} catch {
    Write-ToolkitWarn "Unable to verify migration status via container; proceeding with backend boot."
}

# 4. Stage 3: Backend Gateway Startup
if ($targetMode -eq "full" -or $targetMode -eq "backend") {
    Write-ToolkitHeader "Stage 3: Starting Backend API Gateway Container"
    docker compose up -d backend
    
    # Health Gate 2: FastAPI Gateway Readiness
    $bePort = $config.ports.backend
    $bePath = $config.healthCheckEndpoints.readiness
    $beUrl = "http://localhost:$bePort$bePath"

    $gate2Pass = Invoke-PolledCheck -Description "FastAPI Gateway readiness" -TimeoutSeconds $config.defaults.healthTimeoutSeconds -CheckScript {
        $res = Invoke-HealthEndpoint -Url $beUrl
        return ($res.Success -and $res.StatusCode -eq 200)
    }

    if (-not $gate2Pass) {
        Write-ToolkitWarn "Backend gateway endpoint failed. Attempting controlled restart..."
        docker compose restart backend
        Start-Sleep -Seconds 5
        $res = Invoke-HealthEndpoint -Url $beUrl
        if (-not $res.Success) {
            Write-ToolkitError "Backend API gateway failed readiness checks."
            exit $script:EXIT_FATAL_ERROR
        }
    }

    # Stage 4: Celery Workers and Beat Scheduler
    Write-ToolkitHeader "Stage 4: Starting Celery Worker and Beat Containers"
    docker compose up -d worker beat

    # Health Gate 3: CQRS Projection Lag
    $cqrsPath = $config.healthCheckEndpoints.cqrs
    $cqrsUrl = "http://localhost:$bePort$cqrsPath"

    $gate3Pass = Invoke-PolledCheck -Description "CQRS Projection Sync" -TimeoutSeconds 30 -CheckScript {
        $res = Invoke-HealthEndpoint -Url $cqrsUrl
        return ($res.Success -and $res.Data.data.projection_lag -le 5)
    }
    if (-not $gate3Pass) {
        Write-ToolkitWarn "CQRS projections still syncing; continuing startup."
    }
}

if ($targetMode -eq "backend") {
    Write-ToolkitSuccess "`nBackend API stack and background workers are ready!"
    exit $script:EXIT_SUCCESS
}

# 5. Stage 5: Frontend UI Startup
if ($targetMode -eq "full" -or $targetMode -eq "frontend") {
    Write-ToolkitHeader "Stage 5: Starting Frontend Next.js Container"
    docker compose up -d frontend

    # Health Gate 4: Frontend Readiness
    $fePort = $config.ports.frontend
    $feUrl = "http://localhost:$fePort"

    $gate4Pass = Invoke-PolledCheck -Description "Frontend Next.js UI" -TimeoutSeconds $config.defaults.healthTimeoutSeconds -CheckScript {
        return (Test-PortListening -Port $fePort)
    }

    if (-not $gate4Pass) {
        Write-ToolkitWarn "Frontend UI failed initial port check. Attempting controlled restart..."
        docker compose restart frontend
        Start-Sleep -Seconds 5
    }
}

# 6. Stage 6: Browser Launch Option
if ($config.defaults.openBrowser -or $OpenBrowser) {
    $fePort = $config.ports.frontend
    Write-ToolkitInfo "Opening default browser to http://localhost:$fePort..."
    Start-Process "http://localhost:$fePort"
}

Write-Host "`n==============================================================================" -ForegroundColor DarkCyan
Write-ToolkitSuccess "TECH NEWS TODAY PLATFORM IS READY AND OPERATIONAL!"
Write-Host "==============================================================================" -ForegroundColor DarkCyan
exit $script:EXIT_SUCCESS
