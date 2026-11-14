# Start TrustMed. Requires the report service to be running already.
#
#   .\trustmed\run.ps1                      # MedGemma on the default host
#   .\trustmed\run.ps1 -Name cxr            # label the UI for CXR-LLaVA
#   .\trustmed\run.ps1 -Port 8010 -Backend http://10.10.10.28:8000

param(
    [int]$Port = 8010,
    [string]$Backend = "http://10.10.10.28:8000",
    [string]$Name = "medgemma",
    [string]$Python = "metrics-venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $env:TRUSTMED_API_KEY -and (Test-Path "deploy\api.key")) {
    $env:TRUSTMED_API_KEY = (Get-Content "deploy\api.key" -Raw).Trim()
}

$env:PYTHONPATH       = "."
$env:PYTHONIOENCODING = "utf-8"
$env:TQDM_DISABLE     = "1"
$env:TRUSTMED_BACKEND = $Backend
$env:TRUSTMED_BACKEND_NAME = $Name

Write-Host "TrustMed -> http://127.0.0.1:$Port  (backend $Backend, label $Name)"
& $Python -m uvicorn trustmed.main:app --host 0.0.0.0 --port $Port --log-level info
