param(
    [string]$Manifest = "data\processed\eval\generalization_gate.json",
    [string]$Dataset = "",
    [string]$MetricsOutput = "",
    [string]$FailuresOutput = "",
    [string]$GateReportOutput = "",
    [string[]]$Modes = @(),
    [switch]$UseOllama
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$evalRoot = [System.IO.Path]::GetFullPath((Join-Path $root "temp\generalization-gate-eval"))
$safeTempRoot = [System.IO.Path]::GetFullPath((Join-Path $root "temp"))
if (-not $evalRoot.StartsWith($safeTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Generalization gate evaluation storage must remain under the workspace temp directory."
}

if (Test-Path -LiteralPath $evalRoot) {
    Remove-Item -LiteralPath $evalRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $evalRoot | Out-Null

$manifestJson = Get-Content -Raw -Path $Manifest | ConvertFrom-Json
if (-not $Dataset) {
    $Dataset = [string]$manifestJson.dataset_path
}
if (-not $MetricsOutput) {
    $MetricsOutput = [string]$manifestJson.metrics_path
}
if (-not $FailuresOutput) {
    $FailuresOutput = [string]$manifestJson.failures_path
}
if (-not $GateReportOutput) {
    $GateReportOutput = [string]$manifestJson.report_path
}
if ($Modes.Count -eq 0) {
    $Modes = @([string]$manifestJson.mode)
}

if (-not $UseOllama) {
    $env:USE_OLLAMA_GENERATION = "false"
}
$env:PYTHONPATH = "apps/api"
$env:PYTHONPYCACHEPREFIX = Join-Path $evalRoot "pycache"
$env:SQLITE_PATH = Join-Path $evalRoot "sqlite\nirmiq-generalization.db"
$env:CHROMA_PATH = Join-Path $evalRoot "chroma"
$env:UPLOAD_PATH = Join-Path $evalRoot "uploads"
$env:PARSE_CACHE_PATH = Join-Path $evalRoot "parse-cache"
$env:DIAGRAM_PATH = Join-Path $evalRoot "diagrams"
$env:USE_OLLAMA_EMBEDDINGS = "false"
$env:USE_OLLAMA_RERANKER = "false"
$env:RETRIEVAL_ENABLE_VECTOR = "false"
$env:LOW_MEMORY_MODE = "true"

$candidateMetrics = Join-Path $evalRoot "generalization-gate-metrics.json"
$candidateFailures = Join-Path $evalRoot "generalization-gate-failures.jsonl"
$candidateReport = Join-Path $evalRoot "generalization-gate-report.json"

function Publish-EvaluationArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $destinationDirectory = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null

    $payload = [System.IO.File]::ReadAllBytes([System.IO.Path]::GetFullPath($Source))
    if (Test-Path -LiteralPath $Destination) {
        $existingPayload = [System.IO.File]::ReadAllBytes(
            [System.IO.Path]::GetFullPath($Destination)
        )
        if ([System.Collections.StructuralComparisons]::StructuralEqualityComparer.Equals(
            $payload,
            $existingPayload
        )) {
            return
        }
    }

    $destinationPath = [System.IO.Path]::GetFullPath($Destination)
    $lastError = $null
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            [System.IO.File]::WriteAllBytes($destinationPath, $payload)
            return
        }
        catch {
            $lastError = $_
            if ($attempt -lt 5) {
                Start-Sleep -Milliseconds (200 * $attempt)
            }
        }
    }
    $isAccessDenied =
        ($lastError.Exception -is [System.UnauthorizedAccessException]) -or
        ($lastError.Exception.InnerException -is [System.UnauthorizedAccessException])
    if ($isAccessDenied) {
        Write-Warning "Could not publish optional evaluation artifact '$Destination'; the validated candidate remains at '$Source'."
        return
    }
    throw $lastError
}

$evalArgs = @(
    "scripts/eval_retrieval.py",
    "--dataset", $Dataset,
    "--auto-ingest-sources",
    "--full-query",
    "--k", "3", "5", "8",
    "--modes"
)
$evalArgs += $Modes
$evalArgs += @(
    "--output", $candidateMetrics,
    "--failures-output", $candidateFailures
)

python @evalArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python scripts/validate_eval_gate.py `
    --manifest $Manifest `
    --dataset $Dataset `
    --metrics $candidateMetrics `
    --output $candidateReport
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Publish-EvaluationArtifact -Source $candidateMetrics -Destination $MetricsOutput
Publish-EvaluationArtifact -Source $candidateFailures -Destination $FailuresOutput
Publish-EvaluationArtifact -Source $candidateReport -Destination $GateReportOutput
