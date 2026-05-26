$ErrorActionPreference = "Continue"

Set-Location -LiteralPath "C:\Users\segun\Google Drive\MUSIC_BOX\APP\musicbox_discogs_api"

Write-Host ""
Write-Host "============================================================"
Write-Host "MUSICBOX DISCOGS API - SERVIDOR"
Write-Host "============================================================"
Write-Host "No cierres esta ventana mientras uses Swagger o la API."
Write-Host "URL: http://127.0.0.1:8765/docs"
Write-Host "============================================================"
Write-Host ""

.\run_api.ps1

Write-Host ""
Write-Host "El servidor se ha detenido."
Read-Host "Pulsa ENTER para cerrar esta ventana"
