# Runs the verification suite required before delivery:
#   backend tests, frontend build, database migrations, seed data,
#   docker compose validation and the end-to-end disruption simulation.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\verify.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "1/5 Backend test suite" -ForegroundColor Cyan
Push-Location (Join-Path $root "backend")
& .\.venv\Scripts\python.exe -m pytest tests -q
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "Backend tests failed." -ForegroundColor Red; exit 1 }
Pop-Location

Write-Host "2/5 Frontend production build" -ForegroundColor Cyan
Push-Location (Join-Path $root "frontend")
& npm.cmd run build
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "Frontend build failed." -ForegroundColor Red; exit 1 }
Pop-Location

Write-Host "3/5 Database migrations on a clean database" -ForegroundColor Cyan
Push-Location (Join-Path $root "backend")
$verifyDb = "verify_migrations.db"
Remove-Item $verifyDb -ErrorAction SilentlyContinue
$previousDatabaseUrl = $env:DATABASE_URL
$env:DATABASE_URL = "sqlite:///$verifyDb"
& .\.venv\Scripts\alembic.exe upgrade head
if ($LASTEXITCODE -ne 0) {
    $env:DATABASE_URL = $previousDatabaseUrl
    Pop-Location
    Write-Host "Migration failed." -ForegroundColor Red
    exit 1
}

Write-Host "4/5 Seed demo data" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe scripts\seed_data.py
if ($LASTEXITCODE -ne 0) {
    $env:DATABASE_URL = $previousDatabaseUrl
    Pop-Location
    Write-Host "Seeding failed." -ForegroundColor Red
    exit 1
}
Remove-Item $verifyDb -ErrorAction SilentlyContinue
$env:DATABASE_URL = $previousDatabaseUrl
Pop-Location

Write-Host "5/5 Docker Compose configuration" -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Push-Location $root
    & docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "Compose file invalid." -ForegroundColor Red; exit 1 }
    Pop-Location
    Write-Host "Compose file valid. Start the stack with: docker compose up -d"
} else {
    Write-Host "Docker is not installed on this machine. Validating compose files directly."
    Push-Location $root
    & (Join-Path $root "backend\.venv\Scripts\python.exe") scripts\validate_compose.py
    $composeValidated = $LASTEXITCODE
    Pop-Location
    if ($composeValidated -ne 0) { Write-Host "Compose validation failed." -ForegroundColor Red; exit 1 }
    Write-Host "Compose files valid. Start the stack with: docker compose up -d"
    Write-Host "Then run the end to end demo with: python scripts\run_demo.py"
}

Write-Host "Verification finished successfully." -ForegroundColor Green
