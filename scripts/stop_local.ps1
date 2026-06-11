$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeDir = Join-Path $root "temp\runtime"

function Stop-ProcessTree {
    param([int]$ProcessId)
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
    }
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        Write-Output "Stopped process PID $ProcessId."
    }
}

function Stop-NirmiqWebFallback {
    $webPathPattern = "*Nirmiq-researchOS*apps*web*next*"
    $webProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like $webPathPattern }
    foreach ($process in $webProcesses) {
        Stop-ProcessTree -ProcessId ([int]$process.ProcessId)
    }
}

function Stop-NirmiqApiFallback {
    $apiProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*uvicorn app.main:app*" -and $_.CommandLine -like "*--port 8000*" }
    foreach ($process in $apiProcesses) {
        Stop-ProcessTree -ProcessId ([int]$process.ProcessId)
    }
}

if (-not (Test-Path $runtimeDir)) {
    Write-Output "No NIRMIQ runtime directory found."
} else {
    foreach ($name in @("web", "api")) {
        $pidFile = Join-Path $runtimeDir "$name.pid"
        if (-not (Test-Path $pidFile)) {
            Write-Output "No PID file for $name."
            continue
        }
        $processId = [int](Get-Content $pidFile | Select-Object -First 1)
        Stop-ProcessTree -ProcessId $processId
        Remove-Item -Path $pidFile -Force
    }
}

Stop-NirmiqWebFallback
Stop-NirmiqApiFallback

Write-Output "NIRMIQ local preview processes stopped where PID files matched."
