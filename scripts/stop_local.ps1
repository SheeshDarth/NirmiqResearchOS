$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeDir = Join-Path $root "temp\runtime"
$desktopDir = Join-Path $root "temp\desktop"

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
    $escapedRoot = [WildcardPattern]::Escape([string]$root)
    $webPathPattern = "*$escapedRoot*apps*web*"
    $webProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like $webPathPattern -and ($_.CommandLine -like "*next*" -or $_.CommandLine -like "*npm*run*") }
    foreach ($process in $webProcesses) {
        Stop-ProcessTree -ProcessId ([int]$process.ProcessId)
    }
}

function Stop-NirmiqApiFallback {
    $escapedRoot = [WildcardPattern]::Escape([string]$root)
    $apiProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*uvicorn app.main:app*" -and $_.CommandLine -like "*--port 8000*" -and $_.CommandLine -like "*$escapedRoot*" }
    foreach ($process in $apiProcesses) {
        Stop-ProcessTree -ProcessId ([int]$process.ProcessId)
    }
}

foreach ($pidDir in @($runtimeDir, $desktopDir)) {
    if (-not (Test-Path $pidDir)) {
        Write-Output "No NIRMIQ PID directory found: $pidDir"
        continue
    }
    foreach ($pidFile in Get-ChildItem -Path $pidDir -Filter "*.pid" -File -ErrorAction SilentlyContinue) {
        $rawPid = Get-Content $pidFile.FullName -ErrorAction SilentlyContinue | Select-Object -First 1
        $processId = 0
        if (-not [int]::TryParse([string]$rawPid, [ref]$processId)) {
            Write-Output "Ignoring invalid PID file: $($pidFile.FullName)"
            Remove-Item -Path $pidFile.FullName -Force -ErrorAction SilentlyContinue
            continue
        }
        Stop-ProcessTree -ProcessId $processId
        Remove-Item -Path $pidFile.FullName -Force -ErrorAction SilentlyContinue
    }
}

Stop-NirmiqWebFallback
Stop-NirmiqApiFallback

Write-Output "NIRMIQ local preview processes stopped where PID files matched."
