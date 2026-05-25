# ScholarHive AI verification script (Windows)
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"

if (-not (Test-Path ".venv")) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
$env:DATABASE_URL = "sqlite:///./test_verify.db"
pytest tests/ -v
Write-Host "`nHealth check (start server separately for live test):"
Write-Host "  curl http://localhost:8000/health"
