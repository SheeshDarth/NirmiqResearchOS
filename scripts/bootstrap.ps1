$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\\apps\\api")
python -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    throw "API dependency install failed with exit code $LASTEXITCODE."
}

Set-Location (Join-Path $PSScriptRoot "..\\apps\\web")
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
& $npm install
if ($LASTEXITCODE -ne 0) {
    throw "Web dependency install failed with exit code $LASTEXITCODE."
}

Write-Output "Bootstrap complete."
