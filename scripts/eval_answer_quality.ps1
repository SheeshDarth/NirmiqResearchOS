param(
    [string]$Dataset = "data\processed\eval\real_world_answer_quality.jsonl",
    [string]$MetricsOutput = "data\processed\eval\real_world_answer_quality_metrics.json",
    [string]$FailuresOutput = "data\processed\eval\real_world_answer_quality_failures.jsonl",
    [string[]]$Modes = @("hybrid", "bm25"),
    [int]$SlowestSamples = 5,
    [double]$WarnTotalSeconds = 0,
    [double]$WarnSourceResolutionSeconds = 0,
    [double]$WarnP95SampleSeconds = 0,
    [switch]$UseOllama
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not $UseOllama) {
    $env:USE_OLLAMA_GENERATION = "false"
}
$env:USE_OLLAMA_EMBEDDINGS = "false"
$env:USE_OLLAMA_RERANKER = "false"
$env:LOW_MEMORY_MODE = "true"

$argsList = @(
    "scripts/eval_retrieval.py",
    "--dataset", $Dataset,
    "--auto-ingest-sources",
    "--full-query",
    "--k", "3", "5", "8",
    "--modes"
)
$argsList += $Modes
$argsList += @(
    "--output", $MetricsOutput,
    "--failures-output", $FailuresOutput,
    "--slowest-samples", [string]$SlowestSamples
)
if ($WarnTotalSeconds -gt 0) {
    $argsList += @("--warn-total-seconds", [string]$WarnTotalSeconds)
}
if ($WarnSourceResolutionSeconds -gt 0) {
    $argsList += @(
        "--warn-source-resolution-seconds",
        [string]$WarnSourceResolutionSeconds
    )
}
if ($WarnP95SampleSeconds -gt 0) {
    $argsList += @("--warn-p95-sample-seconds", [string]$WarnP95SampleSeconds)
}

python @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
