param(
    [switch]$Json,
    [switch]$Startup
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$checks = [System.Collections.Generic.List[object]]::new()

function Add-DoctorCheck {
    param(
        [string]$Name,
        [ValidateSet("PASS", "WARN", "FAIL")]
        [string]$Status,
        [string]$Detail,
        [string]$Action = ""
    )
    $checks.Add([pscustomobject]@{
        name = $Name
        status = $Status
        detail = $Detail
        action = $Action
    })
}

function Test-LocalPort {
    param([int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(700)) {
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

function Test-HttpText {
    param(
        [string]$Url,
        [string]$ExpectedText
    )
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -lt 500 -and $response.Content -match $ExpectedText
    } catch {
        return $false
    }
}

function Get-CommandSource {
    param([string]$Name)
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    return $null
}

$python = Get-CommandSource "python"
if (-not $python) {
    Add-DoctorCheck "Python" "FAIL" "Python was not found on PATH." "Install Python 3.11+ and rerun scripts\bootstrap.ps1."
} else {
    try {
        $pythonVersionText = (& $python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>&1 | Out-String).Trim()
        $pythonVersion = [version]$pythonVersionText
        if ($pythonVersion -lt [version]"3.11") {
            Add-DoctorCheck "Python" "FAIL" "Python $pythonVersionText is too old." "Install Python 3.11 or newer."
        } else {
            Add-DoctorCheck "Python" "PASS" "Python $pythonVersionText."
        }
    } catch {
        Add-DoctorCheck "Python" "FAIL" "Python exists but its version could not be read." "Repair the Python installation."
    }
}

$node = Get-CommandSource "node"
if (-not $node) {
    Add-DoctorCheck "Node.js" "FAIL" "Node.js was not found on PATH." "Install Node.js 22+ and rerun scripts\bootstrap.ps1."
} else {
    try {
        $nodeVersionText = (& $node --version 2>&1 | Out-String).Trim().TrimStart("v")
        $nodeVersion = [version]$nodeVersionText
        if ($nodeVersion -lt [version]"22.0") {
            Add-DoctorCheck "Node.js" "FAIL" "Node.js $nodeVersionText is too old." "Install Node.js 22 or newer."
        } else {
            Add-DoctorCheck "Node.js" "PASS" "Node.js $nodeVersionText."
        }
    } catch {
        Add-DoctorCheck "Node.js" "FAIL" "Node.js exists but its version could not be read." "Repair the Node.js installation."
    }
}

$npm = Get-CommandSource "npm.cmd"
if (-not $npm) {
    $npm = Get-CommandSource "npm"
}
if ($npm) {
    Add-DoctorCheck "npm" "PASS" "npm command is available."
} else {
    Add-DoctorCheck "npm" "FAIL" "npm was not found on PATH." "Install Node.js 22+ with npm."
}

if ($python) {
    $previousPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = Join-Path $root "apps\api"
        $importOutput = (& $python -c "import fastapi, fitz, uvicorn; from app.main import app; print('ok')" 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $importOutput -match "ok") {
            Add-DoctorCheck "Backend dependencies" "PASS" "FastAPI, PyMuPDF, Uvicorn, and the NIRMIQ app import correctly."
        } else {
            Add-DoctorCheck "Backend dependencies" "FAIL" "Backend imports failed: $importOutput" "Run powershell -NoProfile -ExecutionPolicy Bypass -File scripts\bootstrap.ps1."
        }
    } catch {
        Add-DoctorCheck "Backend dependencies" "FAIL" "Backend import check failed: $($_.Exception.Message)" "Run scripts\bootstrap.ps1."
    } finally {
        $env:PYTHONPATH = $previousPythonPath
    }
}

$nextPackage = Join-Path $root "apps\web\node_modules\next\package.json"
if (Test-Path $nextPackage) {
    Add-DoctorCheck "Web dependencies" "PASS" "Next.js dependencies are installed."
} else {
    Add-DoctorCheck "Web dependencies" "FAIL" "apps\web\node_modules is incomplete." "Run powershell -NoProfile -ExecutionPolicy Bypass -File scripts\bootstrap.ps1."
}

$electronPackage = Join-Path $root "apps\desktop\node_modules\electron\package.json"
if (Test-Path $electronPackage) {
    Add-DoctorCheck "Desktop dependencies" "PASS" "Electron dependencies are installed."
} else {
    Add-DoctorCheck "Desktop dependencies" "WARN" "Electron dependencies are not installed; browser mode still works." "Run npm.cmd run desktop:install only if you need the desktop shell."
}

$requiredDirectories = @(
    "data\sqlite",
    "data\raw\uploads",
    "data\cache",
    "temp\runtime"
)
$missingDirectories = @(
    $requiredDirectories | Where-Object { -not (Test-Path (Join-Path $root $_)) }
)
if ($missingDirectories.Count -eq 0) {
    Add-DoctorCheck "Local data directories" "PASS" "App-owned data and runtime directories exist."
} else {
    Add-DoctorCheck "Local data directories" "WARN" "First-run directories will be created: $($missingDirectories -join ', ')."
}

$databasePath = Join-Path $root "data\sqlite\nirmiq.db"
if (Test-Path $databasePath) {
    $databaseSizeMb = [math]::Round((Get-Item $databasePath).Length / 1MB, 2)
    Add-DoctorCheck "SQLite corpus" "PASS" "Local database found ($databaseSizeMb MB)."
} else {
    Add-DoctorCheck "SQLite corpus" "WARN" "No local database exists yet; NIRMIQ will create one on first run."
}

if (Test-LocalPort 8000) {
    if (Test-HttpText "http://127.0.0.1:8000/health" '"status"\s*:\s*"ok"') {
        Add-DoctorCheck "API port 8000" "PASS" "A healthy NIRMIQ API is already running."
    } else {
        Add-DoctorCheck "API port 8000" "FAIL" "Port 8000 is occupied by an unhealthy or unrelated service." "Stop the process using port 8000, then start NIRMIQ again."
    }
} else {
    Add-DoctorCheck "API port 8000" "PASS" "Port 8000 is available for local startup."
}

if (Test-LocalPort 3002) {
    if (Test-HttpText "http://127.0.0.1:3002" "NIRMIQ") {
        Add-DoctorCheck "Web port 3002" "PASS" "A NIRMIQ web shell is already running."
    } else {
        Add-DoctorCheck "Web port 3002" "FAIL" "Port 3002 is occupied by an unrelated or stale web service." "Stop the process using port 3002, then start NIRMIQ again."
    }
} else {
    Add-DoctorCheck "Web port 3002" "PASS" "Port 3002 is available for local startup."
}

$apiHost = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
$unsafeOrigins = $env:WEB_ALLOWED_ORIGINS -eq "*"
$arbitraryPaths = $env:SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS -eq "true"
if ($apiHost -notin @("127.0.0.1", "localhost")) {
    Add-DoctorCheck "Local-only binding" "WARN" "API_HOST is '$apiHost', so the API may be reachable beyond this device." "Use API_HOST=127.0.0.1 for the private default."
} elseif ($unsafeOrigins) {
    Add-DoctorCheck "Local-only binding" "WARN" "WEB_ALLOWED_ORIGINS permits every origin." "Use the default localhost allowlist."
} elseif ($arbitraryPaths) {
    Add-DoctorCheck "Local-only binding" "WARN" "Arbitrary local-path ingestion is enabled." "Unset SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS outside trusted local testing."
} else {
    Add-DoctorCheck "Local-only binding" "PASS" "Default localhost binding and restricted local-path policy are active."
}

$ollama = Get-CommandSource "ollama"
if (-not $ollama) {
    Add-DoctorCheck "Ollama" "WARN" "Ollama is not installed; deterministic BM25 synthesis remains available." "Install Ollama only for improved local generation."
} elseif (Test-HttpText "http://127.0.0.1:11434/api/tags" '"models"') {
    Add-DoctorCheck "Ollama" "PASS" "The optional local model server is reachable."
} else {
    Add-DoctorCheck "Ollama" "WARN" "Ollama is installed but not currently reachable; offline fallback remains available." "Run ollama serve when you want local generation."
}

$failures = @($checks | Where-Object status -eq "FAIL")
$warnings = @($checks | Where-Object status -eq "WARN")
$result = [pscustomobject]@{
    product = "NIRMIQ Academic Intelligence"
    workspace = [string]$root
    startup_mode = [bool]$Startup
    ready = $failures.Count -eq 0
    failures = $failures.Count
    warnings = $warnings.Count
    checks = $checks
}

if ($Json) {
    $result | ConvertTo-Json -Depth 5
} else {
    Write-Output "NIRMIQ release doctor"
    Write-Output "Workspace: $root"
    Write-Output ""
    $checks | Format-Table -AutoSize status, name, detail
    if ($failures.Count -gt 0) {
        Write-Output "Required actions:"
        foreach ($failure in $failures) {
            Write-Output "- $($failure.name): $($failure.action)"
        }
    }
    if ($warnings.Count -gt 0) {
        Write-Output "Warnings are optional capabilities or first-run notes; they do not block the offline core."
    }
    Write-Output ""
    Write-Output $(if ($result.ready) { "DOCTOR PASS" } else { "DOCTOR FAIL" })
}

if (-not $result.ready) {
    exit 1
}
