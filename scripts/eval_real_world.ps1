param(
    [string]$Dataset = "data\processed\eval\real_world_academic_seed.jsonl",
    [string]$MetricsOutput = "",
    [string]$FailuresOutput = "",
    [switch]$FullQuery
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$env:USE_OLLAMA_GENERATION = "false"
$env:USE_OLLAMA_EMBEDDINGS = "false"
$env:USE_OLLAMA_RERANKER = "false"
$env:LOW_MEMORY_MODE = "true"

if (-not $MetricsOutput) {
    $MetricsOutput = if ($FullQuery) {
        "data\processed\eval\real_world_full_query_metrics.json"
    } else {
        "data\processed\eval\real_world_retrieval_metrics.json"
    }
}

if (-not $FailuresOutput) {
    $FailuresOutput = if ($FullQuery) {
        "data\processed\eval\real_world_full_query_failures.jsonl"
    } else {
        "data\processed\eval\real_world_retrieval_failures.jsonl"
    }
}

$argsList = @(
    "scripts/eval_retrieval.py",
    "--dataset", $Dataset,
    "--auto-ingest-sources",
    "--k", "3", "5", "8",
    "--modes", "hybrid", "bm25",
    "--output", $MetricsOutput
)
if ($FailuresOutput) { $argsList += "--failures-output"; $argsList += $FailuresOutput }
if ($FullQuery) { $argsList += "--full-query" }

python @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
