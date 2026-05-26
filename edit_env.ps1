$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path "$appRoot\.env")) { Copy-Item "$appRoot\.env.example" "$appRoot\.env" -Force }
notepad "$appRoot\.env"
