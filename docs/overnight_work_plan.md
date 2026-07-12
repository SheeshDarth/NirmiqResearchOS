# NIRMIQ Overnight Work Plan

Last updated: 2026-07-12

Purpose: keep NIRMIQ moving through a focused overnight sprint without increasing product complexity. The priority is demo reliability, answer accuracy, and a clean ChatGPT-like experience.

## North Star

By the end of the sprint, NIRMIQ should feel like a serious local academic intelligence demo:

- Upload or load a sample document.
- Ask a natural question.
- Get a readable answer.
- See clear trust state.
- Open evidence only when needed.
- Avoid confident hallucinations when evidence is weak.

## Non-Negotiables

- Keep the app offline-first.
- Do not add cloud dependency as a fix for quality.
- Do not increase model size, context length, or temperature before fixing retrieval.
- Do not add GraphRAG, agents, or new heavy dependencies tonight.
- Preserve current backend API shapes.
- Keep the UI simple, calm, and chatbot-first.

## Current Baseline

Release-hardening status on 2026-07-12:

- Raw retrieval, 17 samples: Hybrid MRR `0.804`, BM25 MRR `0.843`, Recall@8 `1.000`, citation expected coverage `1.000`.
- Full-query answer path, 17 samples: Hybrid and BM25 MRR `0.882`, Recall@8 `1.000`, citation expected coverage `1.000`.
- Current full-query failure backlog: `0` records.
- Next accuracy work: grow the real-world seed and test abstention/partial evidence; do not tune against the 17 samples further.

Historical baseline before the reliability work:

Known real-world retrieval baseline before the next reliability pass:

- Hybrid MRR: `0.490`
- Hybrid Recall@8: `0.750`
- Hybrid citation expected coverage: `0.750`
- BM25 MRR: `0.578`
- BM25 Recall@8: `0.750`
- BM25 citation expected coverage: `0.750`
- Corrected full-query citation expected coverage: `0.688`

This means the main issue is still evidence selection, not only generation.

## Overnight Sprint Blocks

### Block 1: Freeze And Diagnose

Goal: preserve a clean baseline before changing retrieval behavior.

Tasks:

- Run backend tests.
- Run frontend build.
- Run demo eval.
- Run real-world eval.
- Save notable failures and bad-answer cases into the evaluation backlog.

Commands:

```powershell
python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q
python -m compileall apps/api/app
Push-Location apps/web; npm.cmd run build; Pop-Location
.\scripts\eval_demo_dataset.ps1
.\scripts\eval_real_world.ps1
```

Acceptance:

- Tests pass or failures are documented with exact stack traces.
- Current metrics are not silently overwritten.
- At least the top 5 bad-answer examples are captured for follow-up.

### Block 2: Retrieval Evaluation Expansion

Goal: increase evaluation coverage before tuning retrieval.

Tasks:

- Add textbook-style questions from actual local sample material.
- Include factual lookup, conceptual explanation, compare, summary, exam, and unanswerable cases.
- Add expected page or phrase labels when obvious.
- Convert useful `Needs work` feedback into candidate eval rows.

Acceptance:

- Real-world eval grows from `16` cases toward `40`.
- Every new label has an answerability expectation.
- No sample requires internet access or proprietary cloud APIs.

### Block 3: Answer-Used Citation Selection

Goal: make the cited chunks match the answer content more tightly.

Tasks:

- Inspect when the answer uses weak or broad chunks despite better chunks being retrieved.
- Prefer chunks with direct phrase overlap and section agreement.
- Penalize noisy boilerplate, table-of-contents fragments, broken OCR, and repeated footer/header chunks.
- Keep fallback extractive answers when generation support is weak.

Acceptance:

- Full-query citation expected coverage moves closer to raw retrieval coverage.
- Unsupported claim rate decreases on the expanded eval set.
- No new visible controls are added.

### Block 4: UI Clarity Pass

Goal: make the product feel like an assistant, not a diagnostics dashboard.

Tasks:

- Keep chat thread visually dominant.
- Keep composer compact and collapsible.
- Hide retrieval diagnostics behind Deep Research.
- Show one trust badge per answer.
- Make evidence expandable under the answer.
- Polish no-document, backend-offline, Ollama-unavailable, and insufficient-evidence states.

Acceptance:

- A first-time reviewer can understand the app in under 30 seconds.
- Main answer text is readable without opening side panels.
- Metadata does not compete with the answer.

### Block 5: Release Readiness

Goal: make the repo and demo trustworthy.

Tasks:

- Update `context.md`.
- Update benchmark and accuracy docs if metrics change.
- Run smoke commands.
- Commit only intentional files.
- Push only after tests/build are green or clearly documented.

Acceptance:

- `git status --short` is explainable.
- README and docs match actual behavior.
- Demo path is repeatable from a fresh machine.

## Stop Conditions

Pause and ask for direction if any of these happen:

- Existing unrelated files change unexpectedly.
- A retrieval change improves one metric but worsens groundedness.
- A UI change hides trust signals completely.
- A new dependency is required for the planned fix.
- A command would delete user data or derived artifacts without explicit approval.

## Overnight Priority Order

1. Preserve passing tests and build.
2. Expand eval labels.
3. Improve citation selection.
4. Simplify answer presentation.
5. Update docs and commit.

## Tomorrow Demo Checklist

- Load golden demo.
- Upload a fresh PDF.
- Ask a direct factual question.
- Ask a summary question.
- Ask an unanswerable question.
- Show citation trail.
- Export answer.
- Show local-first privacy statement.
- Mention known RAG Reliability Phase targets honestly.


## 2026-07-11 Sprint Boundary Update

MegaSprint Two is now closed after the chat-first UI simplification, source drawer, answer readability, composer, responsive, and accessibility polish slices were build-verified.

Next active sprint:

- MegaSprint Three: Academic workflow depth.
- Plan: `docs/megasprint_three_plan.md`.
- Focus: Paper Lab, Exam Lab, diagram grounding, study guides, and source-grounded exports.

Priority order changes from UI shell polish to academic workflow correctness while keeping the UI simple.

## 2026-07-12 Release-Hardening Checkpoint

The release gate is green again after fixing the Windows PowerShell child-process exit-code capture in `scripts/ship_check.ps1`.

Completed:

- Isolated backend test runtime paths from production SQLite, Chroma, upload, and parse-cache paths.
- Delegated API tests from `ship_check.ps1` to `test_api.ps1`.
- Ran the Next.js build through a bounded native process wrapper with logs in `temp\runtime`.
- Bound the process handle before `WaitForExit()` so PowerShell reliably exposes the child exit code.

Verification:

- `npm.cmd run ship:check`: passed.
- Backend: `95 passed`, `1 warning`.
- Web production build: passed.
- Publish smoke and golden demo: passed.
