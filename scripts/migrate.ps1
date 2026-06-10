$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Run: uv sync --extra dev"
    exit 1
}

& ".\.venv\Scripts\python.exe" -m syntra.db.migrate
