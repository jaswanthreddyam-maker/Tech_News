# ==============================================================================
# Tech News Today - Mandatory CI Gate Script
# ==============================================================================

Write-Host "=== Phase 8 Mandatory CI Gates ===" -ForegroundColor Cyan
Write-Host "Running comprehensive certification pipeline..." -ForegroundColor Cyan

# 1. Frontend Gates
Write-Host "`n[1/7] Running Frontend Lint..." -ForegroundColor Yellow
Set-Location frontend
npm run lint
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Frontend Lint Failed" -ForegroundColor Red; exit 1 }

Write-Host "`n[2/7] Running Frontend Typecheck..." -ForegroundColor Yellow
npm run typecheck
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Frontend Typecheck Failed" -ForegroundColor Red; exit 1 }

Write-Host "`n[3/7] Running Frontend Build..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Frontend Build Failed" -ForegroundColor Red; exit 1 }
Set-Location ..

# 2. Backend Gates
Write-Host "`n[4/7] Running Backend Pytest..." -ForegroundColor Yellow
docker compose exec -e USE_NULL_POOL=1 -T backend pytest
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Backend Pytest Failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n[5/7] Running Backend Mypy..." -ForegroundColor Yellow
docker compose exec -T backend mypy app
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Backend Mypy Failed" -ForegroundColor Red; exit 1 }

Write-Host "`n[6/7] Running Backend Ruff..." -ForegroundColor Yellow
docker compose exec -T backend ruff check app
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Backend Ruff Failed" -ForegroundColor Red; exit 1 }

# 3. Migration Verification
Write-Host "`n[7/7] Verifying Alembic Migrations Reversibility..." -ForegroundColor Yellow
Write-Host "-> Upgrading to head"
docker compose exec -T backend alembic upgrade head
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Alembic Upgrade Head Failed" -ForegroundColor Red; exit 1 }

Write-Host "-> Downgrading -1"
docker compose exec -T backend alembic downgrade -1
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Alembic Downgrade Failed" -ForegroundColor Red; exit 1 }

Write-Host "-> Upgrading back to head"
docker compose exec -T backend alembic upgrade head
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Alembic Re-upgrade Failed" -ForegroundColor Red; exit 1 }

Write-Host "`n✅ All CI Gates Passed Successfully!" -ForegroundColor Green
exit 0
