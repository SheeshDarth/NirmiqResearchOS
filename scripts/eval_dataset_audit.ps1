param(
    [string]$Manifest = "data\processed\eval\generalization_gate.json",
    [string]$Dataset = "",
    [string]$JsonOutput = "",
    [string]$MarkdownOutput = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$manifestJson = Get-Content -Raw -Path $Manifest | ConvertFrom-Json
if (-not $Dataset) {
    $Dataset = [string]$manifestJson.dataset_path
}
if (-not $JsonOutput) {
    $JsonOutput = [string]$manifestJson.audit_report_path
}
if (-not $MarkdownOutput) {
    $MarkdownOutput = [string]$manifestJson.audit_markdown_path
}

python scripts/audit_eval_dataset.py `
    --manifest $Manifest `
    --dataset $Dataset `
    --json-output $JsonOutput `
    --markdown-output $MarkdownOutput
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
