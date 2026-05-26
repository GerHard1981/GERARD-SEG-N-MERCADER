# MusicBox Discogs API - run local server
$ErrorActionPreference = "Stop"

$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $appRoot

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env" -Force
    Write-Host "Creado .env desde .env.example"
    Write-Host "Edita .env y pega DISCOGS_TOKEN antes de usar endpoints autenticados."
}

if (-not (Test-Path ".\.venv")) {
    py -3 -m venv .venv
}

. ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

$env:PYTHONPATH = $appRoot
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
