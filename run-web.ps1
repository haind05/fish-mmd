$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    throw 'Chua co .venv. Hay cai moi truong theo README.md truoc.'
}

docker compose up -d --wait
if ($LASTEXITCODE -ne 0) {
    throw 'Khong khoi dong duoc PostgreSQL. Hay mo Docker Desktop va thu lai.'
}

Write-Host 'Mo trinh duyet tai http://127.0.0.1:8000. Nhan Ctrl+C de dung web.'
& .venv/Scripts/python.exe -m fish_features.web
exit $LASTEXITCODE
