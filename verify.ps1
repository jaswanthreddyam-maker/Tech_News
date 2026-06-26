# Verification Script

Write-Host "Running Frontend Lint..." -ForegroundColor Yellow
cd frontend
npm run lint
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Frontend Lint Failed" -ForegroundColor Red; exit 1 }

Write-Host "Running Frontend Typecheck..." -ForegroundColor Yellow
npm run typecheck
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Frontend Typecheck Failed" -ForegroundColor Red; exit 1 }

Write-Host "Running Frontend Build..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Frontend Build Failed" -ForegroundColor Red; exit 1 }
cd ..

Write-Host "Running Backend Pytest..." -ForegroundColor Yellow
cd backend
.\venv\Scripts\python.exe -m pytest
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Backend Pytest Failed" -ForegroundColor Red; exit 1 }

Write-Host "Running Backend Mypy..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m mypy app
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Backend Mypy Failed" -ForegroundColor Red; exit 1 }

Write-Host "Running Backend Ruff..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m ruff check app
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Backend Ruff Failed" -ForegroundColor Red; exit 1 }

Write-Host "Verifying Alembic Migrations Reversibility..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Alembic Upgrade Head Failed" -ForegroundColor Red; exit 1 }

.\venv\Scripts\python.exe -m alembic downgrade -1
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Alembic Downgrade Failed" -ForegroundColor Red; exit 1 }

.\venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Alembic Re-upgrade Failed" -ForegroundColor Red; exit 1 }

Write-Host "✅ All Verification Steps Passed Successfully!" -ForegroundColor Green
exit 0
