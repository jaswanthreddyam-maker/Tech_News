# ==============================================================================
# Tech News Today - Developer Automation PowerShell Script for Windows
# ==============================================================================

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "rebuild", "logs", "test", "lint", "clean")]
    [string]$Action
)

switch ($Action) {
    "start" {
        Write-Host "Starting Tech News Today containers..." -ForegroundColor Green
        docker compose up -d
    }
    "stop" {
        Write-Host "Shutting down all containers..." -ForegroundColor Yellow
        docker compose down -v
    }
    "rebuild" {
        Write-Host "Rebuilding and starting all containers..." -ForegroundColor Green
        docker compose up -d --build
    }
    "logs" {
        Write-Host "Streaming container logs (Ctrl+C to quit)..." -ForegroundColor Cyan
        docker compose logs -f
    }
    "test" {
        Write-Host "Executing Pytest test suite inside backend container..." -ForegroundColor Cyan
        docker compose exec backend pytest
    }
    "lint" {
        Write-Host "Executing Ruff linting checks inside backend container..." -ForegroundColor Cyan
        docker compose exec backend ruff check .
        Write-Host "Executing ESLint checks inside frontend container..." -ForegroundColor Cyan
        docker compose exec frontend npm run lint
    }
    "clean" {
        Write-Host "Cleaning temporary file caches..." -ForegroundColor Yellow
        Get-ChildItem -Path . -Filter "__pycache__" -Recurse | Remove-Item -Recurse -Force
        Get-ChildItem -Path . -Filter "*.pyc" -Recurse | Remove-Item -Force
        Write-Host "Temporary caches cleared successfully." -ForegroundColor Green
    }
}
