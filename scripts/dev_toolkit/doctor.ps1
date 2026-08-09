# ==============================================================================
# Tech News Today - RC4 Pre-Flight Environment Doctor (doctor.ps1)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "common.ps1")

$config = Get-DevConfig
Show-VersionBanner -Config $config -ActiveMode "DOCTOR"

Write-Host "==============================================================================" -ForegroundColor DarkCyan
Write-Host " ENVIRONMENT & DEPENDENCY DIAGNOSTIC PROBE" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor DarkCyan

$fatalCount = 0
$warnCount  = 0

# Check 1: Docker Daemon
Write-Host -NoNewline "[CHECK] Docker Daemon .......... "
if (Test-DockerEngineRunning) {
    Write-Host "RUNNING" -ForegroundColor Green
} else {
    Write-Host "FAILED" -ForegroundColor Red
    Write-ToolkitError "  -> Fix: Ensure Docker Desktop is started and running on your system."
    $fatalCount++
}

# Check 2: Docker Compose CLI
Write-Host -NoNewline "[CHECK] Docker Compose v2 ...... "
try {
    $composeVersion = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "AVAILABLE ($($composeVersion.Trim()))" -ForegroundColor Green
    } else {
        Write-Host "FAILED" -ForegroundColor Red
        Write-ToolkitError "  -> Fix: Install or enable Docker Compose plugin for Docker CLI."
        $fatalCount++
    }
} catch {
    Write-Host "FAILED" -ForegroundColor Red
    $fatalCount++
}

# Check 3: Python Runtime
Write-Host -NoNewline "[CHECK] Python Runtime ......... "
try {
    $pyVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "INSTALLED ($($pyVersion.Trim()))" -ForegroundColor Green
    } else {
        Write-Host "WARNING" -ForegroundColor Yellow
        Write-ToolkitWarn "  -> Warning: Python CLI not found in PATH."
        $warnCount++
    }
} catch {
    Write-Host "WARNING" -ForegroundColor Yellow
    $warnCount++
}

# Check 4: Node.js Runtime
Write-Host -NoNewline "[CHECK] Node.js Runtime ........ "
try {
    $nodeVersion = node -v 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "INSTALLED ($($nodeVersion.Trim()))" -ForegroundColor Green
    } else {
        Write-Host "WARNING" -ForegroundColor Yellow
        Write-ToolkitWarn "  -> Warning: Node.js not found in PATH."
        $warnCount++
    }
} catch {
    Write-Host "WARNING" -ForegroundColor Yellow
    $warnCount++
}

# Check 5: Environment File (.env)
Write-Host -NoNewline "[CHECK] Environment File (.env) "
$envPath = Join-Path $script:WORKSPACE_DIR ".env"
if (Test-Path $envPath) {
    Write-Host "FOUND" -ForegroundColor Green
} else {
    Write-Host "FAILED" -ForegroundColor Red
    Write-ToolkitError "  -> Fix: Copy .env.example to .env in the project root folder."
    $fatalCount++
}

# Check 6: Port Conflict Check
Write-Host -NoNewline "[CHECK] Port Availability ...... "
$conflicts = @()
foreach ($service in $config.ports.Keys) {
    $port = [int]$config.ports[$service]
    if (Test-PortListening -Port $port) {
        # Check if listening process is a Docker container or unexpected process
        $proc = Get-ProcessOnPort -Port $port
        if ($proc) {
            $conflicts += "$service (Port $port bound by $($proc.ProcessName))"
        }
    }
}

if ($conflicts.Count -eq 0) {
    Write-Host "ALL PORTS CLEAR" -ForegroundColor Green
} else {
    Write-Host "ACTIVE PORTS DETECTED" -ForegroundColor Yellow
    Write-ToolkitWarn "  -> Active services on ports: $($conflicts -join ', ')"
    Write-ToolkitWarn "  -> Note: Docker containers or local dev servers may already be running."
    $warnCount++
}

# Check 7: Next.js HMR & Docker Volume Configuration
Write-Host -NoNewline "[CHECK] Next.js Build Volumes .. "
$composeYmlPath = Join-Path $script:WORKSPACE_DIR "docker-compose.yml"
if (Test-Path $composeYmlPath) {
    $composeContent = Get-Content $composeYmlPath -Raw
    if ($composeContent -match "- /app/\.next") {
        Write-Host "STALE VOLUME DETECTED" -ForegroundColor Red
        Write-ToolkitError "  -> Fix: Remove '- /app/.next' from docker-compose.yml to prevent stale build caching."
        $fatalCount++
    } else {
        Write-Host "CLEAN (No Anonymous .next Volume)" -ForegroundColor Green
    }
} else {
    Write-Host "WARNING (docker-compose.yml missing)" -ForegroundColor Yellow
    $warnCount++
}

Write-Host "==============================================================================" -ForegroundColor DarkCyan

if ($fatalCount -gt 0) {
    Write-ToolkitError "Pre-flight diagnostic failed with $fatalCount fatal issue(s)."
    exit $script:EXIT_FATAL_ERROR
} elseif ($warnCount -gt 0) {
    Write-ToolkitWarn "Pre-flight diagnostic completed with $warnCount warning(s)."
    exit $script:EXIT_WARNING
} else {
    Write-ToolkitSuccess "All pre-flight environment checks passed successfully! System ready."
    exit $script:EXIT_SUCCESS
}
