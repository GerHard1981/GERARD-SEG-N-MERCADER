# MusicBox Discogs API - basic checks
$ErrorActionPreference = "Stop"

Write-Host "HEALTH"
Invoke-RestMethod "http://127.0.0.1:8765/health" | ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "DISCOGS CONFIG"
Invoke-RestMethod "http://127.0.0.1:8765/api/discogs/config" | ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "MUSIC SUMMARY"
Invoke-RestMethod "http://127.0.0.1:8765/api/music/summary" | ConvertTo-Json -Depth 8

Write-Host ""
Write-Host "TEST SEARCH: Scooter"
Invoke-RestMethod "http://127.0.0.1:8765/api/discogs/search?q=Scooter&type=release&per_page=3" | ConvertTo-Json -Depth 10
