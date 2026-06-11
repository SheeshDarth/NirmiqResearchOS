$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeDir = Join-Path $root "temp\runtime"

if (-not (Test-Path $runtimeDir)) {
    Write-Output "No NIRMIQ runtime directory found."
    exit 0
}

foreach ($name in @("web", "api")) {
    $pidFile = Join-Path $runtimeDir "$name.pid"
    if (-not (Test-Path $pidFile)) {
        Write-Output "No PID file for $name."
        continue
    }
    $processId = [int](Get-Content $pidFile | Select-Object -First 1)
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $processId -Force
        Write-Output "Stopped $name process PID $processId."
    } else {
        Write-Output "$name PID $processId is not running."
    }
    Remove-Item -Path $pidFile -Force
}

Write-Output "NIRMIQ local preview processes stopped where PID files matched."
