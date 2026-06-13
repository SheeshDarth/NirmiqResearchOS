param(
    [string]$Dataset = "data\processed\eval\demo_academic_qa.jsonl",
    [switch]$FullQuery
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$argsList = @(
    "scripts/eval_retrieval.py",
    "--dataset", $Dataset,
    "--k", "3", "5", "8",
    "--modes", "hybrid", "bm25",
    "--output", "data/processed/eval/demo_retrieval_metrics.json"
)
if ($FullQuery) { $argsList += "--full-query" }
python @argsList
