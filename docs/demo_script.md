# NIRMIQ Golden Demo Script

Last updated: 2026-07-15

## Goal

Show NIRMIQ as a local-first academic intelligence workspace, not a generic PDF chatbot.

The demo promise:

> A reviewer can load local academic material, ask a research question, inspect the exact evidence trail, export the answer, and remove a source without internet.

## Target Reviewer

Engineering students, early researchers, and technical reviewers who care about grounded answers, privacy, and maintainable local AI systems.

## Setup

Start the local preview and warm-start the demo corpus:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

If the backend is already running, warm-start only the golden corpus:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\golden_demo.ps1
```

Open:

- `http://127.0.0.1:3002`

## Demo Corpus

Bundled local sources:

- `data/raw/golden_demo/01_grounded_rag_notes.md`
- `data/raw/golden_demo/02_offline_privacy_runtime.md`
- `data/raw/golden_demo/03_exam_lab_question_bank.md`
- `data/raw/golden_demo/04_paper_lab_research_brief.md`

No internet is required.

## 90-Second Flow

1. Log in with the local profile gate.
2. Click `Load Golden Demo`.
3. Run `Research proof`.
4. Click an `Evidence` chip under the answer.
5. Show `Deep Research` opening the focused source chunk.
6. Keep the normal answer view simple; open Sources only when the reviewer wants proof.
7. Click `Export` to create a local Markdown answer with citations.
8. Open `Knowledge Base` and show the three explicit local-data scopes: clear thread, clear indexed material, and reset all local data.
9. Mention `NIRMIQ Diagnostics.cmd`: it exports status summaries without raw logs or document/conversation content.

## Locked Demo Questions

Research:

```text
What problem does grounded retrieval solve for academic study?
```

Summary:

```text
Summarize this document with the main ideas, methods, findings, and limitations.
```

Paper Lab:

```text
Draft a related work paragraph comparing generic chatbots and document-grounded academic assistants.
```

Exam Lab:

```text
Explain citation-grounded retrieval and its role in reducing hallucination as a 10-mark answer.
```

Abstention:

```text
What does the corpus say about the Zeloria orbital cuisine treaty?
```

Expected behavior: NIRMIQ should request external context or state that the uploaded material does not support the answer.

## Pass/Fail Bar

Pass:

- Golden corpus indexes without internet.
- Each grounded query returns at least one citation.
- Evidence chips open the correct Deep Research source chunk.
- Export creates a Markdown artifact with answer and citations.
- Selected material can be removed with confirmation.
- App remains understandable without opening debug panels.

Fail:

- A grounded answer returns without citations.
- A citation chip does not focus a source chunk.
- The app needs cloud/API access for the core demo.
- The UI hides the response behind the composer.
- The demo requires unexplained backend internals to make sense.

## Latest Verified Walkthrough

Validated on 2026-07-15 with:

```powershell
npm.cmd run ship:check
npm.cmd run desktop:smoke
```

Result:

- Backend tests: `163 passed`, `1 warning`.
- API compile: passed.
- Web production build: passed at `118 kB` first-load JavaScript.
- Publish smoke: passed with `cloud_api_required=False`.
- Golden demo indexing: passed for all four bundled local sources.
- Research prompt: passed with grounded citations.
- Summary-style research prompt: passed with grounded citations.
- Exam Lab prompt: passed with grounded citations.
- Paper Lab prompt: passed with grounded citations.
- Unsupported query: passed with `grounded=False` and `citations=0`.
- Desktop smoke: passed through the Electron shell and cleaned up smoke-started runtime processes.
- Rebuilt portable executable smoke: passed.
- Safe diagnostics export: passed inside the ship gate.

Current demo limitation:

- Current Chat, grounded-answer, and citation-trail screenshots are committed. Paper Lab/Exam Lab captures and an optional short GIF remain public-polish follow-ups.

## Fallback Plan

If live retrieval is slow:

1. Keep the app open with the golden corpus already indexed.
2. Use the existing answer history in the thread.
3. Show `Deep Research` citations and source chunks.
4. Use screenshots from the same golden path in README or project notes.

Do not switch to unrelated features during the demo.
