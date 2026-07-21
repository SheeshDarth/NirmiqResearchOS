# NIRMIQ Publish Checklist

Last updated: 2026-07-15

## Target

Publish a working NIRMIQ Academic Intelligence local-first golden demo with clear GitHub credibility, repeatable startup, CI, and measured retrieval evidence.

## Pre-Publish Commands

Run from `C:\Nirmiq-researchOS`.

Full EOD ship check, execution-policy safe:

```powershell
npm.cmd run doctor
npm.cmd run ship:check
npm.cmd run desktop:smoke
```

If startup would otherwise surface `Failed to fetch`, run `npm.cmd run doctor` first. Critical Python, Node, backend-import, web-dependency, or port conflicts fail with an actionable command. Missing/unreachable Ollama is only a warning because the deterministic offline core remains supported.

Latest local verification:

- Date: 2026-07-15.
- Doctor: `12` checks, `0` failures, `1` optional Ollama warning.
- Result: `SHIP CHECK PASS`.
- Backend tests: `163 passed`, `1` third-party deprecation warning.
- API compile: passed.
- Web build: passed; `/` first-load JavaScript `118 kB`.
- Publish smoke: passed with `18` indexed documents, `9443` active chunks, and `cloud_api_required=False`.
- Golden grounded routes and unsupported-query abstention: passed.
- Desktop smoke and portable Windows packaging: passed.
- Strict 40-case result: MRR `0.868`, Recall@8 `0.921`, expected citation coverage `0.921`, faithfulness `0.985`.
- Full evidence: [`release_manifest_v0.5.md`](release_manifest_v0.5.md).

Implementation note:

- `ship_check.ps1` uses an isolated per-run pytest temp/cache directory under `temp\pytest-runs\`.
- This prevents stale Windows temp/cache permissions from breaking the release gate.
- Direct `.\scripts\ship_check.ps1` may be blocked by Windows PowerShell execution policy.
- Use `npm.cmd run ship:check`, `NIRMIQ Ship Check.cmd`, or the explicit bypass command below.

Double-click Windows launcher:

```text
NIRMIQ Ship Check.cmd
```

Explicit PowerShell equivalent:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ship_check.ps1
```

Manual equivalent:

```powershell
.\scripts\test_api.ps1
npm.cmd run compile:api
npm.cmd run build
```

Public repo checks:

```powershell
docker compose -f docker-compose.local.yml config
git status --short
```

Expected repo hygiene:

- `.github/workflows/ci.yml` exists.
- `.github/CODEOWNERS` exists.
- `LICENSE` exists.
- `package.json` root command hub exists.
- `apps/api/Dockerfile` exists.
- `apps/web/Dockerfile` exists.

## Local Demo Startup

Preferred one-command preview:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -OpenBrowser
```

Windows double-click preview:

```text
NIRMIQ Academic Intelligence.cmd
```

Preferred golden-demo preview:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

Windows double-click golden demo:

```text
NIRMIQ Golden Demo.cmd
```

Optional desktop shortcut:

```powershell
.\scripts\create_windows_shortcut.ps1 -Desktop
```

Fallback Terminal 1:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_api.ps1
```

Fallback Terminal 2:

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

If backend is already running:

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
10. Open `Knowledge Base` and show Local Data controls: export thread, clear thread, and clear indexed material.

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
- Present this as NIRMIQ Academic Intelligence: a working local academic document intelligence workspace with a repeatable golden path for grounded answers, citation inspection, Paper Lab, Exam Lab, export, and local-data control.
- If linking publicly, call it a local-first portfolio/demo MVP, not a hosted SaaS.
- Use `/api/v1/*` in future clients, but keep existing local routes working for current UI stability.
- Keep HSTS/CSP disabled on local HTTP unless running behind HTTPS/proxy.

## Latest Ship Gate Result

Validated on 2026-07-15:

```powershell
npm.cmd run ship:check
```

Result:

- Backend unit/integration tests: `163 passed, 1 warning`.
- API compile: passed.
- Web production build: passed, `/` first-load JS `118 kB`.
- Publish smoke: passed with `indexed_documents=18`, `active_chunks=9443`, and `cloud_api_required=False`.
- Golden demo: Research, summary-style Research, Exam Lab, and Paper Lab returned grounded citations.
- Golden demo unsupported Chat query: passed with `grounded=false` and `citations=0`.
- Privacy-safe diagnostics export: passed inside the ship gate.

Release-hardening refresh on 2026-07-15:

- `npm.cmd run desktop:package`: passed.
- `npm.cmd run desktop:smoke`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\eval_answer_quality.ps1`: passed the release thresholds.
- Portable artifact: `dist\desktop\NIRMIQ Academic Intelligence 0.5.0.exe`.
- `npm.cmd run desktop:portable-smoke`: passed against the generated executable.

Current known release debt:

- README screenshots exist; a current optional GIF and final manual desktop/mobile visual acceptance remain.
- Retrieval labels need to grow beyond the current 40-case quality set and include more scans, diagrams, equations, and noisy notes.
- Real-user QA exports should stay under `temp/real_user_qa` until manually reviewed and scrubbed.
- Desktop package uses the NIRMIQ icon but remains unsigned.
- Linux browser-preview path has an Ubuntu CI smoke; native Linux packaging is not validated yet.
