param(
    [string]$Manifest = "data\processed\eval\generalization_gate.json",
    [string]$Dataset = "",
    [string]$JsonOutput = "",
    [string]$MarkdownOutput = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

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

$auditRoot = [System.IO.Path]::GetFullPath((Join-Path $root "temp\generalization-dataset-audit"))
$safeTempRoot = [System.IO.Path]::GetFullPath((Join-Path $root "temp"))
if (-not $auditRoot.StartsWith($safeTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Dataset audit storage must remain under the workspace temp directory."
}
if (Test-Path -LiteralPath $auditRoot) {
    Remove-Item -LiteralPath $auditRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $auditRoot | Out-Null

$candidateJson = Join-Path $auditRoot "generalization-dataset-audit.json"
$candidateMarkdown = Join-Path $auditRoot "generalization-dataset-audit.md"

python scripts/audit_eval_dataset.py `
    --manifest $Manifest `
    --dataset $Dataset `
    --json-output $candidateJson `
    --markdown-output $candidateMarkdown
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

function Publish-IfChanged {
    param(
        [string]$Candidate,
        [string]$Destination
    )

    $destinationParent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null

    if (Test-Path -LiteralPath $Destination) {
        $candidateHash = (Get-FileHash -LiteralPath $Candidate -Algorithm SHA256).Hash
        $destinationHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($candidateHash -eq $destinationHash) {
            return
        }
    }

    $sourcePath = [System.IO.Path]::GetFullPath($Candidate)
    $destinationPath = [System.IO.Path]::GetFullPath($Destination)
    [System.IO.File]::WriteAllBytes(
        $destinationPath,
        [System.IO.File]::ReadAllBytes($sourcePath)
    )
}

Publish-IfChanged -Candidate $candidateJson -Destination $JsonOutput
Publish-IfChanged -Candidate $candidateMarkdown -Destination $MarkdownOutput
