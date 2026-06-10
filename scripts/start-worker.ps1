$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Run: uv sync --extra dev"
    exit 1
}

New-Item -ItemType Directory -Force -Path "logs" | Out-Null
$stdout = Join-Path $Root "logs\worker.log"
$stderr = Join-Path $Root "logs\worker.err.log"
New-Item -ItemType File -Force -Path $stdout | Out-Null
New-Item -ItemType File -Force -Path $stderr | Out-Null

$process = Start-Process `
    -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList @("-m", "syntra.worker") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Syntra worker started. PID: $($process.Id)"
Write-Host "Logs: logs\worker.log and logs\worker.err.log"
