param(
    [string]$CacheDir = ""
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$runId = [Guid]::NewGuid().ToString("N")
$tempRoot = Join-Path $root "temp\pytest-runs\$runId"
$pytestBaseTemp = Join-Path $tempRoot "pytest"
if (-not $CacheDir) {
    $CacheDir = Join-Path $root "temp\pytest-cache-runs\$runId"
}

New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

$env:PYTHONPATH = "apps/api"
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:TMPDIR = $tempRoot
$env:NIRMIQ_TEST_RUNTIME_ROOT = Join-Path $tempRoot "api-runtime"
$env:USE_OLLAMA_GENERATION = "false"
$env:USE_OLLAMA_EMBEDDINGS = "false"
$env:USE_OLLAMA_RERANKER = "false"
$env:LOW_MEMORY_MODE = "true"
$env:SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS = "true"
New-Item -ItemType Directory -Force -Path $env:NIRMIQ_TEST_RUNTIME_ROOT | Out-Null

Push-Location $root
try {
    python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q --basetemp "$pytestBaseTemp" -o "cache_dir=$CacheDir"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
