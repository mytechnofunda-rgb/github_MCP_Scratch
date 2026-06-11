# GitHub MCP Server — Windows setup script
param(
    [switch]$NoVenv
)

$ErrorActionPreference = "Stop"

Write-Host "=== GitHub MCP Server Setup ===" -ForegroundColor Cyan

# Create virtual environment
if (-not $NoVenv) {
    if (-not (Test-Path ".venv")) {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv .venv
    }
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1"
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Copy .env if missing
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "[!] .env created from template. Set your GITHUB_TOKEN before running." -ForegroundColor Red
} else {
    Write-Host ".env already exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Run the server with:  python server.py"
Write-Host "Or via MCP CLI:       mcp run server.py"
