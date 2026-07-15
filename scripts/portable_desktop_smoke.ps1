param(
    [string]$ArtifactPath = "dist\desktop\NIRMIQ Academic Intelligence 0.5.0.exe",
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$artifact = Join-Path $root $ArtifactPath
if (-not (Test-Path -LiteralPath $artifact)) {
    throw "Portable artifact not found. Run npm.cmd run desktop:package first."
}

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
    throw "Timed out waiting for the packaged local runtime. Run NIRMIQ Doctor and inspect local logs."
}

if ((Test-LocalPort 8000) -or (Test-LocalPort 3002)) {
    throw "Ports 8000 or 3002 are already in use. Stop the existing NIRMIQ preview before the portable smoke test."
}

$previousRoot = $env:NIRMIQ_ROOT
$portableProcess = $null
try {
    $env:NIRMIQ_ROOT = [string]$root
    $portableProcess = Start-Process `
        -FilePath $artifact `
        -WorkingDirectory (Split-Path $artifact -Parent) `
        -WindowStyle Hidden `
        -PassThru

    Write-Output "Started portable NIRMIQ process PID $($portableProcess.Id)."
    Wait-ForUrl "http://127.0.0.1:8000/health" $TimeoutSeconds
    Wait-ForUrl "http://127.0.0.1:3002" $TimeoutSeconds

    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 8
    $readiness = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/readiness" -TimeoutSec 12
    $web = Invoke-WebRequest -Uri "http://127.0.0.1:3002" -UseBasicParsing -TimeoutSec 12

    if ($health.status -ne "ok") {
        throw "Packaged backend health check failed."
    }
    if ($readiness.database -ne "ok" -or $readiness.cloud_api_required -ne $false) {
        throw "Packaged readiness did not preserve the local-first contract."
    }
    if ($web.Content -notmatch "NIRMIQ") {
        throw "Packaged web shell did not return NIRMIQ branding."
    }

    Write-Output "PASS: portable Windows executable launched the local runtime."
    Write-Output "PASS: health, SQLite readiness, offline contract, and web shell verified."
} finally {
    $env:NIRMIQ_ROOT = $previousRoot
    if ($portableProcess -and -not $portableProcess.HasExited) {
        & taskkill.exe /pid $portableProcess.Id /t /f 2>$null | Out-Null
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "stop_local.ps1") | Out-Null
}

Start-Sleep -Seconds 2
if ((Test-LocalPort 8000) -or (Test-LocalPort 3002)) {
    throw "Portable smoke cleanup left a NIRMIQ runtime port open."
}
Write-Output "PASS: portable smoke cleanup released local runtime ports."
