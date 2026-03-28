# Contoso HR Agent — Windows Setup
# Requires: Python 3.11+, uv (https://docs.astral.sh/uv/getting-started/installation/)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n=== Contoso HR Agent Setup ===" -ForegroundColor Cyan

# Check uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: 'uv' not found. Install from https://docs.astral.sh/uv/" -ForegroundColor Red
    exit 1
}

# Create .env if missing
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[!] Created .env from .env.example — edit it with your Azure AI Foundry credentials" -ForegroundColor Yellow
}

# Create venv and sync dependencies
Write-Host "`n[1/4] Creating virtual environment..." -ForegroundColor Green
uv venv

Write-Host "`n[2/4] Installing dependencies..." -ForegroundColor Green
uv sync --all-extras

# Create runtime directories
Write-Host "`n[3/4] Creating runtime directories..." -ForegroundColor Green
$dirs = @("data\incoming", "data\processed", "data\knowledge", "data\chroma", "data\outgoing")
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# Seed knowledge base
Write-Host "`n[4/4] Seeding HR policy knowledge base..." -ForegroundColor Green
uv run hr-seed

Write-Host "`n=== Setup Complete ===" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Edit .env with your Azure AI Foundry credentials"
Write-Host "  2. Run: .\scripts\start.ps1"
Write-Host "  3. Open: http://localhost:8080/chat.html"
