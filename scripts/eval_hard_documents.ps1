param(
    [string]$FixtureDirectory = "temp\hard-document-fixtures",
    [string]$MetricsOutput = "data\processed\eval\hard_document_metrics.json",
    [string]$FailuresOutput = "data\processed\eval\hard_document_failures.jsonl",
    [string]$ReportOutput = "data\processed\eval\hard_document_pipeline_report.json"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$fixtureRoot = [System.IO.Path]::GetFullPath((Join-Path $root $FixtureDirectory))
$evalRoot = [System.IO.Path]::GetFullPath((Join-Path $root "temp\hard-document-eval"))
$safeTempRoot = [System.IO.Path]::GetFullPath((Join-Path $root "temp"))
if (-not $fixtureRoot.StartsWith($safeTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Hard-document fixtures must remain under the workspace temp directory."
}
if (-not $evalRoot.StartsWith($safeTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Hard-document evaluation storage must remain under the workspace temp directory."
}

if (Test-Path -LiteralPath $evalRoot) {
    Remove-Item -LiteralPath $evalRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $fixtureRoot, $evalRoot | Out-Null

python scripts/generate_hard_document_fixtures.py --output-dir $fixtureRoot
if ($LASTEXITCODE -ne 0) {
    throw "Hard-document fixture generation failed."
}

$env:PYTHONPATH = "apps/api"
$env:PYTHONPYCACHEPREFIX = Join-Path $evalRoot "pycache"
$env:SQLITE_PATH = Join-Path $evalRoot "sqlite\nirmiq-hard-docs.db"
$env:CHROMA_PATH = Join-Path $evalRoot "chroma"
$env:UPLOAD_PATH = Join-Path $evalRoot "uploads"
$env:PARSE_CACHE_PATH = Join-Path $evalRoot "parse-cache"
$env:DIAGRAM_PATH = Join-Path $evalRoot "diagrams"
$env:USE_OLLAMA_GENERATION = "false"
$env:USE_OLLAMA_EMBEDDINGS = "false"
$env:USE_OLLAMA_RERANKER = "false"
$env:RETRIEVAL_ENABLE_VECTOR = "false"
$env:LOW_MEMORY_MODE = "true"
$env:SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS = "true"

$candidateMetrics = Join-Path $evalRoot "hard-document-metrics.json"
$candidateFailures = Join-Path $evalRoot "hard-document-failures.jsonl"
$candidateReport = Join-Path $evalRoot "hard-document-pipeline-report.json"

function Publish-EvaluationArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $sourceBytes = [System.IO.File]::ReadAllBytes($Source)
    if (Test-Path -LiteralPath $Destination) {
        $destinationBytes = [System.IO.File]::ReadAllBytes($Destination)
        if (
            $sourceBytes.Length -eq $destinationBytes.Length -and
            [System.Convert]::ToBase64String($sourceBytes) -eq
                [System.Convert]::ToBase64String($destinationBytes)
        ) {
            return
        }
    }

    $destinationDirectory = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
    [System.IO.File]::WriteAllBytes(
        $Destination,
        $sourceBytes
    )
}

python scripts/eval_retrieval.py `
    --dataset data/processed/eval/hard_document_qa.jsonl `
    --auto-ingest-sources `
    --full-query `
    --k 3 5 8 `
    --modes bm25 `
    --output $candidateMetrics `
    --failures-output $candidateFailures
if ($LASTEXITCODE -ne 0) {
    throw "Hard-document retrieval evaluation failed."
}

python scripts/verify_hard_document_pipeline.py `
    --fixture-dir $fixtureRoot `
    --metrics $candidateMetrics `
    --report $candidateReport
if ($LASTEXITCODE -ne 0) {
    throw "Hard-document pipeline verification failed."
}

Publish-EvaluationArtifact -Source $candidateMetrics -Destination $MetricsOutput
Publish-EvaluationArtifact -Source $candidateFailures -Destination $FailuresOutput
Publish-EvaluationArtifact -Source $candidateReport -Destination $ReportOutput

Write-Output "HARD DOCUMENT CHECK PASS"
