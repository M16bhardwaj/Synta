param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Run: uv sync --extra dev"
    exit 1
}

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existing) {
    Write-Host "Syntra or another process is already listening on port $Port. PID: $($existing.OwningProcess)"
    Write-Host "Health: http://localhost:$Port/health"
    exit 0
}

New-Item -ItemType Directory -Force -Path "logs" | Out-Null
$stdout = Join-Path $Root "logs\syntra.log"
$stderr = Join-Path $Root "logs\syntra.err.log"
New-Item -ItemType File -Force -Path $stdout | Out-Null
New-Item -ItemType File -Force -Path $stderr | Out-Null

$process = Start-Process `
    -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList @("-m", "uvicorn", "syntra.main:app", "--host", "0.0.0.0", "--port", "$Port") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 3
Write-Host "Syntra started. PID: $($process.Id)"
Write-Host "Health: http://localhost:$Port/health"
Write-Host "Logs: logs\syntra.log and logs\syntra.err.log"
