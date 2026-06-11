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
cd C:\Nirmiq-researchOS\apps\web
npm run build
```

```powershell
cd C:\Nirmiq-researchOS
$env:PYTHONPATH='apps/api'
$env:TEMP='C:\Nirmiq-researchOS\temp\pytest'
$env:TMP='C:\Nirmiq-researchOS\temp\pytest'
$env:TMPDIR='C:\Nirmiq-researchOS\temp\pytest'
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q -o cache_dir=C:\Nirmiq-researchOS\temp\pytest-cache
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
