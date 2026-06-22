param(
    [string]$CacheDir = ""
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$tempRoot = Join-Path $root "temp\pytest"
if (-not $CacheDir) {
    $CacheDir = Join-Path $root "temp\pytest-cache"
}

New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

$env:PYTHONPATH = "apps/api"
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
$env:TMPDIR = $tempRoot
$env:USE_OLLAMA_GENERATION = "false"
$env:USE_OLLAMA_EMBEDDINGS = "false"
$env:USE_OLLAMA_RERANKER = "false"
$env:LOW_MEMORY_MODE = "true"
$env:SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS = "true"

Push-Location $root
try {
    python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q -o "cache_dir=$CacheDir"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
