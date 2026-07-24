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
Set-Location (Join-Path $PSScriptRoot "..")

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
$env:USE_OLLAMA_EMBEDDINGS = "false"
$env:USE_OLLAMA_RERANKER = "false"
$env:RETRIEVAL_ENABLE_VECTOR = "false"
$env:LOW_MEMORY_MODE = "true"

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
    "--output", $MetricsOutput,
    "--failures-output", $FailuresOutput
)

python @evalArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python scripts/validate_eval_gate.py `
    --manifest $Manifest `
    --dataset $Dataset `
    --metrics $MetricsOutput `
    --output $GateReportOutput
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
