param(
    [string]$SqlitePath = $env:SQLITE_PATH,
    [string]$Output = "temp\real_user_qa\local_feedback_eval_candidates.jsonl",
    [string]$Report = "temp\real_user_qa\local_feedback_report.json",
    [switch]$IncludeGood,
    [int]$Limit = 200
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not $SqlitePath) {
    $SqlitePath = "data\sqlite\nirmiq.db"
}

$argsList = @(
    "scripts/export_real_user_qa.py",
    "--sqlite-path", $SqlitePath,
    "--output", $Output,
    "--report", $Report,
    "--limit", $Limit
)

if ($IncludeGood) {
    $argsList += "--include-good"
}

python @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
