# NIRMIQ Publish Checklist

Last updated: 2026-06-06

## Target

Publish a working V4 foundation demo by 2026-06-07.

## Pre-Publish Commands

Run from `C:\Nirmiq-researchOS`.

```powershell
$env:PYTHONPATH='apps/api'
python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q
python -m compileall apps/api/app
cd apps/web
npm run build
```

## Local Demo Startup

Terminal 1:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_api.ps1
```

Terminal 2:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_web.ps1
```

Open:

- `http://127.0.0.1:3002`
- Local backend health: `http://127.0.0.1:8000/health`
- Local backend readiness: `http://127.0.0.1:8000/health/readiness`

## Smoke Check

After backend and frontend are running:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\publish_smoke.ps1
```

Expected:

- Local backend health returns `ok`.
- Readiness returns `ready` when at least one indexed document exists.
- Readiness reports `cloud_api_required=false`.
- Web shell includes NIRMIQ branding.

## Demo Flow

1. Open the app.
2. Enter local profile details.
3. Upload or select a PDF.
4. Click `Summarize PDF`.
5. Inspect citations in `Sources`.
6. Switch to `Paper Lab`.
7. Ask for a related-work or methodology section.
8. Show Paper Lab outline and related-work matrix.
9. Click `Copy Markdown Draft`.
10. Switch to `Exam Lab` and generate a study guide/custom PDF if needed.

## Optional Retrieval Eval Labels

The retrieval evaluator needs real document IDs from your local SQLite database.

After ingesting a demo PDF:

1. Open `Library` in the app and copy the selected document id from API/debug output, or inspect `GET /documents`.
2. Copy `data/processed/eval/qa_labels.example.jsonl` to `data/processed/eval/qa_labels.jsonl`.
3. Replace `replace-with-document-id` with the real indexed document id.
4. Run:

```powershell
python scripts/eval_retrieval.py --dataset data/processed/eval/qa_labels.jsonl --k 3 5 8 --modes hybrid bm25
```

## Publish Notes

- Keep the repo local-first and offline-capable.
- Do not promise production authentication yet.
- Do not claim cloud sync, internet search, or ChatGPT/OpenAI account dependency.
- Present this as a working local academic intelligence workspace with grounded RAG, citations, Paper Lab, and Exam Lab.
