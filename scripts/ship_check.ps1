param(
    [switch]$SkipTests,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeDir = Join-Path $root "temp\runtime"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$verificationRunId = [guid]::NewGuid().ToString("N")
$compileCacheDir = Join-Path $root "temp\pytest-runs\$verificationRunId\compile-cache"

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

function Invoke-NativeChecked {
    param(
        [string]$Description,
        [scriptblock]$Command
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Stop-ScopedProcessTree {
    param([int]$TargetProcessId)
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $TargetProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ScopedProcessTree -TargetProcessId $child.ProcessId
    }
    Stop-Process -Id $TargetProcessId -Force -ErrorAction SilentlyContinue
}

function Invoke-BoundedNativeProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutSeconds = 300
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
    $null = $process.Handle
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-ScopedProcessTree -TargetProcessId $process.Id
        throw "$Name exceeded the ${TimeoutSeconds}s release budget. See $outLog and $errLog."
    }
    $process.WaitForExit()
    $process.Refresh()
    $exitCode = $process.ExitCode
    Get-Content $outLog -ErrorAction SilentlyContinue
    Get-Content $errLog -ErrorAction SilentlyContinue
    if ($null -eq $exitCode) {
        throw "$Name completed but did not expose an exit code. See $outLog and $errLog."
    }
    if ($exitCode -ne 0) {
        throw "$Name failed with exit code $exitCode."
    }
}

Repair-PathEnvironment
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$node = (Get-Command node.exe -ErrorAction Stop).Source
$nextBuildCli = Join-Path $root "apps\web\node_modules\next\dist\bin\next"
if (-not (Test-Path -LiteralPath $nextBuildCli)) {
    throw "Next.js build CLI not found: $nextBuildCli"
}

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
        Invoke-CheckedScript (Join-Path $PSScriptRoot "test_api.ps1")
        Push-Location $root
        try {
            New-Item -ItemType Directory -Force -Path $compileCacheDir | Out-Null
            Invoke-NativeChecked "API compile" {
                python -X "pycache_prefix=$compileCacheDir" -m compileall -q apps/api/app
            }
        } finally {
            Pop-Location
        }
    }

    if (-not $SkipBuild) {
        Invoke-BoundedNativeProcess `
            -Name "web-build" `
            -FilePath $node `
            -Arguments @($nextBuildCli, "build") `
            -WorkingDirectory (Join-Path $root "apps\web") `
            -TimeoutSeconds 300
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
            -FilePath $npm `
            -Arguments @("run", "dev") `
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
    if ($started.Count -gt 0) {
        powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "stop_local.ps1") | Out-Null
    }
}
