param(
    [string]$MetricsOutput = "data\processed\eval\recursive_summary_reliability_metrics.json"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$safeTempRoot = [System.IO.Path]::GetFullPath((Join-Path $root "temp"))
$evalRoot = [System.IO.Path]::GetFullPath((Join-Path $safeTempRoot "summary-reliability-eval"))
$destination = [System.IO.Path]::GetFullPath((Join-Path $root $MetricsOutput))
if (-not $evalRoot.StartsWith($safeTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Summary reliability evaluation storage must remain under the workspace temp directory."
}
if (-not $destination.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Summary reliability metrics must remain inside the workspace."
}

if (Test-Path -LiteralPath $evalRoot) {
    Remove-Item -LiteralPath $evalRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $evalRoot | Out-Null

$candidate = Join-Path $evalRoot "recursive-summary-reliability-metrics.json"
$env:PYTHONPATH = "apps/api"
python scripts/eval_recursive_summary_reliability.py --output $candidate
if ($LASTEXITCODE -ne 0) {
    throw "Recursive-summary reliability evaluation failed."
}

$destinationDirectory = Split-Path -Parent $destination
New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
Copy-Item -LiteralPath $candidate -Destination $destination -Force
Write-Output "SUMMARY RELIABILITY CHECK PASS"
