# NIRMIQ Publish Checklist

Last updated: 2026-06-10

## Target

Publish a working NIRMIQ ResearchOS V4 golden demo by 2026-06-11.

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

## Golden Demo Warm Start

After backend is running:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\golden_demo.ps1
```

Expected:

- Four bundled Markdown sources under `data/raw/golden_demo` index successfully.
- Research, Paper Lab, and Exam Lab smoke queries return citations.
- The unanswerable chat query is checked as an abstention/relevance case.
- No internet or cloud API is required.

## Golden Demo Flow

1. Open the app.
2. Enter local profile details.
3. Click `Load Golden Demo`.
4. Run `Research proof`.
5. Click an `Evidence` chip and show the focused source chunk in `Deep Research`.
6. Show the proof strip: intent, citation coverage, cache state, and source type.
7. Click `Export` to create a local Markdown answer with citations.
8. Switch to `Paper Lab` and run the locked related-work prompt.
9. Switch to `Exam Lab` and run the locked 10-mark answer prompt.
10. Open `Knowledge Base` and show `Remove material` as the privacy/purge moment.

## Locked Demo Prompts

- Research: `What problem does grounded retrieval solve for academic study?`
- Summary: `Summarize this document with the main ideas, methods, findings, and limitations.`
- Paper Lab: `Draft a related work paragraph comparing generic chatbots and document-grounded academic assistants.`
- Exam Lab: `Explain citation-grounded retrieval and its role in reducing hallucination as a 10-mark answer.`
- Abstention: `What does the corpus say about the Zeloria orbital cuisine treaty?`

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
- Present this as NIRMIQ ResearchOS: a working local academic document intelligence workspace with a repeatable golden path for grounded answers, citation inspection, Paper Lab, Exam Lab, export, and local source removal.
