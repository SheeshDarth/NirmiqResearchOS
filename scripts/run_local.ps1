param(
    [switch]$OpenBrowser,
    [switch]$GoldenDemo
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
        [int]$Seconds = 45
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

function Start-NirmiqProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )
    $outLog = Join-Path $runtimeDir "$Name.out.log"
    $errLog = Join-Path $runtimeDir "$Name.err.log"
    $pidFile = Join-Path $runtimeDir "$Name.pid"
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru
    Set-Content -Path $pidFile -Value $process.Id
    Write-Output "Started $Name with PID $($process.Id)"
}

Repair-PathEnvironment
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source

$apiUrl = "http://127.0.0.1:8000"
$webUrl = "http://127.0.0.1:3002"

Write-Output "NIRMIQ local preview launcher"
Write-Output "Workspace: $root"

if (Test-LocalPort 8000) {
    Write-Output "API already listening on $apiUrl"
} else {
    Start-NirmiqProcess `
        -Name "api" `
        -FilePath "python" `
        -Arguments @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory (Join-Path $root "apps\api")
}

if (Test-LocalPort 3002) {
    Write-Output "Web app already listening on $webUrl"
} else {
    Start-NirmiqProcess `
        -Name "web" `
        -FilePath $npm `
        -Arguments @("run", "dev") `
        -WorkingDirectory (Join-Path $root "apps\web")
}

Wait-ForUrl "$apiUrl/health" 45
Wait-ForUrl $webUrl 60

if ($GoldenDemo) {
    $env:NIRMIQ_API_BASE = $apiUrl
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "golden_demo.ps1")
}

Write-Output "NIRMIQ is ready."
Write-Output "Open: $webUrl"
Write-Output "API:  $apiUrl"
Write-Output "Logs: $runtimeDir"

if ($OpenBrowser) {
    Start-Process $webUrl
}
