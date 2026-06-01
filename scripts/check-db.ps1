$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$line = Get-Content ".env" | Where-Object { $_ -match "^DATABASE_URL=" } | Select-Object -First 1
if (-not $line) {
    Write-Host "DATABASE_URL missing from .env"
    exit 1
}

$dbUrl = ($line -replace "^DATABASE_URL=") -replace "^postgresql\+psycopg://", "postgresql://"
$uri = [System.Uri]$dbUrl
$userInfo = $uri.UserInfo.Split(":", 2)
$env:PGPASSWORD = [System.Uri]::UnescapeDataString($userInfo[1])
$database = $uri.AbsolutePath.TrimStart("/")

& "C:\Program Files\PostgreSQL\17\bin\psql.exe" `
    -h $uri.Host `
    -p $uri.Port `
    -U $userInfo[0] `
    -d $database `
    -c "SELECT current_database(), current_schema();" `
    -c "\dt public.*" `
    -c "SELECT id, name, repository_url, default_branch FROM public.projects;"
