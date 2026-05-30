# NIRMIQ Debugging Guide

Last updated: 2026-05-30

## Local URLs

- Web: `http://127.0.0.1:3002`
- API: `http://127.0.0.1:8000`

## Start Backend

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

### Scroll Not Working

Likely cause: sticky composer too tall or nested overflow conflict.

Current mitigation: composer is compact and minimizable. If regressions occur, inspect `.thread-scroll`, `.research-console`, `.composer-wrap`, and viewport height calculations.

### Upload Works But Query Uses Wrong Document

Fix: select the intended document in Library or ensure the newest upload becomes `selectedDocumentId`.

### Ollama Offline

Expected behavior: generation and embeddings should gracefully fall back. The answer may become more extractive, but the app should not crash.

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

