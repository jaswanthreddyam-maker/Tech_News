# ==============================================================================
# Tech News Today - RC4 Local Developer Toolkit Shared Library (common.ps1)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Exit Code Standard Constants
$script:EXIT_SUCCESS     = 0
$script:EXIT_WARNING     = 1
$script:EXIT_FATAL_ERROR = 2

# Path Definitions
$script:TOOLKIT_DIR   = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:WORKSPACE_DIR = Resolve-Path (Join-Path $script:TOOLKIT_DIR "..\..")

# ------------------------------------------------------------------------------
# 1. Config Loading & Merging Cascade
# ------------------------------------------------------------------------------
function Get-DevConfig {
    param (
        [string]$ConfigPath = (Join-Path $script:TOOLKIT_DIR "dev.config.json"),
        [string]$LocalConfigPath = (Join-Path $script:TOOLKIT_DIR "dev.config.local.json"),
        [hashtable]$CliOverrides = @{}
    )

    if (-not (Test-Path $ConfigPath)) {
        Write-ToolkitError "Base configuration file missing: $ConfigPath"
        exit $script:EXIT_FATAL_ERROR
    }

    $rawJson = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
    
    # Convert PSObject to hashtable recursively for easy mutation
    $config = Convert-PSObjectToHashtable $rawJson

    # Merge local overrides if present
    if (Test-Path $LocalConfigPath) {
        try {
            $localJson = Get-Content -Path $LocalConfigPath -Raw | ConvertFrom-Json
            $localHashtable = Convert-PSObjectToHashtable $localJson
            $config = Merge-Hashtables $config $localHashtable
        } catch {
            Write-ToolkitWarn "Failed to parse dev.config.local.json: $_"
        }
    }

    # Merge CLI Overrides
    foreach ($key in $CliOverrides.Keys) {
        if ($null -ne $CliOverrides[$key]) {
            $config[$key] = $CliOverrides[$key]
        }
    }

    return $config
}

function Convert-PSObjectToHashtable {
    param ($InputObject)

    if ($null -eq $InputObject) { return $null }

    if ($InputObject -is [System.Management.Automation.PSCustomObject]) {
        $hash = @{}
        foreach ($prop in $InputObject.PSObject.Properties) {
            $hash[$prop.Name] = Convert-PSObjectToHashtable $prop.Value
        }
        return $hash
    } elseif ($InputObject -is [Array]) {
        $array = @()
        foreach ($item in $InputObject) {
            $array += Convert-PSObjectToHashtable $item
        }
        return $array
    } else {
        return $InputObject
    }
}

function Merge-Hashtables {
    param (
        [hashtable]$Primary,
        [hashtable]$Secondary
    )

    $result = $Primary.Clone()
    foreach ($key in $Secondary.Keys) {
        if ($result.ContainsKey($key) -and ($result[$key] -is [hashtable]) -and ($Secondary[$key] -is [hashtable])) {
            $result[$key] = Merge-Hashtables $result[$key] $Secondary[$key]
        } else {
            $result[$key] = $Secondary[$key]
        }
    }
    return $result
}

# ------------------------------------------------------------------------------
# 2. Colorized Logging Helpers
# ------------------------------------------------------------------------------
function Write-ToolkitInfo {
    param ([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-ToolkitSuccess {
    param ([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-ToolkitWarn {
    param ([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-ToolkitError {
    param ([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Write-ToolkitHeader {
    param ([string]$Title)
    Write-Host "`n=== $Title ===" -ForegroundColor Magenta
}

# ------------------------------------------------------------------------------
# 3. Version Banner Renderer
# ------------------------------------------------------------------------------
function Show-VersionBanner {
    param (
        [hashtable]$Config,
        [string]$ActiveMode = "full"
    )

    $version    = $Config.version
    $env        = $Config.environment
    $fePort     = $Config.ports.frontend
    $bePort     = $Config.ports.backend
    $pgPort     = $Config.ports.postgres
    $redisPort  = $Config.ports.redis

    $modeStr    = $ActiveMode.ToUpper()
    $timeoutStr = "$($Config.defaults.healthTimeoutSeconds) seconds"

    Write-Host "==============================================================================" -ForegroundColor DarkCyan
    Write-Host " TECH NEWS TODAY - $version DEVELOPMENT TOOLKIT" -ForegroundColor Cyan
    Write-Host "==============================================================================" -ForegroundColor DarkCyan
    Write-Host " [CONFIG] Mode: $modeStr | Env: $env | Health Timeout: $timeoutStr" -ForegroundColor Gray
    Write-Host " [PORTS]  Frontend: $fePort | Backend: $bePort | Postgres: $pgPort | Redis: $redisPort" -ForegroundColor Gray
    Write-Host "==============================================================================" -ForegroundColor DarkCyan
}

# ------------------------------------------------------------------------------
# 4. Docker Engine & Container Probes
# ------------------------------------------------------------------------------
function Test-DockerEngineRunning {
    try {
        $null = docker info 2>&1
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Get-DockerContainerState {
    param ([string]$ContainerName)
    try {
        $state = docker inspect --format "{{.State.Status}}" $ContainerName 2>$null
        if ([string]::IsNullOrWhiteSpace($state)) {
            return "not_found"
        }
        return $state.Trim()
    } catch {
        return "not_found"
    }
}

function Test-ContainerHealthy {
    param ([string]$ContainerName)
    try {
        $health = docker inspect --format "{{.State.Status}}" $ContainerName 2>$null
        if ($health -eq "healthy" -or $health -eq "running") {
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

# ------------------------------------------------------------------------------
# 5. Network Port & HTTP Probes
# ------------------------------------------------------------------------------
function Test-PortListening {
    param (
        [string]$HostName = "127.0.0.1",
        [int]$Port,
        [int]$TimeoutMs = 1000
    )

    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $client.BeginConnect($HostName, $Port, $null, $null)
        $waitResult = $asyncResult.AsyncWaitHandle.WaitOne($TimeoutMs, $false)

        if (-not $waitResult) {
            $client.Close()
            return $false
        }

        $client.EndConnect($asyncResult)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Get-ProcessOnPort {
    param ([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            return $proc
        }
        return $null
    } catch {
        return $null
    }
}

function Invoke-HealthEndpoint {
    param (
        [string]$Url,
        [int]$TimeoutSec = 5
    )

    try {
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec $TimeoutSec -ErrorAction Stop
        return @{
            Success = $true
            StatusCode = 200
            Data = $response
        }
    } catch {
        $code = 0
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
        }
        return @{
            Success = $false
            StatusCode = $code
            Error = $_.Exception.Message
        }
    }
}

# ------------------------------------------------------------------------------
# 6. Polling & Retry Helper
# ------------------------------------------------------------------------------
function Invoke-PolledCheck {
    param (
        [scriptblock]$CheckScript,
        [string]$Description,
        [int]$TimeoutSeconds = 30,
        [int]$IntervalSeconds = 2
    )

    $elapsed = 0
    Write-ToolkitInfo "Waiting for $Description..."

    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $result = &$CheckScript
            if ($result) {
                Write-ToolkitSuccess "$Description passed in $elapsed seconds."
                return $true
            }
        } catch {
            # Continue polling
        }

        Start-Sleep -Seconds $IntervalSeconds
        $elapsed += $IntervalSeconds
    }

    Write-ToolkitError "Timeout waiting for $Description after $TimeoutSeconds seconds."
    return $false
}
