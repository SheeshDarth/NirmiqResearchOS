# NIRMIQ Debugging Guide

Last updated: 2026-06-11

## Local URLs

- Web: `http://127.0.0.1:3002`
- API: `http://127.0.0.1:8000`

## Start Backend

Preferred one-command preview:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -OpenBrowser
```

Windows double-click preview:

```text
NIRMIQ ResearchOS.cmd
```

Preview with bundled demo corpus:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

Stop launcher-created preview processes:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\stop_local.ps1
```

If Next.js shows `Cannot find module './398.js'` or missing `.next` manifest errors, stop the preview first, then delete the generated `.next` cache and relaunch:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\stop_local.ps1
Remove-Item -Recurse -Force .\apps\web\.next
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

Manual backend:

```powershell
cd C:\Nirmiq-researchOS\apps\api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Start Frontend

```powershell
cd C:\Nirmiq-researchOS\apps\web
npm run dev
```

## Build And Test

Full EOD verification:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\ship_check.ps1
```

Manual frontend build:

```powershell
cd C:\Nirmiq-researchOS
npm.cmd run build
```

```powershell
cd C:\Nirmiq-researchOS
.\scripts\test_api.ps1
```

## Golden Demo Debug

Warm-start the bundled corpus:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\golden_demo.ps1
```

If this fails:

- Confirm the backend is running at `http://127.0.0.1:8000`.
- Confirm `data/raw/golden_demo/*.md` files exist.
- Confirm local path ingestion roots include `C:\Nirmiq-researchOS\data\raw`.
- Run `GET /health/readiness` and check database status.
- If a query has no citations, use the UI `Deep Research` panel to inspect retrieved chunks and try BM25 mode.
- If the abstention check fails, inspect `retrieval_meta.context_relevance_state`; General Chat should only answer when actual subject terms overlap retrieved chunks.

## Common Issues

### Hydration Warning With `fdprocessedid`

Cause: browser extensions inject attributes before React hydrates.

Fix: test in a clean profile/incognito or disable form-filling/security extensions. The app also avoids `Date.now()`/`Math.random()` in SSR-sensitive rendering paths where possible.

### Next.js Runtime Error After Heavy UI Edits

Cause: stale dev-server cache or partial hot reload.

Fix:

```powershell
Stop-Process -Name node -Force -ErrorAction SilentlyContinue
cd C:\Nirmiq-researchOS\apps\web
npm run dev
```

If it persists, remove `.next` and rebuild.

### PDF Says “Not Enough Context” After Upload

Checklist:

- Confirm the document appears in Library.
- Confirm chunk count is greater than zero.
- Click `Summarize PDF` instead of asking an extremely broad custom prompt.
- Check API logs for parsing errors.
- If scanned PDF, install OCR dependencies and Tesseract.

### Local Path Ingestion Is Rejected

Cause: V3 privacy hardening restricts direct filesystem ingestion to trusted corpus roots.

Fix:

- Upload through the app composer, or
- Move the file under `C:\Nirmiq-researchOS\data\raw`, or
- Add the folder to `LOCAL_INGEST_ALLOWED_ROOTS` in `.env`.

Only set `SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS=true` for trusted local development.

### Upload Rejected As Invalid File Type

Cause: the upload extension and file content do not match, or the text file is not valid UTF-8.

Fix:

- Confirm the file is a real PDF/image/text file.
- Re-save text/Markdown files as UTF-8.
- Avoid renaming unsupported binaries to `.pdf` or `.txt`.

### Scroll Not Working

Likely cause: sticky composer too tall or nested overflow conflict.

Current mitigation: composer is compact and minimizable. If regressions occur, inspect `.thread-scroll`, `.research-console`, `.composer-wrap`, and viewport height calculations.

### Upload Works But Query Uses Wrong Document

Fix: select the intended document in Library or ensure the newest upload becomes `selectedDocumentId`.

### Browser Shows Failed To Fetch / TypeError

Most likely causes:

- FastAPI returned a backend `500`.
- The local backend is down.
- Next.js dev cache is stale and needs a clean restart.

Known V4 fix:

- Chroma vector collections can retain a previous embedding dimension. If Ollama is offline and fallback hash embeddings are used, Chroma may report a dimension mismatch.
- `ChromaRepo` now resets the affected collection and retries once during upsert, and vector query dimension mismatch degrades to lexical retrieval instead of crashing.

Preview recovery:

```powershell
cd C:\Nirmiq-researchOS
powershell -ExecutionPolicy Bypass -File .\scripts\publish_smoke.ps1
```

If the web TypeError persists, stop the web listener, delete generated `apps\web\.next`, and restart `.\scripts\run_web.ps1`.

### Upload Returns 413 Request Body Too Large

Cause: the API rejected the request before ingestion because `Content-Length` exceeded `MAX_REQUEST_BODY_BYTES`.

Default:

```powershell
$env:MAX_REQUEST_BODY_BYTES='78643200'
```

Fix:

- Use a smaller PDF or split a very large textbook.
- Increase `MAX_REQUEST_BODY_BYTES` only for trusted local runs.
- Keep the default for public demo safety.

### API Versioned Route Check

Current local routes still work, and `/api/v1` aliases are also available.

Smoke:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Both should return:

```json
{"status":"ok"}
```

### Docker Compose Fails To Start

First validate config:

```powershell
docker compose -f docker-compose.local.yml config
```

If the web container cannot find `node_modules`, remove the named volume and rebuild:

```powershell
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up --build
```

Use the Windows launcher for best RTX 4050/Ollama performance:

```powershell
.\scripts\start_local.ps1 -GoldenDemo -OpenBrowser
```

### Summary Still Feels Slow

Checklist:

- Confirm a document is selected before using `Summarize PDF`; cache is only used for selected-document summaries.
- Confirm the second identical summary request has `retrieval_meta.cache_hit=true` when debug metadata is enabled.
- Reindexing or changing the source file intentionally misses cache because the document `content_hash` changed.

### Trust Badge Says Low Citation Coverage

Cause: the answer has several claim-like sentences without citation anchors.

Fix:

- Ask a narrower question, switch to Precision, or inspect Sources to verify whether retrieval found enough evidence.
- If the badge appears on an obviously extractive answer, check `citation_coverage`, `citation_sentence_count`, and `citation_anchor_count` in debug metadata.

### Ollama Offline

Expected behavior: generation and embeddings should gracefully fall back. The answer may become more extractive, but the app should not crash.

### Local Model Feels Laggy Or Uses Too Much Memory

Current default backend settings are RTX 4050-friendly:

```powershell
$env:LOW_MEMORY_MODE='true'
$env:OLLAMA_KEEP_ALIVE='45s'
$env:OLLAMA_NUM_CTX='3072'
$env:OLLAMA_NUM_PREDICT='768'
$env:OLLAMA_EMBED_BATCH_SIZE='8'
```

If VRAM is still unstable, cap GPU layers or CPU threads before starting the API:

```powershell
$env:OLLAMA_NUM_GPU='20'
$env:OLLAMA_NUM_THREAD='6'
```

If response quality drops, prefer improving retrieval labels/eval before increasing model size.

### Git Permission Warning

Observed warning:

```text
unable to access 'C:\Users\Siddharth/.config/git/ignore': Permission denied
```

This is a user-level Git ignore permission issue and does not block project commits.

## Debugging Priorities

1. Keep API health green.
2. Keep web build green.
3. Verify upload -> index -> summarize -> cite.
4. Confirm no console errors in browser.
5. Update `context.md` after every meaningful change.
6. Push to GitHub after every completed work unit.

### Textbook Answers Are Wrong Or Too Generic

Checklist:

- Confirm the selected document has active chunks. A row marked `needs_reindex` should not be used for demo answers.
- Confirm Ollama has an answer-capable local model installed. Current routing prefers `mistral:7b-instruct-q4_K_M` when `phi3:mini` is missing.
- Check debug metadata:
  - `generation_model_requested`
  - `generation_model_used`
  - `generation_model_fallback`
  - `answer_rewritten_for_faithfulness`
  - `focused_seed_chunks`
  - `summary_seed_chunks`
- If `generation_backend=fallback`, the answer should still be source-only and cited, but it may be more extractive.
- If the local model adds unsupported techniques, the faithfulness verifier should rewrite the answer into source-only form.

Known validated textbook smoke:

```powershell
# Document id from the 2026-06-11 clean index
$doc='e9b7b4ff-b679-44db-a2cf-bbb945caee22'
```

Query:

```text
What is overfitting and how can it be reduced?
```

Expected evidence:

- Page 58 definition of overfitting.
- Page 59 solutions including simplifying/constraining the model, gathering more data, and reducing noise/outliers.

### Ollama Returns Empty Answer Text

Observed with `qwen3.5:4b`: Ollama can return an empty `response` while filling a `thinking` field. This is not acceptable for the user-facing answer path.

Mitigation:

- Prefer `mistral:7b-instruct-q4_K_M` for generation when available.
- Keep Qwen as a lower-priority fallback unless its response behavior is retested with a better local prompt/budget.

Updated local runtime defaults:

```powershell
$env:OLLAMA_TIMEOUT_SECONDS='120'
$env:OLLAMA_NUM_PREDICT='512'
```
