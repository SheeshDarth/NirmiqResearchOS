param(
    [switch]$SkipTests,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeDir = Join-Path $root "temp\runtime"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Repair-PathEnvironment {
    $pathValue = [System.Environment]::GetEnvironmentVariable("Path", "Process")
    if (-not $pathValue) {
        $pathValue = [System.Environment]::GetEnvironmentVariable("PATH", "Process")
    }
    [System.Environment]::SetEnvironmentVariable("PATH", $null, "Process")
    [System.Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
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
        [int]$Seconds = 60
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

function Start-ScopedProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )
    $outLog = Join-Path $runtimeDir "$Name.ship.out.log"
    $errLog = Join-Path $runtimeDir "$Name.ship.err.log"
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru
    Write-Host "Started $Name for ship check with PID $($process.Id)"
    return $process
}

function Invoke-CheckedScript {
    param(
        [string]$ScriptPath
    )
    powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Script failed with exit code ${LASTEXITCODE}: $ScriptPath"
    }
}

Repair-PathEnvironment

$started = @()
$apiBase = "http://127.0.0.1:8000"
$webBase = "http://127.0.0.1:3002"

try {
    Write-Output "Stopping any existing NIRMIQ preview before build/check..."
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "stop_local.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to stop existing NIRMIQ preview before ship check."
    }

    if (-not $SkipTests) {
        Push-Location $root
        $env:PYTHONPATH = "apps/api"
        $env:TEMP = Join-Path $root "temp\pytest"
        $env:TMP = $env:TEMP
        $env:TMPDIR = $env:TEMP
        New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
        python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q -o "cache_dir=$root\temp\pytest-cache"
        python -m compileall apps/api/app
        Pop-Location
    }

    if (-not $SkipBuild) {
        Push-Location (Join-Path $root "apps\web")
        npm run build
        Pop-Location
    }

    if (-not (Test-LocalPort 8000)) {
        $started += Start-ScopedProcess `
            -Name "api" `
            -FilePath "python" `
            -Arguments @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
            -WorkingDirectory (Join-Path $root "apps\api")
    }

    if (-not (Test-LocalPort 3002)) {
        $started += Start-ScopedProcess `
            -Name "web" `
            -FilePath "cmd.exe" `
            -Arguments @("/c", "npm run dev") `
            -WorkingDirectory (Join-Path $root "apps\web")
    }

    Wait-ForUrl "$apiBase/health" 60
    Wait-ForUrl $webBase 90

    $env:NIRMIQ_API_BASE = $apiBase
    $env:NIRMIQ_WEB_BASE = $webBase
    Invoke-CheckedScript (Join-Path $PSScriptRoot "publish_smoke.ps1")
    Invoke-CheckedScript (Join-Path $PSScriptRoot "golden_demo.ps1")

    Write-Output "SHIP CHECK PASS: tests/build/smoke/golden demo completed."
} finally {
    foreach ($process in $started) {
        if ($process -and $process.Id -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Write-Output "Stopped scoped process PID $($process.Id)."
        }
    }
}
