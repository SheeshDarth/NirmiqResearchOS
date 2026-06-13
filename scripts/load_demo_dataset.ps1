param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [switch]$ForceReindex
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$docs = @(
    @{ path = "data\raw\demo_pdfs\nirmiq_rag_reference.pdf"; title = "NIRMIQ Demo - RAG Reference Notes" },
    @{ path = "data\raw\demo_pdfs\nirmiq_exam_reference.pdf"; title = "NIRMIQ Demo - Exam Preparation Notes" }
)

foreach ($doc in $docs) {
    $sourcePath = Resolve-Path $doc.path
    $payload = @{
        source_path = $sourcePath.Path
        title = $doc.title
        mime_type = "application/pdf"
        force_reindex = [bool]$ForceReindex
    } | ConvertTo-Json
    Write-Output "Indexing $($doc.title)..."
    Invoke-RestMethod -Method Post -Uri "$ApiBase/ingest" -ContentType "application/json" -Body $payload | ConvertTo-Json -Depth 4
}

Write-Output "Demo dataset loaded. Run scripts\eval_retrieval.ps1 or open http://127.0.0.1:3002."
