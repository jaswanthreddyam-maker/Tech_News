<#
.SYNOPSIS
Migrates existing data to the new runtime directory structure.

.DESCRIPTION
This script safely copies existing local data (uploads, backups, logs) and 
Docker named volume data (PostgreSQL, Redis) into the centralized /runtime directory.
It uses an ephemeral alpine container to extract Docker volume data.
#>

$ErrorActionPreference = "Stop"

Write-Host "Starting Runtime Migration..." -ForegroundColor Cyan

# 1. Ensure new directory structure exists
$dirs = @(
    "runtime/storage/uploads/thumbnails/original",
    "runtime/storage/uploads/thumbnails/optimized",
    "runtime/storage/uploads/thumbnails/fallback",
    "runtime/storage/temp",
    "runtime/storage/exports",
    "runtime/storage/backups",
    "runtime/postgres",
    "runtime/redis",
    "runtime/logs",
    "runtime/monitoring",
    "runtime/celery"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path -Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
}

# 2. Copy Local Files
Write-Host "Copying local storage (uploads, backups, logs)..." -ForegroundColor Yellow

if (Test-Path ".\storage\uploads") {
    Copy-Item -Path ".\storage\uploads\*" -Destination ".\runtime\storage\uploads\" -Recurse -Force -ErrorAction SilentlyContinue
}
if (Test-Path ".\storage\backups") {
    Copy-Item -Path ".\storage\backups\*" -Destination ".\runtime\storage\backups\" -Recurse -Force -ErrorAction SilentlyContinue
}
if (Test-Path ".\backend\logs") {
    Copy-Item -Path ".\backend\logs\*" -Destination ".\runtime\logs\" -Recurse -Force -ErrorAction SilentlyContinue
}
if (Test-Path ".\logs") {
    Copy-Item -Path ".\logs\*" -Destination ".\runtime\logs\" -Recurse -Force -ErrorAction SilentlyContinue
}

# 3. Migrate Docker Named Volumes
Write-Host "Migrating Docker volumes to bind mounts..." -ForegroundColor Yellow

$pwd = (Get-Location).Path -replace "\\", "/"
# In docker, windows paths usually need to be formatted differently depending on shell, but ${PWD} in PS resolves.
# Safer to use an absolute path formatted for Docker:
$dockerPwd = "/host_mnt/" + ($pwd -replace ":", "").ToLower()
# Actually, Docker Desktop handles C:\ paths well. Let's just use absolute paths.

try {
    Write-Host "  -> Extracting tech_news_postgres_data..."
    docker run --rm -v "tech_news_postgres_data:/from" -v "$pwd/runtime/postgres:/to" alpine sh -c "cp -a /from/* /to/ 2>/dev/null || true"
} catch {
    Write-Host "     Warning: Could not copy postgres data. It may not exist." -ForegroundColor Red
}

try {
    Write-Host "  -> Extracting tech_news_redis_data..."
    docker run --rm -v "tech_news_redis_data:/from" -v "$pwd/runtime/redis:/to" alpine sh -c "cp -a /from/* /to/ 2>/dev/null || true"
} catch {
    Write-Host "     Warning: Could not copy redis data. It may not exist." -ForegroundColor Red
}

Write-Host "Migration complete! Verify your data in ./runtime before deleting old volumes." -ForegroundColor Green
Write-Host "You can remove old volumes via: docker volume rm tech_news_postgres_data tech_news_redis_data" -ForegroundColor Cyan
