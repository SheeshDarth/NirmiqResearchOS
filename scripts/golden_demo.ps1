$ErrorActionPreference = "Stop"

$apiBase = $env:NIRMIQ_API_BASE
if (-not $apiBase) {
    $apiBase = "http://127.0.0.1:8000"
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$demoRoot = Join-Path $root "data\raw\golden_demo"

$sources = @(
    @{ path = Join-Path $demoRoot "01_grounded_rag_notes.md"; title = "Golden Demo 01 - Grounded Academic Retrieval"; mode = "research"; query = "What problem does grounded retrieval solve for academic study?" },
    @{ path = Join-Path $demoRoot "02_offline_privacy_runtime.md"; title = "Golden Demo 02 - Offline Runtime And Privacy"; mode = "research"; query = "How does NIRMIQ preserve local-first privacy during document work?" },
    @{ path = Join-Path $demoRoot "03_exam_lab_question_bank.md"; title = "Golden Demo 03 - Exam Lab Study Notes"; mode = "exam_answer"; query = "Explain citation-grounded retrieval and its role in reducing hallucination as a 10-mark answer." },
    @{ path = Join-Path $demoRoot "04_paper_lab_research_brief.md"; title = "Golden Demo 04 - Paper Lab Research Brief"; mode = "research_paper"; query = "Draft a related work paragraph comparing generic chatbots and document-grounded academic assistants." }
)

Write-Output "NIRMIQ golden demo warm start"
Write-Output "Backend: $apiBase"

$health = Invoke-RestMethod -Uri "$apiBase/health" -Method Get -TimeoutSec 8
if ($health.status -ne "ok") {
    throw "Backend health failed: $($health | ConvertTo-Json -Compress)"
}

$indexed = @()
foreach ($source in $sources) {
    if (-not (Test-Path $source.path)) {
        throw "Demo source missing: $($source.path)"
    }
    $payload = @{
        source_path = [string](Resolve-Path $source.path)
        title = $source.title
        force_reindex = $false
    } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "$apiBase/ingest" -Method Post -ContentType "application/json" -Body $payload -TimeoutSec 60
    $indexed += @{
        id = $response.document_id
        title = $source.title
        mode = $source.mode
        query = $source.query
    }
    Write-Output "Indexed: $($source.title) -> $($response.document_id)"
}

foreach ($item in $indexed) {
    $queryPayload = @{
        session_id = "golden-demo-smoke"
        query = $item.query
        document_id = $item.id
        mode = $item.mode
        retrieval_mode = "hybrid"
        retrieval_profile = "balanced"
        debug = $true
    } | ConvertTo-Json
    $queryResponse = Invoke-RestMethod -Uri "$apiBase/query" -Method Post -ContentType "application/json" -Body $queryPayload -TimeoutSec 90
    $citationCount = @($queryResponse.citations).Count
    if ($citationCount -lt 1) {
        throw "Golden demo query returned no citations for $($item.title)"
    }
    Write-Output "PASS: $($item.mode) / citations=$citationCount / grounded=$($queryResponse.grounded)"
}

$unanswerablePayload = @{
    session_id = "golden-demo-smoke"
    query = "What does the corpus say about the Zeloria orbital cuisine treaty?"
    mode = "general_chat"
    retrieval_mode = "hybrid"
    retrieval_profile = "fast"
    debug = $true
} | ConvertTo-Json
$unanswerable = Invoke-RestMethod -Uri "$apiBase/query" -Method Post -ContentType "application/json" -Body $unanswerablePayload -TimeoutSec 90
$unanswerableCitationCount = @($unanswerable.citations).Count
if ($unanswerable.grounded -ne $false -or $unanswerableCitationCount -ne 0) {
    throw "Abstention check failed: grounded=$($unanswerable.grounded), citations=$unanswerableCitationCount"
}
Write-Output "PASS: abstention / grounded=$($unanswerable.grounded) / citations=$unanswerableCitationCount"

Write-Output "Golden demo ready. Open the web app, click Load Golden Demo, then run the locked prompts."
