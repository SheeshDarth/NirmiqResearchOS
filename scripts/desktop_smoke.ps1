param(
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$desktopDir = Join-Path $root "apps\desktop"
$runtimeDir = Join-Path $root "temp\runtime"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Test-LocalPort {
    param([int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(600)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [int]$Seconds
    )
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 4 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Url"
}

function Stop-ProcessTree {
    param([int]$ProcessId)
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
    }
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        Write-Output "Stopped desktop smoke process PID $ProcessId."
    }
}

function Stop-SmokeStartedRuntime {
    param([string[]]$Names)
    foreach ($pidFile in Get-ChildItem -Path $runtimeDir -Filter "*.desktop.pid" -File -ErrorAction SilentlyContinue) {
        $serviceName = $pidFile.Name -replace "\.desktop\.pid$", ""
        if ($Names -notcontains $serviceName) {
            continue
        }
        $rawPid = Get-Content $pidFile.FullName -ErrorAction SilentlyContinue | Select-Object -First 1
        $processId = 0
        if ([int]::TryParse([string]$rawPid, [ref]$processId)) {
            Stop-ProcessTree -ProcessId $processId
        }
        Remove-Item -Path $pidFile.FullName -Force -ErrorAction SilentlyContinue
    }
}

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
if (-not (Test-Path $electronBin)) {
    throw "Desktop dependencies are missing. Run: npm.cmd run desktop:install"
}

$apiWasOpen = Test-LocalPort 8000
$webWasOpen = Test-LocalPort 3002
$outLog = Join-Path $runtimeDir "desktop-smoke.out.log"
$errLog = Join-Path $runtimeDir "desktop-smoke.err.log"

Write-Output "NIRMIQ desktop smoke check"
Write-Output "Existing API port: $apiWasOpen"
Write-Output "Existing web port: $webWasOpen"

$desktopProcess = $null
try {
    $desktopProcess = Start-Process `
        -FilePath $npm `
        -ArgumentList @("--prefix", $desktopDir, "run", "start") `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru

    Write-Output "Started desktop smoke process PID $($desktopProcess.Id)."
    Wait-ForUrl "http://127.0.0.1:8000/health" $TimeoutSeconds
    Wait-ForUrl "http://127.0.0.1:3002" $TimeoutSeconds

    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 8
    if ($health.status -ne "ok") {
        throw "Backend health failed: $($health | ConvertTo-Json -Compress)"
    }

    $readiness = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/readiness" -Method Get -TimeoutSec 12
    if ($readiness.database -ne "ok") {
        throw "Readiness database failed: $($readiness | ConvertTo-Json -Compress)"
    }

    $web = Invoke-WebRequest -Uri "http://127.0.0.1:3002" -UseBasicParsing -TimeoutSec 12
    if ($web.Content -notmatch "NIRMIQ") {
        throw "Web shell loaded, but NIRMIQ branding was not detected."
    }

    Write-Output "PASS: desktop launched local runtime."
    Write-Output "PASS: backend health ok."
    Write-Output "PASS: readiness database = $($readiness.database), cloud_api_required = $($readiness.cloud_api_required)."
    Write-Output "PASS: web shell returned NIRMIQ branding."
} finally {
    if ($desktopProcess -and -not $desktopProcess.HasExited) {
        Stop-ProcessTree -ProcessId $desktopProcess.Id
    }
    $startedBySmoke = @()
    if (-not $apiWasOpen) { $startedBySmoke += "api" }
    if (-not $webWasOpen) { $startedBySmoke += "web" }
    if ($startedBySmoke.Count -gt 0) {
        Stop-SmokeStartedRuntime -Names $startedBySmoke
    }
}
