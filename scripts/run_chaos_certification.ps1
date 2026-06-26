$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host " RC2.2 Phase 2: Runtime Certification     "
Write-Host "=========================================="

cd $(Join-Path $PSScriptRoot "..")

$env:POSTGRES_DB="tech_news_today"
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres_secure_pass@localhost:5433/tech_news_today"

Write-Host "1. Tearing down existing stack..."
docker compose down -v

Write-Host "2. Starting fresh production stack (building images)..."
docker compose up -d --build

Write-Host "3. Waiting for services to become healthy..."
Start-Sleep -Seconds 15

# Verify container status before testing
$containers = docker compose ps -q
if (-not $containers) {
    Write-Error "Failed to start Docker Compose stack."
    exit 1
}

Write-Host "4. Running Certification Chaos Suite..."
cd backend
$env:PYTHONPATH="."
$env:CHAOS_RUNNER="0" # Explicitly test runtime
venv\Scripts\pytest.exe -v tests/chaos/test_runtime_certification.py

$test_exit_code = $LASTEXITCODE

Write-Host "5. Checking Artifact Generation..."
if (Test-Path "chaos/results/runtime/") {
    $artifacts = Get-ChildItem "chaos/results/runtime/*.json"
    Write-Host "Generated $($artifacts.Count) evidence artifacts."
} else {
    Write-Warning "No evidence artifacts found."
}

Write-Host "6. Tearing down stack..."
cd ..
docker compose down -v

if ($test_exit_code -eq 0) {
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host " CERTIFICATION PASSED                     " -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
} else {
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host " CERTIFICATION FAILED                     " -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
}

exit $test_exit_code
