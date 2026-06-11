$ErrorActionPreference = "Stop"

$apiBase = $env:NIRMIQ_API_BASE
if (-not $apiBase) {
    $apiBase = "http://127.0.0.1:8000"
}

$webBase = $env:NIRMIQ_WEB_BASE
if (-not $webBase) {
    $webBase = "http://127.0.0.1:3002"
}

Write-Output "NIRMIQ publish smoke check"
Write-Output "Local backend: $apiBase"
Write-Output "Web: $webBase"

$health = Invoke-RestMethod -Uri "$apiBase/health" -Method Get -TimeoutSec 12
if ($health.status -ne "ok") {
    throw "Local backend health failed: $($health | ConvertTo-Json -Compress)"
}

$readiness = Invoke-RestMethod -Uri "$apiBase/health/readiness" -Method Get -TimeoutSec 25
if ($readiness.database -ne "ok") {
    throw "Readiness database check failed: $($readiness | ConvertTo-Json -Compress)"
}

$web = Invoke-WebRequest -Uri $webBase -UseBasicParsing -TimeoutSec 25
if ($web.Content -notmatch "NIRMIQ") {
    throw "Web app loaded, but NIRMIQ branding was not detected."
}

if ($readiness.cloud_api_required -ne $false) {
    throw "Readiness must not require a cloud API for core operation."
}

Write-Output "PASS: local backend health ok"
Write-Output "PASS: readiness status = $($readiness.status), indexed_documents = $($readiness.indexed_documents), active_chunks = $($readiness.active_chunks)"
Write-Output "PASS: offline-first core confirmed, cloud_api_required = $($readiness.cloud_api_required)"
Write-Output "PASS: web app returned NIRMIQ shell"
