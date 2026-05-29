$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\\apps\\api")
python -m pip install -e .

Set-Location (Join-Path $PSScriptRoot "..\\apps\\web")
npm install

Write-Output "Bootstrap complete."

