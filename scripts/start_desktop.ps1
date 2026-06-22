param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$desktopDir = Join-Path $root "apps\desktop"

function Repair-PathEnvironment {
    $pathValue = [System.Environment]::GetEnvironmentVariable("Path", "Process")
    if (-not $pathValue) {
        $pathValue = [System.Environment]::GetEnvironmentVariable("PATH", "Process")
    }
    [System.Environment]::SetEnvironmentVariable("PATH", $null, "Process")
    [System.Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
}

Repair-PathEnvironment

$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$electronBin = Join-Path $desktopDir "node_modules\.bin\electron.cmd"

if ($Install -and -not (Test-Path $electronBin)) {
    Write-Output "Installing NIRMIQ desktop dependencies..."
    & $npm install --prefix $desktopDir
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path $electronBin)) {
    Write-Output "NIRMIQ desktop dependencies are not installed yet."
    Write-Output ""
    Write-Output "Run this once:"
    Write-Output "  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_desktop.ps1 -Install"
    Write-Output ""
    Write-Output "Then launch the desktop app with:"
    Write-Output "  npm run desktop"
    exit 1
}

Write-Output "Starting NIRMIQ desktop app..."
& $npm --prefix $desktopDir run start
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
