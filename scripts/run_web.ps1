$ErrorActionPreference = "Stop"

$pathValue = [System.Environment]::GetEnvironmentVariable("Path", "Process")
if (-not $pathValue) {
    $pathValue = [System.Environment]::GetEnvironmentVariable("PATH", "Process")
}
[System.Environment]::SetEnvironmentVariable("PATH", $null, "Process")
[System.Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")

Set-Location (Join-Path $PSScriptRoot "..\\apps\\web")
npm run dev
