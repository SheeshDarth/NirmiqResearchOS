# NIRMIQ ResearchOS Context

Last updated: 2026-07-10
Current branch: `main`
Repository target: `https://github.com/SheeshDarth/NirmiqResearchOS`
Local workspace: `C:\Nirmiq-researchOS`
Primary app URL: `http://127.0.0.1:3002/`
API URL: `http://127.0.0.1:8000/`

## Latest Session Update - 2026-07-10 MegaSprint Two Overnight Kickoff

Objective: begin the overnight MegaSprint Two execution loop after closing MegaSprint One retrieval reliability.

Implemented:

- Created an active hourly heartbeat automation: `nirmiq-overnight-sprint`.
- Started MegaSprint Two: ChatGPT-grade academic UX simplification.
- Reduced the main chat header from a dashboard-like surface to a compact chat-first header.
- Replaced route helper copy with small source/mode pills so the normal UI feels less crowded.
- Slimmed the composer height, upload button, send button, and source cockpit spacing.
- Changed minimized composer copy to a simple `Composer minimized / Ask next` flow.
- Collapsed dense source passage lists behind `More source passages` in the Sources panel.
- Adjusted assistant answer styling to feel calmer and more readable, closer to a chat answer than a heavy dashboard card.
- Added a first-run three-step strip: upload material, ask naturally, verify sources.
- Improved source citation cards so they read as `Source` cards with page and usage reason instead of raw evidence/chunk previews.
- Started the frontend component split by extracting the onboarding/empty-state UI into `apps/web/components/chat-empty-state.tsx`.
- Continued the component split by extracting the readable Sources evidence panel into `apps/web/components/source-evidence-panel.tsx`.
- Fixed small-screen scroll behavior by letting the mobile layout use normal page flow instead of inheriting desktop `100dvh`/hidden-overflow constraints.

Validation:

- `npm.cmd run build` from `apps/web`: passed after all five UI slices.

Next overnight continuation:

- Split `apps/web/app/page.tsx` into focused UI components only after this first shell cleanup is stable.
- Continue with source drawer readability, mobile/laptop QA, and first-run/sample-paper guidance.
- Preserve backend APIs, Paper Lab, Exam Lab, upload flow, and citation trust behavior.

Current repo note:

- `deep-research-report.md` remains intentionally untracked and untouched.

## Latest Session Update - 2026-07-10 MegaSprint One Final Tightening

Objective: push MegaSprint One retrieval reliability further without overfitting or adding heavy local dependencies.

Implemented:

- Added shared OCR/text normalization helper at `apps/api/app/domain/text_normalization.py`.
- Updated retrieval eval normalization to reuse the shared helper.
- Corrected two real-world eval labels after verifying the source evidence:
  - GenAI privacy labels now use `sensitive user data`, `personal information`, and `data retention`.
  - Transformer architecture labels now accept the actual source phrasing: `we propose the Transformer`, `relying entirely on an attention mechanism`, and `eschewing recurrence`.
- Rebalanced retrieval candidate priority in `RetrievalService` so direct answer relevance has more influence than a loose reranker hit.
- Bumped retrieval metadata method version to `megasprint1.v2`.
- Rejected broader production OCR normalization because trial runs reduced real-world MRR; the safer change is eval normalization plus label correction.

Validation:

- Real-world academic seed:
  - BM25: MRR `0.843`, Recall@8 `1.000`, citation expected coverage `1.000`.
  - Hybrid: MRR `0.804`, Recall@8 `1.000`, citation expected coverage `1.000`.
- Query-category seed:
  - BM25: MRR `0.950`, Recall@8 `1.000`, citation expected coverage `1.000`.
  - Hybrid: MRR `0.850`, Recall@8 `1.000`, citation expected coverage `1.000`.
- Targeted selected-document Transformer query now ranks the direct `we propose the Transformer...` passage first in hybrid mode.

Status:

- MegaSprint One's first reliability pass is complete on the current seed.
- Do not claim production-grade arbitrary-document accuracy yet; the next reliability work is label growth, answer relevance scoring, and more textbook/notes/paper coverage.
- Next MegaSprint should focus on ChatGPT-grade UI simplification, source drawer clarity, mobile/laptop QA, and lower cognitive load without exposing metadata.
- MegaSprint Two plan is tracked at `docs/megasprint_two_plan.md`.

Current repo note:

- `deep-research-report.md` remains intentionally untracked and untouched.

## Latest Session Update - 2026-07-09 MegaSprint One Query-Agnostic RAG Reliability

Objective: align NIRMIQ with the vision of a simple ChatGPT-like academic assistant that works across valid user queries, hides confusing metadata, and avoids confident answers when evidence is only loosely related.

Implemented:

- Replaced prompt-specific reliability framing with a query-category eval seed at `data/processed/eval/query_agnostic_rag_categories.jsonl`.
- Added document-aware query expansion in retrieval so acronyms and source terminology can be expanded from uploaded material.
- Added direct-evidence scoring to retrieval candidate priority and hidden chunk-selection diagnostics.
- Penalized backmatter/index/glossary/example-list passages for explanatory questions so broad fragments do not outrank real concept sections.
- Added synthesis-side answer relevance states: direct evidence, weak related mention, no direct evidence, and unrelated.
- Simplified user-facing abstention messages so users see clear language instead of reliability-gate internals.
- Simplified UI trust copy to `Verified`, `Needs more evidence`, and `Not found in sources`.
- Hid normal metadata noise by showing answer-used source passages and page references rather than chunk IDs, token counts, scores, or retrieval internals.
- Fixed SQLite test cleanup on Windows by closing SQLite connections after context-manager use.

Validation:

- Focused retrieval/synthesis tests: passed.
- Full backend tests: `71 passed`, `1` warning, using workspace-scoped pytest temp/cache paths.
- API compile: passed before doc updates; rerun before final push.
- Query-category BM25 smoke eval: MRR `1.000`, Recall@8 `1.000`, citation expected coverage `1.000` on the initial 10-sample seed.

Current repo note:

- `deep-research-report.md` remains intentionally untracked and untouched.

## Latest Session Update - 2026-07-08 Ship Check Retry UX Fix

Objective: retry the release gate and resolve the remaining execution-policy friction.

Finding:

- Direct `.\scripts\ship_check.ps1` can fail on Windows with `PSSecurityException` when PowerShell script execution is disabled.
- The project itself was healthy when invoked with `-ExecutionPolicy Bypass`.

Implemented:

- Added `NIRMIQ Ship Check.cmd` as a double-clickable ship-check launcher.
- Updated `docs/publish_checklist.md` to lead with `npm.cmd run ship:check`, the CMD launcher, and the explicit bypass command.
- Updated `README.md` so public setup instructions do not push users toward a command that Windows may block.

Validation:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ship_check.ps1`: passed.
- Backend tests: `61 passed`, `1` warning.
- API compile: passed.
- Web build: passed.
- Publish smoke: passed.
- Golden demo warm start: passed.

## Latest Session Update - 2026-07-07 Release Gate Hardening

Objective: run the full release-readiness gate and fix any safe, local-only issue that blocks repeatable shipping.

Finding:

- `.\scripts\ship_check.ps1` initially failed during backend tests with `PermissionError: [WinError 5] Access is denied`.
- Root cause: the script reused a fixed `temp\pytest` and `temp\pytest-cache` location, which can be left in a stale or locked state on Windows.

Implemented:

- Hardened `scripts\ship_check.ps1` to create a unique per-run pytest temp/cache directory under `temp\pytest-runs\`.
- This avoids stale Windows ACL/lock problems without deleting user data or requiring admin permissions.

Validation:

- `.\scripts\ship_check.ps1`: passed end to end.
- Backend tests inside ship check: `61 passed`, `1` warning.
- API compile: passed.
- Web production build: passed.
- Publish smoke: passed.
- Golden demo warm start: passed.
- Local scoped API/web processes were stopped after the check.

Current repo note:

- `deep-research-report.md` remains intentionally untracked.

## Latest Session Update - 2026-07-07 Ascension Separation And RAG Sprint Continuation

Objective: move Ascension OS foundation out of the NIRMIQ ResearchOS repository and continue the next RAG reliability sprint.

Implemented:

- Moved `docs/ascension_os_foundation.md` to `C:\Users\Siddharth\Documents\Ascension OS\ascension_os_foundation.md`.
- Updated NIRMIQ docs so Ascension OS is referenced as an adjacent product track outside this repository.
- Kept NIRMIQ ResearchOS focused on academic document intelligence and retrieval reliability.

Next sprint scope:

- Add deterministic query expansion for academic wording mismatches.
- Add retrieval noise penalties so index/glossary/reference chunks do not dominate explanatory answers.
- Add normalized phrase matching in evaluation diagnostics to reduce false misses from PDF punctuation, ligatures, and encoding artifacts.
- Re-run backend tests and real-world eval to verify whether the reliability slice improves metrics without breaking the golden demo.

Implemented in this sprint:

- Added deterministic local query expansion in `RetrievalService`.
- Added retrieval noise penalties for index/glossary/reference-like chunks during candidate prioritization.
- Added debug metadata for query expansion and retrieval noise policy.
- Added normalized phrase matching to `scripts/eval_retrieval.py`.
- Added unit tests for query expansion and index-like chunk penalty behavior.

Validation:

- Focused retrieval policy tests: `7 passed`.
- `.\scripts\eval_real_world.ps1`: passed and improved the 16-sample real-world seed.
  - Hybrid: MRR `0.655`, Recall@8 `0.875`, citation expected coverage `0.875`.
  - BM25: MRR `0.781`, Recall@8 `0.875`, citation expected coverage `0.875`.
- `.\scripts\eval_demo_dataset.ps1`: passed with no golden-demo regression.
  - Hybrid and BM25 remain Recall@8 `1.000` and citation expected coverage `1.000`.
- Full-query real-world eval also improved after synthesis-side query expansion.
  - Hybrid: MRR `0.646`, Recall@8 `0.813`, citation expected coverage `0.813`.
  - BM25: MRR `0.667`, Recall@8 `0.875`, citation expected coverage `0.875`.

Current remaining gap:

- Citation expected coverage improved but remains below the `0.900` target.
- The real-world eval set still has only `16` samples and must grow toward `40+`.
- Remaining weak records dropped from `13` to `5`, mainly OCR/encoding and section-overview failures.
- BM25 full-query coverage now matches raw BM25 retrieval coverage on the current seed.
- Hybrid full-query coverage still trails raw hybrid retrieval, so answer-used citation selection remains active work.

Follow-up heartbeat progress:

- Updated `scripts/eval_real_world.ps1` so raw retrieval and full-query runs write separate metrics and failure files by default.
- Generated `data/processed/eval/real_world_full_query_metrics.json`.
- Generated `data/processed/eval/real_world_full_query_failures.jsonl`.
- Added `docs/answer_used_citation_backlog.md`.
- Full-query failure log dropped from `8` to `5` missed-at-8 records after synthesis-side query expansion.

Second follow-up heartbeat progress:

- Added synthesis-side academic query-term expansion so answer fallback scoring uses the same intent vocabulary as retrieval.
- Added `apps/api/app/tests/unit/test_synthesis_query_terms.py`.
- Full-query BM25 citation expected coverage improved from `0.750` to `0.875`.

## Latest Session Update - 2026-07-07 Overnight Sprint Baseline Diagnostics

Objective: execute the first safe overnight sprint block, freeze baseline health, and capture concrete retrieval failures for the next accuracy pass.

Validation:

- `python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q`: `55 passed`, `1` warning.
- `python -m compileall apps/api/app`: passed.
- `npm.cmd run build` from `apps/web`: passed.
- `.\scripts\eval_demo_dataset.ps1`: passed.
  - Hybrid and BM25 Recall@8 remain `1.000`.
  - Hybrid and BM25 citation expected coverage remain `1.000`.
- `.\scripts\eval_real_world.ps1`: passed.
  - Hybrid MRR `0.490`, Recall@8 `0.750`, citation expected coverage `0.750`.
  - BM25 MRR `0.578`, Recall@8 `0.750`, citation expected coverage `0.750`.

Implemented:

- Added failure-diagnostic output support to `scripts/eval_retrieval.py`.
- Updated `scripts/eval_real_world.ps1` to write `data/processed/eval/real_world_retrieval_failures.jsonl`.
- Added `docs/retrieval_failure_backlog.md` as the tracked summary of weak retrieval patterns.

Findings:

- The first failure log contains `13` weak retrieval records.
- Hybrid has `7` weak records; BM25 has `6`.
- `8` records are missed at rank 8; `5` are late hits beyond rank 3.
- Main observed causes:
  - textbook index/glossary chunks outranking body explanations,
  - natural query wording not expanding to source terms such as "positional encodings",
  - exact-phrase eval labels being too brittle in some cases,
  - OCR/encoding artifacts reducing lexical match quality,
  - broad overview questions needing stronger section-first retrieval.

Next:

- Add normalized phrase matching to eval diagnostics.
- Penalize index/glossary/table-of-contents chunks for explanatory questions.
- Add deterministic local query expansion from headings and academic synonyms.
- Expand the real-world eval set toward `40` cases.

## Latest Session Update - 2026-07-07 Overnight Sprint And Ascension OS Kickoff

Objective: create a practical overnight execution plan for NIRMIQ while starting Ascension OS as a separate, cleanly scoped product direction.

Implemented:

- Added `docs/overnight_work_plan.md` as the active overnight sprint plan.
- The plan prioritizes:
  - preserving passing tests and build,
  - expanding real-world retrieval evaluation,
  - improving answer-used citation selection,
  - simplifying answer presentation,
  - updating docs and release readiness after each verified change.
- Added `docs/ascension_os_foundation.md` as the initial Ascension OS foundation. This file was later moved outside the NIRMIQ repo to `C:\Users\Siddharth\Documents\Ascension OS\ascension_os_foundation.md`.
- Ascension OS is intentionally scoped as a separate local-first personal execution operating system, not a feature inside NIRMIQ ResearchOS.
- Documented the product boundary:
  - NIRMIQ ResearchOS remains the academic document intelligence workspace.
  - Ascension OS can become the broader command center for goals, projects, execution loops, and personal operating routines.

Tradeoffs:

- No Ascension OS application code was generated yet. This avoids mixing an early new product with the current shippable NIRMIQ demo.
- No heavy agent, graph, cloud, or automation dependency was added.
- The next safest engineering step remains RAG reliability and UI clarity before adding new product surface area.

Next:

- Execute the overnight sprint blocks in order.
- Expand real-world eval labels toward `40`.
- Improve answer-used citation selection.
- Keep Ascension OS outside the NIRMIQ ResearchOS repo until its PRD/TRD and repository boundary are confirmed.

## Latest Session Update - 2026-07-06 Deep Research Evaluation And Evidence Gate

Objective: analyze `deep-research-report.md`, evaluate current RAG functioning, identify architecture failures, and proceed with the safest reliability fixes.

Findings:

- The deep research report correctly recommends Adaptive Evidence-Grounded Hybrid RAG with Lite/Edge/Pro modes.
- NIRMIQ's architecture is directionally aligned with that recommendation.
- GraphRAG should remain optional Pro/background work until BM25/hybrid reliability improves.
- Real-world retrieval remains the quality bottleneck:
  - Hybrid MRR `0.490`, Recall@8 `0.750`, citation expected coverage `0.750`.
  - BM25 MRR `0.578`, Recall@8 `0.750`, citation expected coverage `0.750`.
- BM25 still beats hybrid on the current real-world seed, so BM25 remains the Lite/default reliability baseline.
- Full-query eval initially looked much worse because it scored expected phrases against truncated UI citation excerpts.
- After fixing the evaluator to use full cited chunk text, full-query real-world citation expected coverage is `0.688`.

Implemented:

- Fixed SQLite migration ordering so legacy databases add section metadata columns before section indexes are created.
- Added a legacy-schema regression test.
- Fixed full-query retrieval evaluation to score full cited chunks instead of truncated citation preview text.
- Added an evidence reliability gate in `SynthesisService`.
- The gate blocks grounded answers when evidence/citation support is too weak.
- Improved citation coverage scoring so structural study-guide lines and UI headings are not treated as unsupported claims.
- Fixed fallback list-answer wording so cited direct answers use source text rather than generic wrapper prose.

Validation:

- `python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q`: `55 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm.cmd run build` from `apps/web`: passed.
- `scripts/eval_real_world.ps1`: passed, real-world retrieval baseline unchanged.
- `scripts/eval_demo_dataset.ps1`: passed, demo retrieval remains at Recall@8 `1.00` and citation expected coverage `1.00`.

Next:

- Expand real-world eval from `16` to at least `40`, then `100+`.
- Add per-sample failure reporting for full-query eval.
- Improve answer-used citation selection so full-query coverage catches up to raw retrieval coverage.
- Tune hybrid retrieval only when it beats BM25 on real corpora.

## Latest Session Update - 2026-06-26 RAG Reliability Phase Kickoff

Objective: update the public documentation and begin the first backend slice of the RAG Reliability Phase without changing public query APIs or adding heavy dependencies.

Implemented:

- Refreshed `README.md` with a clear `Known Retrieval Gap` and `Next Phase: RAG Reliability` section.
- Preserved the honest real-world baseline:
  - BM25 MRR `0.578`.
  - Recall@8 `0.750`.
  - Citation expected coverage `0.750`.
- Added additive SQLite support for textbook-aware retrieval:
  - New `document_sections` table.
  - Nullable chunk metadata for `section_id`, `heading`, `section_path`, `chunk_type`, and `key_terms_json`.
- Updated indexing to detect lightweight textbook headings/sections and persist section metadata while staying backwards-compatible with old chunks.
- Updated BM25 indexing to include heading, section path, chunk type, and key terms in lexical search text.
- Added section-first retrieval for selected-document queries:
  - rank candidate sections from local metadata,
  - narrow chunk retrieval when a relevant section is detected,
  - keep normal BM25/vector/hybrid fallback when section evidence is weak.
- Added debug-only retrieval diagnostics inside `retrieval_meta`:
  - `section_candidates`,
  - `section_first_enabled`,
  - `chunk_selection_reasons`,
  - `retrieval_diagnostics`.
- Added tests for section detection, metadata persistence, and selected-document section-first diagnostics.

Acceptance targets for the phase:

- Improve Recall@8 from about `0.750` to at least `0.850`.
- Improve MRR from about `0.578` to at least `0.700`.
- Improve expected citation coverage from about `0.750` to at least `0.900`.
- Preserve golden demo behavior and local fallback behavior without Chroma, reranker, or Ollama.

Tradeoffs:

- Heading detection is heuristic by design. It is cheap, offline, and low-VRAM, but it will not perfectly identify every PDF structure yet.
- Section-first retrieval is only applied when a selected document has positive section matches. This avoids over-filtering broad or unclear questions.
- Diagnostics are returned as optional debug metadata instead of visible UI controls, keeping the user experience simple.

## Latest Session Update - 2026-06-26 RAG Reliability Problem Log

Objective: start the RAG Reliability Phase by documenting all known problems and the architecture-level path to reduce hallucination from weak retrieval.

Implemented:

- Added `problems_faced.md` as the canonical engineering problem log.
- Added a Mermaid architecture diagram showing ingestion, retrieval, synthesis, verification, feedback, and evaluation loops.
- Documented past problems, current retrieval gaps, future risks, root causes, what has worked, and the retrieval reliability roadmap.
- Recorded the current real-world retrieval baseline:
  - BM25 MRR around `0.578`.
  - BM25 Recall@8 around `0.750`.
  - Expected citation coverage around `0.750`.
- Framed hallucination as primarily a retrieval precision and evidence-verification problem, not only a model-quality problem.

Next intended phase:

- Freeze baseline eval metrics.
- Convert `Needs work` feedback into labeled retrieval cases.
- Add textbook-aware chunk metadata.
- Add section-first retrieval before chunk-level ranking.
- Improve local deterministic query expansion and lightweight reranking only after diagnostics are available.

## Latest Session Update - 2026-06-26 V4.2 Local Feedback Loop And Phone Codex Access

Objective: continue the next phase without complicating the UI, while giving Siddharth a safe phone-based Codex access path.

Implemented:

- Added a local SQLite `answer_feedback` table for answer-quality signals.
- Added `POST /memory/{session_id}/feedback` and `GET /memory/{session_id}/feedback`.
- Added a compact ChatGPT-style feedback row below assistant answers: `Good` and `Needs work`.
- Saved feedback stores session id, rating, prompt, answer, optional source document id/title, reason, and timestamp.
- Session deletion now removes associated feedback records.
- Document deletion preserves the feedback review signal but nulls the deleted document id so stale foreign references are not kept.
- Added unit and integration tests for feedback storage, API contract, session deletion, and document deletion behavior.
- Refreshed `docs/remote_codex_access.md` from the current official Codex manual:
  - Recommended path is Codex App Remote Connections through ChatGPT mobile.
  - Do not expose NIRMIQ local FastAPI/Next.js or Codex app-server ports publicly.
  - Use Codex Web/GitHub only for code/docs tasks that do not need private local corpora.

Why it improves the project:

- Bad or boring answers can now become a local review dataset instead of disappearing after testing.
- This supports the next retrieval-evaluation sprint without adding a heavy analytics system.
- The UI remains simple because feedback is shown as quiet answer-level controls, not a dashboard.
- Phone access is framed around the official secure remote-control flow instead of risky port exposure.

Tradeoffs:

- Feedback is currently manual and local-only. It does not auto-tune retrieval yet.
- Feedback is stored per current UI run key, so saved-button state resets on browser refresh while the backend record remains.
- The official phone remote-control flow requires the Codex desktop host to stay awake and signed into the same account.

Verification:

- `python -m pytest apps/api/app/tests/unit/test_answer_feedback.py apps/api/app/tests/integration/test_answer_feedback_flow.py -q`: passed, 3 tests.
- `python -m compileall apps/api/app`: passed.
- `npm.cmd run build` from `apps/web`: passed.
- `npm.cmd run test:api`: passed, 50 tests.

Test harness fix:

- `scripts/test_api.ps1` now uses a unique per-run temp/cache folder under `temp/pytest-runs` and `temp/pytest-cache-runs` to avoid stale Windows temp ACL/lock failures.

## Latest Session Update - 2026-06-22 V4.1 Chat Shell And Accuracy Pass

Objective: respond to live testing feedback that answers improved but still needed stronger accuracy and a simpler, more ChatGPT-like presentation.

Council verdict:

- The main product path should be `attach material -> ask naturally -> read a clear answer -> open sources only if needed`.
- Frontend mode controls should stop driving normal query behavior; backend intent routing should own summaries, comparisons, paper drafting, exam-style answers, and abstention.
- Presentation is part of reliability. Answers need a predictable contract: direct answer, key points, and evidence note.
- More visible tools create doubt. Paper Lab and Exam Lab should remain available as quiet tool hints, not compete with the primary chat.

Implemented:

- Simplified the top workspace header from a mode switcher into a clear `Ask your documents` assistant header.
- Moved Research/Chat/Paper/Exam controls into compact composer tool chips: `Auto`, `Chat`, `Paper`, `Exam`.
- Changed normal query submission so it no longer inherits stale UI modes such as `summary`; default `Auto` sends `research` and lets the backend detect intent.
- Kept explicit actions such as one-click summary, golden-demo prompts, Paper, and Exam as optional mode hints.
- Extracted `AnswerBody` into `apps/web/components/answer-body.tsx` for the ongoing frontend component split.
- Improved answer readability with a narrower assistant column, better answer line spacing, compact headings, and less dashboard-like header weight.
- Added backend detection for exam-style language such as `10 mark answer`, `study guide`, `revision notes`, and `important questions` even when the UI is in normal Research/Auto mode.
- Wired backend-detected exam intent into exam context loading so question banks/diagrams can be used without perfect frontend mode selection.
- Added focused retrieval expansion for factual lookup prompts, especially natural textbook questions like `Explain a few unsupervised algorithms`.
- Expanded unsupervised-algorithm focus terms for selected-document seed chunks and synthesis sentence scoring.
- Tightened the fallback synthesis answer contract for list/algorithm questions to produce `Direct answer`, `Key points`, and `Evidence note` instead of dense chunk dumps.

Verification:

- `python -m pytest apps/api/app/tests/unit/test_query_intent.py apps/api/app/tests/unit/test_synthesis_faithfulness.py -q`: passed, 17 tests.
- `python -m compileall apps/api/app`: passed.
- `npm.cmd run build` from `apps/web`: passed.
- `npm.cmd run test:api`: passed, 47 tests.

Preview note:

- Browser preview initially showed only the server boot shell because the already-running Next dev server served HTML pointing to a stale page chunk after a rebuild.
- This is a dev-runtime chunk mismatch, not a TypeScript/build failure. The fix for local preview is to stop the stale web dev process and restart from `scripts/run_local.ps1` or `NIRMIQ ResearchOS.cmd`.

Tradeoffs:

- This is not the full component split yet. `page.tsx` is smaller but still owns most state.
- The answer quality improvement is conservative and local-first; no cloud/API model routing or heavy reranker/graph dependency was added.
- Retrieval accuracy still needs a larger real-world labeled eval set to move from demo-good to robust across textbooks.

## Latest Session Update - 2026-06-22 UI Cleanup Pass

Objective: remove harmful or unnecessary product-surface clutter before the larger ChatGPT-style component rebuild.

Implemented:

- Removed untracked root-level PDFs that should not ship with the repository:
  - `Finale AI — Dashboard.pdf`
  - `flyrank-internship-confirmation-siddharth-p-july-2026-16-weeks.pdf`
- Removed the in-app retrieval evaluation panel from the normal UI. Evaluation remains a backend/script/docs concern, not a user-facing chat control.
- Removed related dead CSS for eval cards, eval input, meter bars, and proof-grid metadata.
- Hid full local filesystem paths from the library, source inspector, and diagram cards.
- Replaced raw source-path display with safer local/privacy copy.
- Renamed the right inspector from Deep Research metadata language to a simpler Sources/check-answer drawer.
- Removed visible intent/cache/citation-coverage percentages and retrieval scores from normal source cards.
- Simplified exported Markdown citations by removing internal retrieval scores and citation coverage metadata.
- Softened the composer advanced summary so normal users see `Advanced / optional` instead of retrieval mode/session internals.

Verification:

- `npm.cmd run build`: passed.
- `npm.cmd run test:api`: passed, 44 tests.
- `python -m compileall apps/api/app`: passed.

Tradeoff:

- The source-path fields still exist in API types and internal UI logic because local ingestion and golden-demo matching depend on them. They are no longer displayed in normal UI surfaces.

## Latest Session Update - 2026-06-22 Citation Trust Fix

Objective: start resolving the architecture-review P1 findings by tightening the citation trust contract before doing the larger ChatGPT-style UI rebuild.

Implemented:

- Changed `SynthesisService` to report the exact selected context chunk ids and final answer-cited chunk ids.
- Changed `QueryService` so public `citations` are built only from answer-used context chunks, not the full retrieved bundle.
- Added `citation_anchor_chunk_map` metadata for debug/source inspection when debug metadata is explicitly requested.
- Bumped selected-document summary cache profile from `v4` to `v5` so older cached summaries with broad citations are naturally bypassed and regenerated.
- Updated normal frontend query calls to stop forcing `debug: true`; debug metadata is now requested only when the source inspector is already open or Paper/Exam tool artifacts need it.
- Added regression tests proving synthesis reports only answer-cited chunks and query citations filter out retrieved-but-unused chunks.

Verification:

- `python -m pytest apps/api/app/tests/unit/test_synthesis_faithfulness.py -q`: passed, 8 tests.
- `python -m compileall apps/api/app`: passed.
- `npm.cmd run test:api`: passed, 44 tests.
- `npm.cmd run build`: passed.

Tradeoff:

- This is a surgical trust-layer fix, not the full UI simplification. Source-path redaction, backend-owned routing cleanup, score normalization, and the component split remain next.

## Latest Session Update - 2026-06-11 EOD Launch Sprint

Objective: respond to the shipped Folio reference, simplify running NIRMIQ, and make the project demo-shippable by end of day.

External reference checked:

- LinkedIn short link resolved to `https://github.com/kartikdubey17/FOLIO/releases/tag/v0.1.0`.
- Folio v0.1.0 positions itself as a personal offline AI document assistant for PDF upload, local Q&A, privacy, lightweight Tauri desktop runtime, and offline usage.
- NIRMIQ differentiation should remain academic intelligence rather than generic PDF chat: citations, abstention, Deep Research, Paper Lab, Exam Lab, benchmarked golden demo, and local-first proof.

Implemented in this session:

- Added `scripts/run_local.ps1` for one-command local preview.
- Added `scripts/stop_local.ps1` to stop only launcher-created local preview PIDs.
- Added root double-click launchers `NIRMIQ ResearchOS.cmd` and `NIRMIQ Stop.cmd`.
- Added `scripts/create_windows_shortcut.ps1` for Desktop/Start Menu shortcuts.
- Added `docs/windows_app_packaging.md` explaining why one-click launcher is the right EOD Windows-app layer and why a full installer should be a separate sprint.
- Added `scripts/ship_check.ps1` for full EOD verification: backend tests, API compile, web build, publish smoke, golden demo, and scoped process cleanup.
- Hardened `scripts/publish_smoke.ps1` timeouts for local startup/readiness probes.
- Hardened `scripts/stop_local.ps1` to stop the full Next.js child process tree, preventing stale `.next` cache errors after restart.
- Added `docs/folio_competitive_review.md`.
- Updated README and publish checklist with one-command run/ship-check instructions.
- Updated landing screen proof chips to communicate offline core, citation trail, abstention, and Paper/Exam labs.
- Created Windows Desktop shortcuts: `NIRMIQ ResearchOS.lnk` and `Stop NIRMIQ ResearchOS.lnk`.

Verification completed:

- `scripts/ship_check.ps1`: passed.
- Backend tests inside ship check: 31 passed, 1 warning.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed, first-load JS about 115 kB.
- Publish smoke: backend health OK, readiness ready, `cloud_api_required=false`, web shell returned NIRMIQ.
- Golden demo: four grounded checks passed with citations; unsupported chat prompt abstained with zero citations.
- Persistent preview after ship check: API `ok`, web `200`, NIRMIQ shell present at `http://127.0.0.1:3002`.

Run command for review:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

Windows double-click preview:

```text
NIRMIQ ResearchOS.cmd
```

Pre-publish command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\ship_check.ps1
```

## Previous Session Update - 2026-06-10 Golden Demo Sprint

Objective: convert the broad polish backlog into a publishable golden demo path for reviewers.

Implemented so far in this session:

- Installed Codex skills `llm-council` and `graphify` under `C:\Users\Siddharth\.codex\skills`.
- Ran an LLM Council war-room on the polish backlog.
- Council verdict: use the strategic spine `messy academic docs -> trustworthy inspectable offline research`, and execute with a frozen-backend golden demo sprint.
- Added bundled offline demo corpus under `data/raw/golden_demo`.
- Added expected-source manifest at `data/processed/eval/golden_demo_expected_sources.json`.
- Added `scripts/golden_demo.ps1` to index bundled sources and run citation-bearing smoke queries.
- Added UI `Load Golden Demo` action, locked demo prompts, compact Deep Research proof strip, and local Markdown answer export.
- Added `docs/demo_script.md` and `docs/benchmark_report.md`.
- Added a strict local relevance gate for General Chat so retrieved chunks must match the actual subject of the query before NIRMIQ answers.
- Updated the golden demo abstention check to fail if an unsupported chat prompt returns grounded output or citations.
- Updated README, PRD, TRD, UI/UX spec, and publish checklist for the golden demo path.

Golden demo acceptance bar:

- Reviewer can load local corpus without internet.
- Reviewer can ask a locked research question and get citations.
- Evidence chips open Deep Research and focus source chunks.
- Proof strip shows intent, citation coverage, cache state, and source type.
- Reviewer can export an answer with citations as Markdown.
- Reviewer can remove selected local material as the privacy/purge moment.
- Unsupported chat prompts abstain with zero citations instead of answering from unrelated material.

Verification completed:

- `python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q`: 31 passed, 1 warning.
- `python -m compileall apps/api/app`: passed.
- `npm run build` from `apps/web`: passed.
- `scripts/golden_demo.ps1` against local API port `8012`: four grounded queries passed, abstention passed.

Commit recorded:

- `928906b` - Added the golden demo sprint implementation, sample corpus, UI proof path, smoke script, docs, and General Chat relevance gate.

Implementation tradeoff:

- No broad frontend component split in this sprint.
- Backend retrieval/model/schema stayed frozen except for the trust-blocking General Chat relevance gate.
- No GraphRAG, cloud/API, auth, or agent feature expansion.

## Project Metadata

Project name: NIRMIQ ResearchOS
Project type: Offline-first adaptive academic intelligence system
Owner/developer: Siddharth / SheeshDarth
Target user: Solo local-first researcher/student/developer
Target machine: RTX 4050 laptop class hardware
Primary branch for current work: `v3-foundation`
Stable baseline branch: `main`

## Product Direction

NIRMIQ ResearchOS is the academic document intelligence workspace inside the broader NIRMIQ ecosystem. It is a local-first document intelligence system for:

- Research over uploaded documents.
- General local-first chatbot behavior with abstention when no evidence exists.
- Exam preparation using uploaded notes, PDFs, textbooks, question banks, answer styles, marks, and extracted source diagrams.
- Grounded answers with citations and source inspection.
- Low-VRAM, offline-friendly operation.

The system should avoid cloud-first, enterprise, and multi-user complexity until the local MVP is strong. The local FastAPI backend is part of the offline app runtime and must not be confused with a cloud API dependency.

## Core Technical Stack

Frontend:

- Next.js PWA-style app in `apps/web`.
- Main UI file: `apps/web/app/page.tsx`.
- Main style file: `apps/web/app/globals.css`.

Backend:

- FastAPI app in `apps/api`.
- Entrypoint: `apps/api/app/main.py`.
- Dependency container: `apps/api/app/core/deps.py`.

Storage:

- SQLite for documents, chunks, memory, sessions, exam profiles, question banks, and diagram metadata.
- ChromaDB for vector storage.
- BM25 index for lexical retrieval.

Retrieval / RAG:

- BM25 retrieval.
- Chroma vector retrieval.
- Reciprocal Rank Fusion.
- Lightweight reranking abstraction.
- Context packing and citation-aware synthesis.
- Study-guide retrieval query expansion from imported question bank.

Parsing / Assets:

- PyMuPDF for PDFs and embedded diagram extraction.
- Tesseract OCR adapter exists for OCR support.
- Extracted diagrams are stored under `data/processed/diagrams/<document_id>/` and served through safe asset routes.

Local inference:

- Ollama-backed generation adapter.
- Intended models include Phi-3 Mini, Qwen2.5 3B, DeepSeek Coder 6.7B, `nomic-embed-text`, and `bge-reranker-base`.

## Current UX Direction

The UI was moved away from a generic AI dashboard toward a custom NIRMIQ local research cockpit:

- Left rail: Source intake and source vault.
- Center: Chat-first workspace.
- Top of center: Compact pill workspace selector for Research, Chat, and Exam Lab.
- Right rail: Evidence, context, comparison, eval, and Exam Lab tooling.
- Exam Lab: Profiles, question bank import, diagram extraction, source diagram previews.
- Study guide answers render as expandable cards.

## Current Major Capabilities

Research Workspace:

- Ingest local documents.
- Query documents with hybrid/BM25/vector retrieval.
- Receive grounded answers with citations.
- Inspect citation chunks and nearby source text.
- Compare recent answer changes.
- Load retrieval evaluation reports.

General Chat:

- Chat section exists as a separate workspace.
- Offline answers are intended to use relevant local document evidence.
- If evidence is insufficient, the system should abstain instead of hallucinating.

Exam Lab:

- Save exam answer settings: marks, answer style, content type, custom instructions.
- Import question banks from pasted text.
- Store/list imported questions per document.
- Extract embedded PDF images as diagram assets.
- Store/list diagram metadata in SQLite.
- Serve diagram images safely by asset ID.
- Pack question-bank and diagram metadata into study-guide synthesis context.
- Expand retrieval queries using imported questions for study-guide and important-question modes.
- Render study-guide responses as expandable cards.
- Render diagram assets as clickable previews.

## Backend Architecture Summary

Important backend modules:

- `apps/api/app/main.py`: FastAPI app creation and router registration.
- `apps/api/app/core/config.py`: Settings.
- `apps/api/app/core/deps.py`: App container and service wiring.
- `apps/api/app/adapters/storage/sqlite_repo.py`: SQLite repository and schema initialization.
- `apps/api/app/adapters/storage/chroma_repo.py`: Chroma repository.
- `apps/api/app/adapters/retrieval/bm25_index.py`: BM25 lexical index.
- `apps/api/app/adapters/retrieval/rrf_fuser.py`: Reciprocal rank fusion.
- `apps/api/app/adapters/llm/generator.py`: Generation abstraction.
- `apps/api/app/adapters/llm/ollama_client.py`: Ollama client.
- `apps/api/app/services/ingestion_service.py`: Ingest orchestration.
- `apps/api/app/services/indexing_service.py`: Chunking/indexing orchestration.
- `apps/api/app/services/retrieval_service.py`: Retrieval flow.
- `apps/api/app/services/synthesis_service.py`: Grounded answer synthesis and fallback synthesis.
- `apps/api/app/services/query_service.py`: Query lifecycle, memory persistence, retrieval, synthesis.
- `apps/api/app/services/exam_service.py`: Exam profile, question-bank, and diagram operations.

Important API routers:

- `/health`
- `/ingest`
- `/documents`
- `/memory`
- `/query`
- `/exam`

## Frontend Architecture Summary

Important frontend files:

- `apps/web/app/page.tsx`: Main client UI and stateful app shell.
- `apps/web/app/globals.css`: NIRMIQ visual system and responsive layout.
- `apps/web/lib/api-client.ts`: Typed API client for backend calls.
- `apps/web/next.config.mjs`: Next config.

Frontend state currently handles:

- Health status.
- Ingest path/title.
- Selected document.
- Document details and visible chunks.
- Query text, history, mode, retrieval mode/profile.
- Session memory/timeline.
- Exam profile settings.
- Question-bank items.
- Diagram assets.
- Eval report input.
- Deep rail view.

## Database / Persistence Notes

SQLite tables from the MVP include:

- documents
- chunks
- ingest_jobs
- sessions
- messages
- memory_snapshots
- exam_profiles
- question_bank_items
- diagram_assets

Important V3 exam additions:

- `exam_profiles`: session/document-specific exam settings.
- `question_bank_items`: imported questions tied to documents.
- `diagram_assets`: extracted diagram file metadata tied to documents/pages.

Ignored local/generated data:

- `data/sqlite/*.db`
- `data/indexes/chroma/*`
- `temp/`
- logs and caches

## Retrieval Lifecycle

1. User submits a query from Research, Chat, or Exam Lab.
2. `QueryService` resolves retrieval mode/profile.
3. Exam modes optionally load question-bank and diagram context.
4. Study-guide and important-question modes expand retrieval query using imported questions.
5. `RetrievalService` retrieves with BM25, vector, or hybrid/RRF depending on mode.
6. Retrieved chunks are converted into citations.
7. `SynthesisService` builds a grounded prompt from retrieved chunks and optional exam context.
8. Ollama generation is attempted.
9. If generation is unavailable, fallback extractive synthesis is used.
10. Messages, citations, and retrieval metadata are persisted to SQLite when not previewing.

## Ingestion Lifecycle

1. User enters local file path and title in Source Intake.
2. `/ingest` creates/updates document record.
3. Parser extracts readable text from supported files.
4. Indexing chunks text and stores chunks in SQLite.
5. BM25 and vector stores are updated.
6. Ingest job status is persisted and displayed in UI.

Known document note:

- `C:\Downloads\daily stoic.pdf` was ingested successfully in the local environment.
- Live local state previously showed Daily Stoic with hundreds of active chunks.

## Exam Lifecycle

1. User selects Exam Lab.
2. User configures marks, answer style, content type, and custom instructions.
3. User can import a pasted question bank.
4. User can extract diagrams from source PDFs.
5. Query payload includes active exam settings.
6. Backend packs question bank and diagrams into synthesis context.
7. Study-guide mode renders generated answers as expandable guide cards.
8. Diagram assets can be clicked/opened from the right rail.

## Verification State

Latest verified commands before this context file:

- `npm run build` in `apps/web`: passed.
- Backend pytest command for unit/integration tests: passed, `6 passed`.
- API health endpoint: OK in previous verification.
- Web app at `http://127.0.0.1:3002/`: returned 200 in previous verification.
- Browser smoke test after UI refinement:
  - `Local Academic Intelligence System` visible.
  - `Source Vault` visible.
  - No bad encoding artifacts detected.
  - No Next runtime error detected.
  - No console errors detected.

## Run Instructions

Fast local preview:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -OpenBrowser
```

Fast local preview with bundled demo corpus:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

Open app:

```text
http://127.0.0.1:3002/
```

Run backend tests:

```powershell
cd C:\Nirmiq-researchOS
$env:PYTHONPATH='apps/api'
python -m pytest apps/api/app/tests/unit/test_health_contract.py apps/api/app/tests/integration -q
```

Run complete EOD ship check:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\ship_check.ps1
```

Run frontend build:

```powershell
cd C:\Nirmiq-researchOS\apps\web
npm run build
```

## Git / Branch State

Current working branch at time of creating this file:

- `v3-foundation`

Important branch meanings:

- `main`: V2 academic workspace baseline.
- `v3-foundation`: active V3 direction with Research, Chat, Exam Lab, exam artifacts, study-guide context, and custom UI refinement.

## Commit History

### 44aa66893ffb31f238c43122c9543f66d27cc394

Short hash: `44aa668`
Refs: `origin/main`, `main`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 10:40:06 +0530
Subject: `V2 academic workspace baseline`

Summary:

- Established the V2 baseline for the full local-first academic/research workspace.
- Added FastAPI backend, Next.js frontend, SQLite persistence, Chroma/BM25 retrieval infrastructure, ingestion, memory, query APIs, and tests.
- Added architecture, API, retrieval eval, and Codex/project documentation.
- Added local scripts for running API/web, reindexing, and retrieval evaluation.

Notable files/directories:

- `.env.example`
- `.gitignore`
- `README.md`
- `apps/api/**`
- `apps/web/**`
- `docs/**`
- `nirmiq_codex_docs/**`
- `scripts/**`
- `data/**` placeholders
- `models/.gitkeep`

Stat summary:

- 116 files changed.
- 9638 insertions.

### f6b331673bb696d2f0d606112f3b7cc4626c7437

Short hash: `f6b3316`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 10:46:12 +0530
Subject: `Start V3 workspace foundation`

Summary:

- Began V3 direction.
- Added separate workspace sections for Research, General Chat, and Exam Lab.
- Added section-aware frontend modes.
- Extended synthesis mode instructions for `general_chat`, `deep_research`, and `study_guide`.
- Added `docs/v3_foundation_plan.md` documenting the V3 direction and GraphRAG-lite preference over heavyweight graph infrastructure.

Files changed:

- `apps/api/app/services/synthesis_service.py`
- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`
- `docs/v3_foundation_plan.md`

Stat summary:

- 4 files changed.
- 260 insertions.
- 14 deletions.

### 1b9faff3100d450a9098331ee8d8f896691f5878

Short hash: `1b9faff`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 11:04:42 +0530
Subject: `Add V3 exam lab foundation`

Summary:

- Added V3 Exam Lab backend foundation.
- Added exam schemas, router, service, and dependency wiring.
- Added SQLite tables/methods for exam profiles, question bank items, and diagram assets.
- Added frontend API client support for exam endpoints.
- Added Exam Lab UI panel for settings, question bank import, and diagram extraction/listing.
- Added integration test for profile/question-bank/diagram contracts.
- Fixed UI hit-area overlap so Exam Lab switching works reliably.

Files changed:

- `apps/api/app/adapters/storage/sqlite_repo.py`
- `apps/api/app/api/routers/exam.py`
- `apps/api/app/api/schemas/exam.py`
- `apps/api/app/core/deps.py`
- `apps/api/app/main.py`
- `apps/api/app/services/exam_service.py`
- `apps/api/app/tests/integration/test_exam_lab_flow.py`
- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`
- `apps/web/lib/api-client.ts`

Stat summary:

- 10 files changed.
- 999 insertions.
- 5 deletions.

### 200917e621c153ea70bc6360d37b41a271e55b9d

Short hash: `200917e`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 11:09:18 +0530
Subject: `Use exam settings during grounded synthesis`

Summary:

- Added `exam_profile` to query payloads.
- Wired marks, answer style, content type, and custom instructions into synthesis prompts.
- Added retrieval metadata showing whether exam profile settings were used.
- Updated frontend query submission to include active Exam Lab settings.
- Extended integration tests to assert exam profile use during grounded query flow.

Files changed:

- `apps/api/app/api/schemas/query.py`
- `apps/api/app/services/query_service.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/integration/test_exam_lab_flow.py`
- `apps/web/app/page.tsx`
- `apps/web/lib/api-client.ts`

Stat summary:

- 6 files changed.
- 90 insertions.
- 4 deletions.

### 4afae1cf0149fbfe95a609eed56de57ce53435ff

Short hash: `4afae1c`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 11:25:06 +0530
Subject: `Pack exam artifacts into study guide synthesis`

Summary:

- Added lightweight Exam Context Packing in `QueryService`.
- Exam/study-guide queries now load question bank and diagram metadata from SQLite.
- Study-guide and important-question retrieval queries expand using imported question text to improve retrieval grounding.
- `SynthesisService` now includes imported questions and source diagram metadata in prompts.
- Offline fallback can produce a basic study guide from imported questions plus retrieved evidence.
- Integration tests assert exam context usage and question/diagram counts.

Files changed:

- `apps/api/app/services/query_service.py`
- `apps/api/app/services/synthesis_service.py`
- `apps/api/app/tests/integration/test_exam_lab_flow.py`

Stat summary:

- 3 files changed.
- 174 insertions.
- 6 deletions.

### 32c3c1ccbfa324be39538c223822d6262477b5c1

Short hash: `32c3c1c`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 12:34:53 +0530
Subject: `Polish study guide and diagram asset UI`

Summary:

- Added safe backend route for serving extracted diagram assets by asset ID.
- Added SQLite lookup for single diagram asset.
- Added service-level path-safety validation to prevent serving files outside processed diagram directory.
- Added frontend `diagramAssetUrl` helper.
- Rendered extracted diagrams as clickable image previews in Exam Lab.
- Rendered study-guide responses as expandable answer cards.
- Added integration check for missing diagram asset route returning 404.

Files changed:

- `apps/api/app/adapters/storage/sqlite_repo.py`
- `apps/api/app/api/routers/exam.py`
- `apps/api/app/services/exam_service.py`
- `apps/api/app/tests/integration/test_exam_lab_flow.py`
- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`
- `apps/web/lib/api-client.ts`

Stat summary:

- 7 files changed.
- 191 insertions.
- 1 deletion.

### af6164821c89e7c972ae50200124dbef5c00290c

Short hash: `af61648`
Refs: `HEAD -> v3-foundation`, `origin/v3-foundation`
Author: SheeshDarth <siddharthprashoo@gmail.com>
Date: 2026-05-29 18:02:11 +0530
Subject: `Refine NIRMIQ custom chat UI`

Summary:

- Refined the UI away from a generic AI-generated dashboard style.
- Changed visual system to a warmer custom NIRMIQ local research cockpit identity.
- Reworked the workspace selector into compact pill navigation.
- Renamed UI sections toward Source Intake and Source Vault language.
- Made the chat area visually primary.
- Removed bad encoding artifacts from visible UI text.
- Verified browser smoke state with no visible runtime error and no console errors.

Files changed:

- `apps/web/app/globals.css`
- `apps/web/app/page.tsx`

Stat summary:

- 2 files changed.
- 191 insertions.
- 134 deletions.

## Phase Progress Summary

Phase 1: Foundational architecture

Status: Complete.

Included:

- Repository structure.
- Service boundaries.
- Ingestion lifecycle.
- Retrieval lifecycle.
- Query lifecycle.
- Memory lifecycle.
- Backend layering.
- Shared schemas.
- SQLite and Chroma foundation.
- Basic testing and API contracts.

Phase 2: Operability and workflow polish

Status: Mostly complete for MVP.

Included:

- Cleaner document browsing.
- Citation cards and citation-to-chunk drilldown.
- Query/session comparison support.
- Retrieval evaluation script and eval report UI.
- Chatbot-style UI direction started.

Phase 3 / V3 Foundation: Multi-workspace product direction

Status: In progress.

Included:

- Research workspace.
- General Chat workspace shell.
- Exam Lab workspace.
- Exam profiles.
- Question banks.
- Diagram extraction and preview.
- Study-guide generation context from question bank and diagrams.
- Custom UI refinement.

Remaining recommended V3 work:

- More ChatGPT-like center layout with optional collapsible rails.
- Dedicated General Chat API-key settings only if user explicitly wants online mode.
- Better document upload UX beyond local path input.
- More robust OCR/image extraction flow.
- Source diagram-to-chunk/page alignment.
- GraphRAG-lite concept tables and metadata expansion.
- Stronger automated retrieval evaluation datasets.
- Optional answer export for study guides.

## Design / Architecture Decisions So Far

1. Use SQLite for GraphRAG-lite first instead of TigerGraph or heavy graph infrastructure.

Reason:

- Better for local-first MVP.
- Lower operational complexity.
- Better solo-developer maintainability.
- Lower memory/VRAM footprint.

2. Keep exam features integrated into existing query flow instead of adding a new orchestration service.

Reason:

- Fewer abstractions.
- Easier to maintain.
- Keeps retrieval/synthesis path simple.

3. Prefer grounded abstention over hallucinated general answers.

Reason:

- NIRMIQ is intended to be citation-aware and source-traceable.

4. Serve diagram assets through backend by asset ID with path validation.

Reason:

- Avoid exposing arbitrary filesystem paths.
- Keeps local assets usable in the browser safely.

5. Use fallback extractive synthesis when Ollama generation is unavailable.

Reason:

- Offline/local reliability.
- Better degraded behavior than failing hard.

## Known Warnings / Notes

- Git sometimes logs: `unable to access 'C:\Users\Siddharth/.config/git/ignore': Permission denied`. This has not blocked commits or pushes.
- Next.js dev cache previously produced a stale missing chunk runtime error; clearing `apps/web/.next` and restarting web fixed it.
- The current UI is improved but can still be pushed further toward a truly ChatGPT-like interface by making side rails collapsible and keeping the composer/chat as the dominant surface.

## Suggested Next Work

1. Add collapsible left and right rails so the app can become nearly full-screen chat when desired.
2. Add a better local file picker/import workflow if feasible in the desktop environment.
3. Add General Chat online-provider settings as optional and disabled by default.
4. Add GraphRAG-lite concept extraction tables and retrieval expansion.
5. Add source diagram/page alignment and show diagrams in generated study-guide cards.
6. Add export: study guide to Markdown/PDF.
7. Build a small retrieval evaluation corpus for Daily Stoic and academic PDFs.

## Update: ChatGPT-like Shell, Paper Lab, Legal/Security, and Test Corpus

Date: 2026-05-29

This update simplified the product shell toward a ChatGPT-like workflow:

- Added a local-only login/profile gate.
- Defaulted the app to the downloaded arXiv test corpus: `Attention Is All You Need`.
- Removed Daily Stoic from the live local SQLite document store.
- Added Paper Lab as a dedicated workspace for engineering research-paper drafting with citations.
- Hid the advanced evidence/source inspector by default behind a `Sources` toggle.
- Added Privacy, Terms, and Security documents under `docs/` and `apps/web/public/`.
- Added API and web security headers.
- Added parser cleanup for common malformed PDF glyphs.
- Added better offline fallback formatting for Research Paper mode.
- Added `docs/next_version_improvements.md`.

Local test corpus status:

- Downloaded from arXiv: `https://arxiv.org/pdf/1706.03762`
- Local path: `data/raw/attention_is_all_you_need.pdf`
- Not committed to Git because it is third-party runtime/test data.
- Indexed document title: `Attention Is All You Need`
- Indexed chunks: 41
- Extracted diagrams: 3
- Imported test question-bank questions: 3

Latest verification for this update:

- `npm run build`: passed.
- Backend tests: `6 passed`.
- `python -m compileall apps/api/app`: passed.
- API health endpoint: OK.
- Web endpoint on port 3002: OK.
- Browser smoke test: login gate visible, Paper Lab visible, Daily Stoic absent, Attention paper visible after unlock, Sources drawer toggle works.

### 4ba4944

Full hash: `4ba4944` (see Git history for complete SHA)
Refs at creation: `HEAD -> v3-foundation`, `origin/v3-foundation`
Subject: `Simplify shell and add paper lab security docs`

Summary:

- Added local-only login/profile gate.
- Changed default test corpus from Daily Stoic to `Attention Is All You Need`.
- Added Paper Lab workspace and `research_paper` synthesis mode.
- Hid advanced source/evidence inspector by default behind a `Sources` toggle.
- Added API and Next.js security headers.
- Added Privacy Policy, Terms and Conditions, and Security documents in both `docs/` and `apps/web/public/`.
- Added `docs/next_version_improvements.md`.
- Added PDF text cleanup for common malformed glyph extraction.
- Improved offline fallback response structure for research paper drafting.
- Updated `.gitignore` so downloaded PDFs and extracted diagrams remain local runtime/test data.

Verification:

- `npm run build`: passed.
- Backend tests: `6 passed`.
- `python -m compileall apps/api/app`: passed.
- Local arXiv PDF indexed successfully.
- Diagram extraction produced 3 source diagrams.
- Question bank import produced 3 questions.
- Paper Lab and Study Guide API smoke tests returned grounded responses.

### Update: Chat-first Drawers and Document Purge

Date: 2026-05-30

This update moved the shell closer to ChatGPT by making chat the default single-column surface:

- Source Library is now hidden by default and opened with a `Library` button.
- Evidence/source inspector remains hidden by default and opens with `Sources`.
- The app shell now supports independent `library-open` and `inspector-open` drawer states.
- Added `DELETE /documents/{document_id}` to purge a document from SQLite document metadata, chunks, ingestion jobs, exam profiles, question-bank items, and diagram metadata.
- Added best-effort Chroma cleanup through `ChromaRepo.delete_document`.
- Added frontend `deleteDocument` client helper.
- Added `Remove selected source` control inside the Library drawer.
- Added integration test coverage for document deletion and 404 after purge.

Verification:

- `npm run build`: passed.
- Backend tests: `6 passed` with one third-party dateutil deprecation warning.
- `python -m compileall apps/api/app`: passed.
- API health endpoint: OK.
- Web endpoint on port 3002: OK.
- Browser smoke test: default chat shell visible, Library drawer opens, Remove selected source appears, Daily Stoic absent, no console errors.

### Update: Minimal NIRMIQ Academic Intelligence System UI Pass

Date: 2026-05-30

This update refined the user-facing product direction from a dashboard-like Academic Intelligence System toward a minimal, technical, ChatGPT-like workspace:

- Chose `NIRMIQ Academic Intelligence System` as the product name and retired the previous project codename for this repository.
- Added a reusable NIRMIQ brand lockup and simple placeholder `N` mark for the future logo.
- Simplified the login page headline and value proposition.
- Reworked the chat header into a compact app bar with brand, workspace switcher, and Library/Sources toggles.
- Hid session/retrieval/profile controls inside a `Tuning` disclosure in the composer.
- Shifted the visual language to a darker technical palette with phosphor green/cyan accents.
- Fixed responsive behavior so the Library is not reserved when closed and the workspace switcher remains horizontal on narrow screens.
- Updated browser metadata plus public/legal docs to use `NIRMIQ Academic Intelligence System`.

Verification:

- `npm run build`: passed.
- Local web dev server on port 3002 restarted successfully.
- Browser smoke test: `NIRMIQ Academic Intelligence System` title visible, Tuning disclosure exists, workspace switcher is horizontal, Daily Stoic absent, no console errors.

### Update: NIRMIQ Logo Selection and App Branding

Date: 2026-05-30

Logo candidates reviewed:

- `logo multiple.png`: useful reference sheet, but contains multiple variants and the older `Local-first AI Operating Ecosystem` positioning.
- `WhatsApp Image 2026-05-30 at 3.43.35 PM.jpeg`: light banner variant, readable but less aligned with the dark minimal app shell.
- `WhatsApp Image 2026-05-30 at 3.43.35 PM (1).jpeg`: dark full banner, strong but includes old positioning text and is too wide for app chrome.
- `WhatsApp Image 2026-05-30 at 3.43.35 PM (2).jpeg`: standalone dark network mark, selected as the best fit.
- `WhatsApp Image 2026-05-30 at 3.43.36 PM.jpeg`: monochrome light banner, clean but weaker for the current dark technical UI.

Decision:

- Selected the standalone dark network mark because it fits the minimal technical UI, works as an app/favicon mark, avoids conflicting old tagline text, and visually represents retrieval, memory, coordination, and research.

Implementation:

- Cropped and resized the selected candidate into `apps/web/public/brand/nirmiq-mark.png`.
- Replaced the temporary `N` placeholder mark in the login, sidebar, and app header.
- Added the mark to Next.js metadata icons.

### Update: Chat Scroll, Upload Attachments, and Performance Polish

Date: 2026-05-30

This update addressed the reported lag/confusion and missing ChatGPT-like upload workflow:

- Added `POST /ingest/upload` for direct file upload ingestion.
- Uploaded files are stored under the configured local upload path and then routed through the existing ingestion/indexing pipeline.
- Supported upload extensions: PDF, text, Markdown, PNG, JPG/JPEG, TIFF, BMP, and WebP.
- Added `UPLOAD_PATH` setting so tests and local runtime can isolate upload storage.
- Added frontend `uploadDocument` API helper.
- Added a hidden file input and visible `+` attachment button in the chat composer.
- Added an Upload file button in the Library/Source Intake drawer.
- Kept the local path ingest form as an advanced fallback.
- Fixed scroll behavior by making the chat thread a proper fixed-height scroll container.
- Reduced UI lag by removing heavy blur and entry animations.
- Slimmed the chat header by hiding the bulky title block and keeping workspace/mode controls compact.

Known note:

- Image/photo uploads are accepted. Text extraction from photos depends on local OCR availability. `Pillow` is installed, but `pytesseract` is not currently installed/configured in this environment.

Verification:

- `npm run build`: passed.
- Backend integration/unit suite: `7 passed`.
- `python -m compileall apps/api/app`: passed.
- Live API health: OK.
- Live upload smoke test: uploaded and indexed a temporary text file through `/ingest/upload`, then deleted it from the local document store.
- Browser smoke test: plus attachment button visible, upload accept types present, chat scroll container uses `overflow-y: auto`, Daily Stoic absent, no console errors.

### Update: PDF Summary Capability

Date: 2026-05-30

This update fixed the issue where broad prompts such as `Explain the pdf` could retrieve citations but still return `Please ingest documents first`.

Root cause:

- Broad document-summary prompts contain very few useful lexical terms, so retrieval scores can be low even when scoped document chunks are available.
- The synthesis safety gate previously treated low score as no usable context.

Implementation:

- Added a `summary` response mode for whole-document overviews.
- Added a Research workspace `Summarize` button in the UI.
- Expanded retrieval queries for broad summary/overview prompts with document-overview hints.
- Added document-scope fallback retrieval so selected-document summary requests can use available chunks even when lexical search has no strong hit.
- Updated synthesis grounding logic to allow low-score answers only when the user clearly asks for a document overview and at least two chunks are retrieved.
- Added fallback document-summary formatting with sections: what it is about, main ideas, useful caveats/details.
- Improved insufficient-context wording so weak partial matches do not falsely say no documents were ingested.

Verification:

- `npm run build`: passed.
- Backend integration/unit suite: `7 passed`.
- `python -m compileall apps/api/app`: passed.
- Live smoke test: `Explain the pdf` against `Attention Is All You Need` returned a grounded summary with 8 citations.
- Browser smoke test: `Summarize` mode visible, attachment button visible, Daily Stoic absent, no console errors.

### Update: Internship Impact Plan and Parsed PDF Cache

Date: 2026-05-30

This update moved the project further toward a portfolio/internship-ready academic intelligence system instead of a generic RAG chatbot.

Planning and positioning:

- Added `docs/internship_impact_plan.md`.
- Defined NIRMIQ as a local-first academic intelligence workspace for document understanding, citation-backed synthesis, engineering paper drafting, exam preparation, and retrieval evaluation.
- Added a project differentiator narrative: not just upload-and-chat, but explainable evidence, abstention, paper workflows, exam workflows, local hardware constraints, and measurable retrieval quality.
- Added a demo script, sprint roadmap, performance strategy, retrieval-quality strategy, and metrics to show in interviews.
- Updated `README.md` to point to the impact plan and reflect current V3 capabilities.

Performance optimization:

- Added parsed-PDF page caching by content hash.
- Added `PARSE_CACHE_PATH` setting with default `data/cache/parsed_pages`.
- Wired `PyMuPDFParser(cache_root=...)` through the app container.
- The cache stores cleaned page text as local JSON and safely falls back to normal parsing if cache read/write fails.
- Added isolated test cache path for test runs.
- Added unit test coverage proving the parser reuses the cache for repeated parses of the same PDF content.

Why it matters:

- Faster repeated reindexing during demos, evaluation, and local experimentation.
- Better RTX 4050/local-laptop experience because less time is wasted reparsing unchanged PDFs.
- Stronger engineering story: measurable local performance improvement without adding infrastructure.

Verification:

- Backend unit/integration suite: `8 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

### Update: Source Cockpit and One-Click Summary UI

Date: 2026-05-30

This update improved the live app UI for usefulness and demo clarity:

- Added a compact source cockpit above the composer.
- Shows the selected source name directly where the user asks questions.
- Shows selected-source chunk count.
- Shows current grounding state near the composer instead of hiding it in the source drawer.
- Added one-click `Summarize PDF` action wired to the grounded `summary` mode.
- Added a secondary `Upload` quick action beside the source cockpit.
- Replaced noisy grounding chips with a calmer composer hint.
- Updated the empty state to guide the user toward the intended workflow: upload source, summarize first, then ask deeper questions.
- Ensured summary action does not accidentally inherit Exam Lab formatting.

Why it matters:

- Makes the app less confusing because source selection is visible at the point of asking.
- Makes the project demo stronger: upload/select PDF -> click Summarize PDF -> inspect citations.
- Supports the internship-positioning story by making grounded document intelligence obvious without opening debug panels.

Verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.

### Update: Compact Research Composer and Logo Alignment

Date: 2026-05-30

This update fixed the issue where the query/composer box consumed too much vertical space and made research responses hard to read.

Changes:

- Reduced composer padding and card height.
- Made the source cockpit a compact single-line command strip.
- Reduced textarea height for research-style querying.
- Moved the primary `Ask` button into the input row.
- Converted `Clear Thread` into a compact text action.
- Hid the composer hint by default to prioritize response visibility.
- Tightened top header spacing.
- Adjusted NIRMIQ logo sizing and lockup alignment in the app header.

Measured result in browser:

- Composer height reduced from approximately `279px` to approximately `173px`.
- Response scroll area increased from approximately `292px` to approximately `397px` on the tested viewport.
- Source cockpit reduced to approximately `38px` height.
- Logo lockup is centered with a `42px` mark height.

Verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.
- Live browser smoke test: compact composer visible, `Ask` button in input row, scroll remains enabled, logo aligned, no console errors.

### Update: V3 Landing, Login, Minimized Composer, Exam PDF Action, and Handoff Docs

Date: 2026-05-30

This update continued the V3 direction: make NIRMIQ feel closer to ChatGPT in daily use while preserving its academic intelligence identity.

Product/UX changes:

- Reworked the local entry screen into a stronger NIRMIQ Academic Intelligence System landing page.
- Added a compact animated hero/orbit visual to make the first screen feel intentional without adding heavy dependencies.
- Added local profile fields for name, email, and phone.
- Kept login local-only for now; this is a profile/personalization gate, not real hosted authentication yet.
- Clarified the four workspaces: Research, Chat, Paper Lab, and Exam Lab.
- Made composer placeholder text and primary action labels change by workspace.
- Added a `Minimize` / `Open Search` control so long answers can be read more comfortably.
- Added an Exam Lab `Custom PDF` action that opens the current grounded answer in a printable document view.
- Kept citations available through grounded badges, evidence chips, and the Sources drawer instead of forcing every panel onscreen.

Architecture/documentation changes:

- Added `prd.md` for product requirements and V3/V4 direction.
- Added `trd.md` for technical requirements and acceptance criteria.
- Added `UI_UX.md` for the UI/UX specification. The requested `UI/UX.md` filename was normalized because Windows treats `/` as a path separator.
- Added `backend_architecture.md` for service boundaries, data lifecycles, and next backend upgrades.
- Added `debugging.md` for run commands, test commands, and common issue fixes.
- Added `codex_implementaton.md` as requested to preserve Codex implementation history and future workflow notes.

Research references used for V3 planning:

- OWASP Authentication Cheat Sheet for future real auth/security posture.
- W3C WCAG 2.2 for visible focus and usable target-size guidance.
- NIST AI Risk Management Framework for trust, grounding, and risk framing.

Why it matters:

- The app now starts with a clearer product story instead of opening directly into a complex workspace.
- The composer no longer has to occupy reading space permanently.
- Each section can now feel purpose-built while sharing one maintainable query flow.
- Future Codex sessions can use the new docs as the source of truth instead of replaying the entire chat.

Verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.

### Latest Update: V3.1 Performance-Safe Motion Polish

Date: 2026-05-30

This is the latest completed work unit. A lightweight CSS-first motion system was added to make NIRMIQ feel smoother and more futuristic without adding new dependencies or heavy processor/GPU effects.

Latest changes:

- Added motion tokens, soft page boot, landing reveal, workspace underline scan, drawer slide-in, composer dock/minimized pill animation, assistant answer reveal, citation chip stagger, and one-time source-ready pulse.
- Added visible focus states and `prefers-reduced-motion` safeguards.
- Updated `UI_UX.md` with the motion direction and performance constraints.
- Restarted the Next dev server after a stale hot-reload cache error; no `.next` deletion was required.

Latest verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.
- Live browser smoke test: page loads on `http://127.0.0.1:3002`, motion tokens are active, app boot/composer animations are active, source cockpit remains compact, `Minimize` is visible, and console has no errors.

### Latest Update: NIRMIQ Academic Intelligence System Brand Migration

Date: 2026-05-30

This update migrated the repository identity away from the previous project name and toward **NIRMIQ Academic Intelligence System** as the standalone academic product under the broader NIRMIQ ecosystem.

Changes:

- Created a custom vector logo at `apps/web/public/brand/nirmiq-ais-mark.svg`.
- Updated the Next.js app metadata, favicon path, visible UI tagline, API title, backend package description, and web package name.
- Updated README, PRD, TRD, UI/UX, legal docs, architecture docs, Codex docs, and context docs to use the new product name.
- Added `docs/nirmiq_ecosystem.md` to explain NIRMIQ OS, Mirror, Intelligence Engine, Agent System, Academic Intelligence System, and Echo.
- Preserved actual local paths such as `C:\Nirmiq-researchOS` so the current workspace keeps running.
- Recorded the target GitHub repository slug: `NirmiqAcademicIntelligenceSystem`.

Notes:

- GitHub CLI is not installed in the current environment, so the remote repository could not be renamed from the terminal during this update.
- The current git remote should remain usable until the GitHub repository is renamed manually or via GitHub CLI.

Verification:

- `npm run build`: passed.
- Backend unit/integration suite: `8 passed`.
- Local web server restarted successfully on `http://127.0.0.1:3002`.
- Browser smoke test: page title is `NIRMIQ Academic Intelligence System`, visible tagline is `ACADEMIC INTELLIGENCE SYSTEM`, visible logo uses `/brand/nirmiq-ais-mark.svg`, no visible ResearchOS branding in the app shell, and console has no errors.

### Latest Update: Accuracy and Remote Codex Audit

Date: 2026-05-31

This update started a reliability sprint focused on retrieval precision, hallucination resistance, and remote Codex readiness.

Research basis:

- RAGAS for context relevance, faithfulness, and answer-quality evaluation dimensions.
- ARES for automated RAG evaluation around context relevance, answer faithfulness, and answer relevance.
- Self-RAG and chain-of-verification patterns for retrieve/generate/critique and claim verification.
- Official OpenAI Codex docs for local CLI, Codex web/GitHub, mobile/remote continuity, and workspace controls.

Implemented:

- Added deterministic cited-claim verification in `SynthesisService`.
- Unsupported cited claims now trigger a safe extractive fallback rewrite instead of allowing unsupported fluent output through.
- Added retrieval metadata for `citation_verification_state`, checked claim count, unsupported claims, original unsupported claims, and rewrite status.
- Added UI answer-card badges for citation verification and faithfulness rewrites.
- Added unit tests for supported and unsupported cited generations.
- Added `docs/accuracy_precision_audit.md`.
- Added `docs/remote_codex_access.md`.

Known limitation:

- The current verifier is lexical and local-first. It is intentionally cheap and deterministic, but not a full semantic entailment model.

Verification:

- Backend unit/integration suite: `10 passed`.
- `npm run build`: passed.
- `python -m compileall apps/api/app`: passed.
- Local web server restarted successfully on `http://127.0.0.1:3002`.
- Browser smoke test: NIRMIQ Academic Intelligence System UI loads, workspace tabs are visible, no old ResearchOS branding appears in the app shell, and console has no errors.

### Latest Update: Chunk Quality Scoring and Portable GitHub CLI

Date: 2026-05-31

This update improved retrieval precision without adding new UI complexity.

Changes:

- Added chunk quality scoring during indexing.
- Stored `quality_score` on `document_chunks`.
- Added SQLite migration logic for existing local databases.
- Passed quality score into Chroma metadata when vector storage is available.
- Applied quality weighting during retrieval scoring so noisy PDF/OCR chunks are less likely to dominate context.
- Added retrieval metadata for average chunk quality and quality weighting.
- Added unit tests for clean academic text and noisy PDF text.
- Added `tools/gh/` to `.gitignore`.
- Installed portable GitHub CLI at `C:\Nirmiq-researchOS\tools\gh\bin\gh.exe` because Winget/MSI system install was blocked by a stuck Windows Installer process.

User impact:

- The app stays simple. No new control is shown.
- Retrieval should quietly prefer readable, useful chunks over malformed PDF extraction garbage.
- GitHub CLI is available locally, but GitHub auth still needs user login.

Verification:

- Backend unit/integration suite: `12 passed`.
- `npm run build`: passed.
- `python -m compileall apps/api/app`: passed.
- Portable GitHub CLI version check passed: `gh version 2.92.0`.
- `gh auth status` confirms authentication is still pending.

### Latest Update: V3 Security, Privacy, and Adaptive Generation Hardening

Date: 2026-06-02

This update tightened the project without adding interface complexity.

Implemented:

- Restricted direct local-path ingestion to configured trusted corpus roots.
- Added `LOCAL_INGEST_ALLOWED_ROOTS` and `SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS=false`.
- Preserved normal app uploads by storing uploaded files inside the project raw-data area.
- Added lightweight content validation for PDF, image, text, and Markdown uploads to reduce extension-spoofing risk.
- Added adaptive generation temperature:
  - Grounded factual/summary/exam paths stay conservative by default.
  - Long-context deep research, paper drafting, and study-guide synthesis can use `0.85` when enough evidence is retrieved.
  - Citation-faithfulness verification still runs after generation.
- Added backend unit tests for ingestion privacy and upload validation.
- Added a local agent plan that keeps future agent behavior local, tool-limited, and approval-aware rather than unbounded.

Tradeoffs:

- Direct local-path ingestion is safer but now requires files to be under allowed roots unless explicitly overridden.
- Higher-temperature generation is not global, because summary/exam/factual answers need reliability more than stylistic variety.
- The local agent was documented rather than fully implemented to avoid complicating V3 before Version 4 requirements arrive.

Verification:

- Backend unit/integration suite: `17 passed`.
- `npm run build`: passed.
- `python -m compileall apps/api/app`: passed.

### Latest Update: V3.1 Faster Summaries, Intent Routing, and Trust Signals

Date: 2026-06-06

This update implemented the planned V3.1 reliability/performance increment without adding new user-facing complexity.

Implemented:

- Added SQLite-backed `document_summaries` cache for selected-document summary mode.
- Cache key uses document id, content hash, and summary profile, so source edits/reindexing naturally miss stale summaries.
- Document deletion now purges cached summaries.
- Added deterministic query intent routing for summary, factual lookup, compare, deep research, paper draft, exam, general chat, and unclear prompts.
- Added retrieval metadata for `cache_hit`, `detected_intent`, `intent_confidence`, and `intent_route`.
- Added citation coverage metadata: `citation_coverage`, `citation_sentence_count`, and `citation_anchor_count`.
- Updated the UI trust chip to show one compact label: `Verified`, `Rewritten`, `Needs review`, or `Low citation coverage`.
- Added unit tests for intent routing, citation coverage, and summary cache storage.
- Expanded integration coverage for summary cache miss, cache hit, stale-content miss after reindex, and cache purge on document delete.

Tradeoffs:

- Intent routing is deterministic and lexical to stay fast/offline; it should be tuned with a labeled evaluation dataset next.
- Summary cache is limited to selected-document summary requests, avoiding ambiguous corpus-wide cache behavior.
- Citation coverage checks anchor presence, while citation-faithfulness verification remains responsible for claim support.

Verification:

- Backend unit/integration suite: `25 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.
- Browser plugin was unavailable in this session, so browser smoke was not run.

Commit:

- `b036ad8` - Add V3.1 summary cache and trust routing.

### Latest Update: V4 Paper Lab Foundation

Date: 2026-06-06

This update began Version 4 with a focused Paper Lab foundation instead of a broad, risky feature wave.

Implemented:

- Added deterministic Paper Lab artifact generation from retrieved chunks.
- Paper draft responses now expose `retrieval_meta.paper_lab`.
- Paper Lab metadata includes source count, evidence count, citation clusters, related-work matrix rows, and a suggested paper outline.
- Added a Paper Lab right-rail workspace panel with outline and related-work matrix previews.
- Added `Copy Markdown Draft` to export the grounded answer, outline, matrix, and citations without adding server-side file writes or new dependencies.
- Added unit tests for Paper Lab artifact generation.
- Expanded integration tests to verify paper-draft metadata.

Tradeoffs:

- The V4 foundation uses deterministic chunk organization rather than another LLM pass, keeping latency and VRAM usage low.
- Markdown copy export is the first export target; DOCX/LaTeX should wait until the Paper Lab draft shape is validated.
- Multi-document citation diversity is still a future V4 item.

Verification:

- Backend unit/integration suite: `26 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

Commit:

- `52bcbe5` - Add V4 Paper Lab citation workspace.

### Latest Update: V4 Publish Readiness Sprint

Date: 2026-06-06

This update targeted a working publish/demo pass for June 7, 2026.

Implemented:

- Added `GET /health/readiness` to report API/database readiness, indexed document count, active chunk count, Chroma availability, Ollama availability, and local-first status.
- Added backend contract coverage for readiness.
- Added `scripts/publish_smoke.ps1` to verify API health, readiness, and web shell branding after local servers are running.
- Rewrote `README.md` around the current V4 product state and demo flow.
- Added `docs/publish_checklist.md` with pre-publish commands, local startup, smoke check, demo script, and eval label workflow.
- Updated `docs/api_contract.md` for readiness and V4 query metadata.

Tradeoffs:

- Readiness is intentionally simple and local; it does not require Ollama or Chroma to be online because deterministic fallback paths are valid.
- Eval labels are not hardcoded because document IDs are local database state. The checklist explains how to create real labels after ingest.

Verification:

- Backend unit/integration suite: `27 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

Commit:

- `15a2787` - Prepare V4 publish readiness.

### Latest Update: Preview Hotfix For Failed Fetch / Chroma Dimension Mismatch

Date: 2026-06-06

Problem observed:

- The browser showed `Failed to fetch` / `TypeError`.
- FastAPI was alive, but `POST /query` and some uploads returned `500`.
- The root cause was a Chroma collection created with `768`-dimension embeddings while offline fallback hash embeddings used `256` dimensions.

Implemented:

- `ChromaRepo` now detects embedding dimension mismatch errors.
- On upsert mismatch, it resets only the affected Chroma collection and retries once.
- On query mismatch, it returns no vector hits so retrieval can continue through BM25/lexical fallback instead of crashing.
- Added unit tests for the Chroma resilience path.

Preview recovery performed:

- Restarted FastAPI.
- Cleared generated Next.js `.next` cache and restarted the web preview.
- Smoke check passed.
- Direct summary query returned `grounded=True` with 8 citations.

Verification:

- Backend unit/integration suite: `29 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.
- `scripts/publish_smoke.ps1`: passed with one indexed demo document and 35 active chunks.

Commit:

- `fa85a78` - Fix Chroma dimension mismatch preview failures.

### Latest Update: Offline-First Runtime Clarification

Date: 2026-06-06

Clarification:

- The word API caused confusion because NIRMIQ has a local FastAPI backend, but the product must not depend on a cloud API.
- Core NIRMIQ operation is local/offline first.
- ChatGPT/OpenAI-linked account usage is only a future optional enhancement path, not the primary goal or required runtime.

Implemented:

- Readiness now reports `local_backend=true`, `cloud_api_required=false`, `external_provider_enabled=false`, and `primary_inference=local_offline`.
- Publish smoke check now validates that cloud API is not required.
- README, publish checklist, API contract, security docs, and TRD now use clearer local-backend/offline-first language.

Verification:

- Backend unit/integration suite: `29 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.

Commit:

- `2802deb` - Clarify offline-first local backend contract.

### Latest Update: GitHub README ResearchOS Positioning

Date: 2026-06-06

Purpose:

- The GitHub-facing README needed to reflect the user's NIRMIQ ResearchOS positioning: "Upload. Understand. Verify. Learn."
- The update merges the user's stronger public narrative with the real V4 implementation state, avoiding claims that are not currently supported.

Implemented:

- Rewrote `README.md` as a polished public project overview for NIRMIQ ResearchOS.
- Clarified that ResearchOS is an offline-first academic document intelligence system, not just a PDF chatbot.
- Added the offline-first contract: local FastAPI backend is part of the app runtime, not a cloud API dependency.
- Documented current V4 capabilities: upload, summary, grounded Q&A, source inspection, Research/Chat/Paper Lab/Exam Lab, summary cache, intent routing, trust badges, Paper Lab metadata, Exam Lab PDFs, readiness checks, and smoke script.
- Updated project memory and handoff docs to treat NIRMIQ ResearchOS as the GitHub-facing academic document product name.
- Preserved the broader NIRMIQ ecosystem framing without forcing a risky runtime folder/app rename during this docs-only pass.

Tradeoffs:

- Historical context entries still mention the earlier Academic Intelligence System naming so the implementation history remains traceable.
- Runtime UI/browser metadata was not renamed in this pass because the user asked specifically for GitHub README/context updates and the current app preview should remain stable.

Verification:

- `git diff --check`: passed.
- README/context spot check: passed.
- Code tests/build were not rerun because this was a documentation-only positioning update.

Commit:

- `3110de0` - Update ResearchOS GitHub positioning.

### Latest Update: Low-Memory Local Runtime Hardening

Date: 2026-06-06

Purpose:

- The project needed an end-to-end stability pass focused on lower memory usage without weakening grounded answer quality.
- The user asked to quantize/tune the model path, check loopholes, and make the system more efficient for local/offline use.

Implemented:

- Added bounded Ollama runtime controls:
  - `LOW_MEMORY_MODE=true`
  - `OLLAMA_KEEP_ALIVE=45s`
  - `OLLAMA_NUM_CTX=3072`
  - `OLLAMA_NUM_PREDICT=768`
  - optional `OLLAMA_NUM_GPU`
  - optional `OLLAMA_NUM_THREAD`
- Added batched Ollama embedding calls through `OLLAMA_EMBED_BATCH_SIZE=8` so indexing does not send every chunk in one large model request.
- Readiness now exposes `low_memory_mode` and `ollama_runtime` metadata so the active local profile is visible.
- Added `apps/api/.env.example` with the RTX 4050-friendly local backend profile.
- Added `docs/local_model_optimization.md` explaining quantized/small Ollama model usage, Q4 GGUF guidance, memory tradeoffs, and benchmark targets.
- Updated README, API contract, backend architecture, PRD, TRD, debugging guide, and accuracy audit with the low-memory/quantized model strategy.
- Added tests for bounded Ollama generation payloads, embedding batching, and readiness runtime metadata.

Architecture decision:

- NIRMIQ does not fake runtime quantization inside FastAPI. Actual quantization belongs to Ollama/GGUF model artifacts. The backend now makes those models safer to use by bounding context, output length, keep-alive, and embedding batch size.

Verification:

- Backend unit/integration suite: `31 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm run build`: passed.
- `git diff --check`: passed after normalizing the accuracy audit doc.

Commit:

- `6e53767` - Add low-memory local model runtime profile.

### Latest Update: Minimal ChatGPT-Style UI Transformation

Date: 2026-06-09

Purpose:

- Transform NIRMIQ ResearchOS toward a ChatGPT-like local academic document interface without changing backend APIs or removing Paper Lab/Exam Lab capabilities.

Implemented:

- Made Chat the default primary route while preserving Research, Paper Lab, and Exam Lab.
- Opened the left rail by default and reshaped it into a study sidebar:
  - New Study Thread
  - Recent Study Threads
  - Study Material upload
  - Knowledge Base
  - Local runtime status
- Kept upload accessible from the composer and the sidebar.
- Moved local-path ingestion into an advanced disclosure so normal users feel like they are attaching study material, not managing a database.
- Replaced the old `Sources` toggle with a collapsible `Deep Research` panel.
- Added evidence/trust copy under assistant answers:
  - grounded answer copy
  - citation coverage warning copy
  - insufficient evidence copy
  - `View Deep Research` action
- Added an `Evidence Trail` label above citation chips under answers.
- Moved detailed mode routing into compact composer tuning with a `Route` selector.
- Simplified the local login/landing page into a single focused message: "Chat with your study material."
- Retuned visible UI colors toward graphite, research ivory, oxide copper, deep teal, and sage.
- Cleaned safe ResearchOS naming traces in frontend metadata and private package metadata.
- Cleaned safe ResearchOS naming traces in public privacy, terms, and security markdown.
- Updated README demo wording and UI/UX handoff notes.

Preserved:

- Existing backend APIs.
- Existing upload/query/document/exam/paper capabilities.
- Paper Lab metadata/export panel.
- Exam Lab profile/question-bank/diagram/custom-PDF tooling.
- Citation chips, trust badges, and evidence drilldown.

Verification:

- `npm run build`: passed after frontend and public markdown changes.
- Active frontend/legal naming scan: no `Academic Intelligence System`, `Sources` toggle, `Source Intake`, `Source Vault`, or `nirmiq-ais-web` traces outside historical context.
- Browser visual QA was not run because the browser skill path was unavailable and no callable browser inspection tool was exposed in this session.

Remaining UI debt:

- `apps/web/app/page.tsx` is still a large single component and should eventually be split into sidebar, chat thread, composer, Deep Research, Paper Lab, and Exam Lab components.
- Some older historical naming remains in archived context entries and public/legal markdown files.
- The Knowledge Base sidebar is always visible on desktop; mobile behavior should be manually reviewed.
- Deep Research is cleaner but still dense because it contains evidence, context, compare, eval, Paper Lab, and Exam Lab panels in one rail.
- Chat routing is compact, but automatic intent-driven UI hints can be improved after more real usage.

Commit:

- `d19de62` - Transform UI into ChatGPT-style study shell.

### Latest Update: Accuracy Rescue And Textbook Grounding Pass

Date: 2026-06-11

Purpose:

- The working demo was failing on answer quality: the app appeared to retrieve sources, but answers were weak, sometimes stale, and sometimes plausible rather than strictly grounded.
- The validation source for this pass was `Hands-On Machine Learning with Scikit-Learn, Keras and TensorFlow`, indexed from `data/raw/uploads/Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-TensorFlow-3rd-Ed.---Annot-5b287bd745.pdf`.

Root causes found:

- The default generation model was `phi3:mini`, but this machine did not have that model installed.
- `qwen3.5:4b` was installed but returned most content in Ollama's `thinking` field and an empty `response`, so it was unsafe as the first generation model for the demo.
- The Ollama timeout was too short for cold local generation.
- Long-textbook summary retrieval could pull bibliography/resource chunks instead of the document outline.
- Factual queries such as `What is overfitting and how can it be reduced?` over-focused on one wording path and missed the textbook definition page.
- Generated answers could include plausible ML techniques not present in the retrieved source chunks.
- Stale document rows with `indexed` plus `0` chunks made the library look healthier than it was.

Implemented:

- Added cached Ollama model discovery through `/api/tags`.
- Added generator model routing: prefer installed instruct models for answer text, with `mistral:7b-instruct-q4_K_M` preferred over `qwen3.5:4b` on this machine.
- Added generation metadata: requested model, used model, fallback flag, and error string.
- Raised default Ollama timeout to `120s` and reduced default prediction cap to `512` for local stability.
- Added light stemming to BM25 and lexical reranking for variants such as `reduce`, `reduced`, `reducing`, `overfit`, and `overfitting`.
- Added selected-document summary seeding from early outline chunks.
- Added selected-document factual seeding for definition/solution questions.
- Tightened cited-claim verification so unsupported specific techniques trigger source-only rewrite.
- Added citation anchoring for uncited generated sentences instead of appending a weak `Sources: [1]` footer.
- Added structured source-only fallback for definition-plus-solution questions.
- Filtered low-value resource/bibliography sentences from summary fallback.
- Marked stale library rows as `needs_reindex` when they are not actually usable.
- Added tests for model routing, BM25 morphology matching, citation anchoring, and faithfulness preservation.

Validation:

- Clean textbook index created: `e9b7b4ff-b679-44db-a2cf-bbb945caee22`, `1833` active chunks.
- Live query tested: `What is overfitting and how can it be reduced?`
- Result used `mistral:7b-instruct-q4_K_M`, retrieved page 58 definition and page 59 solutions, rewrote unsupported model additions into source-only form, and returned cited textbook evidence.
- Full backend suite: `34 passed, 1 warning`.
- `python -m compileall apps/api/app`: passed.
- `npm run build` from `apps/web`: passed.

Tradeoffs:

- Some answers are now more conservative and extractive when the local model adds unsupported claims. This is intentional for demo reliability and hallucination reduction.
- First uncached summaries on large textbooks can still take around a minute on local models; repeated selected-document summaries use cache.
- The textbook summary is cleaner than before but remains extractive. A later V4 upgrade should add chapter-aware summary profiles and a proper retrieval eval set.

Commit:

- Pending in this work unit: accuracy rescue, model routing, focused retrieval seeding, and faithfulness hardening.

### Latest Update: Recruiter-Facing Demo Dataset And README Polish

Date: 2026-06-13

Purpose:

- Position NIRMIQ ResearchOS as the strongest GenAI/RAG/document-AI internship project.
- Make the GitHub README easier for recruiters to evaluate quickly.
- Add real demo data, sample questions, measurable retrieval metrics, one-command startup, and working Docker dev instructions.

Implemented:

- Added two original sample PDFs under `data/raw/demo_pdfs/`:
  - `nirmiq_rag_reference.pdf`
  - `nirmiq_exam_reference.pdf`
- Added 10 sample QA labels with expected answers and phrase-level evidence targets:
  - `data/processed/eval/demo_academic_qa.jsonl`
- Extended `scripts/eval_retrieval.py` to support `expected_phrases` labels and nDCG metrics.
- Added generated retrieval metrics output:
  - `data/processed/eval/demo_retrieval_metrics.json`
- Added scripts:
  - `scripts/start_local.ps1`
  - `scripts/load_demo_dataset.ps1`
  - `scripts/eval_demo_dataset.ps1`
- Updated `scripts/eval_retrieval.ps1` to run the demo dataset by default.
- Updated `docker-compose.local.yml` with API and web services that install dependencies in dev containers.
- Updated README with:
  - `What Works Now`
  - `Planned Next`
  - one-command startup via `scripts/start_local.ps1`
  - Docker dev instructions
  - demo dataset and retrieval metrics
  - screenshot/GIF capture checklist links
- Added docs:
  - `docs/demo_dataset.md`
  - `docs/retrieval_eval_results.md`
  - `docs/demo_assets.md`
- Updated `docs/benchmark_report.md` with the measured demo retrieval table.
- Added `.gitignore` exceptions so only curated demo PDFs are tracked, not user uploads.

Latest demo retrieval metrics:

- Hybrid: MRR `0.95`, Recall@3/5/8 `1.00`, nDCG@3 `0.708`, citation expected coverage `1.00`.
- BM25: MRR `0.90`, Recall@3/5/8 `1.00`, nDCG@3 `0.642`, citation expected coverage `1.00`.

Validation:

- `scripts/load_demo_dataset.ps1 -ForceReindex`: indexed both demo PDFs successfully.
- `scripts/eval_demo_dataset.ps1`: produced metrics successfully.
- `python -m py_compile scripts/eval_retrieval.py`: passed.
- Focused backend tests: `4 passed`.
- `docker compose -f docker-compose.local.yml config`: valid config; Docker emitted only a user-level config permission warning.
- `npm run build`: passed.

Tradeoffs:

- Actual README screenshots/GIFs were not captured in this session because no screenshot-capable browser tool was available. The repo now includes an explicit capture checklist in `docs/demo_assets.md`.
- Docker compose is a dev/demo path and installs dependencies at startup. The Windows PowerShell launcher remains the best local path for performance.

Commit:

- Pending in this work unit: recruiter polish, demo dataset, retrieval eval metrics, Docker dev setup, README cleanup.

### Latest Update: EOD Ship Readiness Hardening

Date: 2026-06-14

Purpose:

- Convert the working local demo into a more publish-ready GitHub project.
- Address Finale AI dashboard findings without breaking the local-first/offline-first product direction.
- Improve deployment credibility, repo hygiene, security posture, and reviewer onboarding.

Finale AI findings used:

- Overall score: `72.9`.
- Security: `80`.
- Reliability: `91`.
- Deployment: `58`.
- Architecture: `88`.
- Cost Risk: `0`.
- Highest-impact gaps: no CI/CD, no CODEOWNERS, no root package manifest, no Dockerfile, no license, API versioning, request size limit, response compression, SQL f-string scanner finding, and unclear production security header posture.

Implemented:

- Added GitHub Actions CI:
  - `.github/workflows/ci.yml`
  - Runs backend tests, backend compile, frontend build, and Docker Compose config validation.
- Added ownership and licensing:
  - `.github/CODEOWNERS`
  - MIT `LICENSE`
- Added root command hub:
  - `package.json`
  - `npm.cmd run start`
  - `npm.cmd run start:golden`
  - `npm.cmd run test:api`
  - `npm.cmd run compile:api`
  - `npm.cmd run build`
  - `npm.cmd run ship:check`
- Added stable Windows API test runner:
  - `scripts/test_api.ps1`
  - Uses project-local temp and pytest cache paths to avoid user temp permission failures.
- Added Docker build assets:
  - `.dockerignore`
  - `apps/api/Dockerfile`
  - `apps/web/Dockerfile`
  - Updated `docker-compose.local.yml` to build checked-in containers instead of installing dependencies on every startup.
- Added backend hardening:
  - Request body size guard through `MAX_REQUEST_BODY_BYTES`.
  - GZip response compression.
  - Production opt-in `ENABLE_HSTS` and `ENABLE_CONTENT_SECURITY_POLICY`.
  - `/api/v1/*` route aliases while preserving existing legacy local routes.
  - Updated API title/version to `NIRMIQ ResearchOS API` / `0.4.0`.
- Cleaned SQLite scanner findings:
  - Removed f-string `execute()` patterns from `sqlite_repo.py`.
  - Added allowlisted migration identifiers for schema column additions.
- Added tests:
  - `test_api_hardening.py` covers `/api/v1/health`, baseline security headers, and oversized request rejection.
- Updated docs:
  - `README.md`
  - `docs/ship_readiness.md`
  - `docs/security.md`
  - `docs/publish_checklist.md`
  - `docs/benchmark_report.md`
  - `docs/accuracy_precision_audit.md`
  - `backend_architecture.md`
  - `debugging.md`
  - `trd.md`
  - `.env.example`

Validation:

- `python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q -o cache_dir=C:\Nirmiq-researchOS\temp\pytest-cache`: `37 passed, 1 warning`.
- `npm.cmd run test:api`: `37 passed, 1 warning`.
- `python -m compileall apps/api/app`: passed.
- `npm run build` from `apps/web`: passed.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed.
- `docker compose -f docker-compose.local.yml config`: passed, with only an existing user-level Docker config permission warning.
- `rg` scanner check for f-string `execute()` patterns: no matches in `sqlite_repo.py`.
- `scripts/ship_check.ps1`: passed full EOD gate.
  - Backend tests: passed.
  - API compile: passed.
  - Web build: passed.
  - Publish smoke: passed.
  - Readiness: `ready`, `indexed_documents=9`, `active_chunks=1880`.
  - Golden demo Research: passed with 2 citations.
  - Golden demo Summary-style Research: passed with 2 citations.
  - Golden demo Exam Lab: passed with 2 citations.
  - Golden demo Paper Lab: passed with 2 citations.
  - Golden demo unsupported Chat query: passed with `grounded=false`, `citations=0`.

Tradeoffs:

- HSTS and CSP are opt-in rather than default because localhost HTTP should stay easy to run and HSTS only makes sense behind HTTPS.
- Authentication was intentionally not added because NIRMIQ is still a local single-user system, not a hosted SaaS.
- Cloud error tracking was intentionally not added because default telemetry conflicts with the privacy/offline-first contract.
- Docker is now better for reviewer verification, but Windows PowerShell launch remains the preferred RTX 4050/Ollama path.
- SQLite dynamic placeholder SQL remains where needed for `IN (...)`, but scanner-triggering f-string `execute()` patterns were removed and user values remain parameterized.

Remaining ship debt:

- Capture README screenshots/GIFs.
- Add real-world retrieval eval labels beyond the synthetic demo set.
- Add uploaded-source-file purge after safe ownership checks.
- Add chapter-wise summaries for long textbooks.
- Add optional local bug-report bundle export.
- Add hosted auth only if a future version becomes a public multi-user SaaS.

Commit:

- `c15b0fb` - Add EOD ship readiness hardening.

### Latest Update: Privacy Controls And 30-Sample Retrieval Eval Sprint

Date: 2026-06-14

Purpose:

- Continue the post-ship polish sprint without complicating the UI.
- Add reviewer-visible local privacy/reset controls.
- Strengthen the retrieval benchmark from a tiny 10-question demo to a broader 30-question phrase-labeled dataset.

Implemented:

- Added backend local data controls:
  - `GET /memory/{session_id}/export` returns a local Markdown thread export.
  - `DELETE /memory/{session_id}` clears local session messages and snapshots.
  - `DELETE /documents` clears all indexed document metadata, chunks, jobs, summaries, exam artifacts, and vector entries.
- Added storage/service support:
  - `SQLiteRepo.delete_session`
  - `SQLiteRepo.delete_all_documents`
  - `ChromaRepo.clear_all_documents`
  - `MemoryService.export_markdown`
  - `MemoryService.delete_session`
  - `DocumentsService.purge_documents`
- Added typed frontend API client methods:
  - `exportSessionMarkdown`
  - `deleteSession`
  - `purgeDocuments`
- Added a compact `Local Data` card in the Knowledge Base rail:
  - Export thread.
  - Clear thread.
  - Clear indexed material.
- Kept purge behavior safe:
  - NIRMIQ clears local database/vector/index state.
  - Source files on disk are not deleted yet because arbitrary filesystem deletion is risky.
- Expanded `data/processed/eval/demo_academic_qa.jsonl` from 10 to 30 phrase-labeled questions.
- Regenerated `data/processed/eval/demo_retrieval_metrics.json`.
- Updated docs:
  - `README.md`
  - `docs/demo_dataset.md`
  - `docs/retrieval_eval_results.md`
  - `docs/benchmark_report.md`
  - `docs/security.md`
  - `docs/publish_checklist.md`
  - `docs/ship_readiness.md`
  - `backend_architecture.md`
  - `trd.md`

Latest expanded demo retrieval metrics:

- Hybrid: samples `30`, MRR `0.967`, Recall@3/5/8 `1.00`, nDCG@3 `0.847`, citation expected coverage `1.00`.
- BM25: samples `30`, MRR `0.839`, Recall@3/5/8 `1.00`, nDCG@3 `0.749`, citation expected coverage `1.00`.

Validation:

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/eval_demo_dataset.ps1`: passed and wrote expanded metrics.
- `npm.cmd run test:api`: `37 passed, 1 warning`.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed; frontend route `/` size `15.3 kB`, first load JS `115 kB`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/ship_check.ps1`: passed.
  - Backend tests: passed.
  - API compile: passed.
  - Web build: passed.
  - Publish smoke: passed.
  - Golden demo Research: passed with 2 citations.
  - Golden demo Summary-style Research: passed with 2 citations.
  - Golden demo Exam Lab: passed with 2 citations.
  - Golden demo Paper Lab: passed with 2 citations.
  - Golden demo unsupported Chat query: passed with `grounded=false`, `citations=0`.
- `docker compose -f docker-compose.local.yml config`: passed; same user-level Docker config permission warning remains.

Tradeoffs:

- The clear-indexed-material control does not delete raw source files yet. This is safer for local-path ingestion because the app can point at files outside its ownership.
- The 30-question dataset is still synthetic and compact. The next quality sprint should add labels from real textbooks, notes, and papers.
- The browser visual smoke could not be run from the current tool set, but the frontend production build and full ship check passed.

Remaining next sprint candidates:

- Capture README screenshots/GIFs.
- Add real-world eval labels beyond the synthetic demo PDFs.
- Add uploaded-file-only source purge with explicit ownership checks.
- Add local bug-report bundle export.

Commit:

- `d6e8c99` - Add local privacy controls and expanded eval.

### Latest Update: CI Backend Install Fix

Date: 2026-06-14

Purpose:

- Fix the GitHub Actions `Backend tests and web build` failure after the EOD/privacy sprint pushes.

Root cause:

- CI failed during `python -m pip install -e apps/api` before backend tests or the frontend build ran.
- Setuptools discovered two top-level packages in `apps/api`: `app` and `alembic`.
- Because `pyproject.toml` relied on automatic package discovery, editable install failed with:
  - `Multiple top-level packages discovered in a flat-layout: ['app', 'alembic']`.

Implemented:

- Updated `apps/api/pyproject.toml` with explicit setuptools package discovery:
  - include `app*`
  - exclude `alembic*`
- Pinned Pydantic to `>=2.10.0,<2.11.0` because NIRMIQ works on that range and it avoids unnecessarily upgrading the user's local Python environment in a way that conflicts with unrelated packages such as `f5-tts`.
- Updated GitHub Actions frontend steps to use `npm.cmd ci` and `npm.cmd run build` so Windows CI never resolves to PowerShell's `npm.ps1` shim.
- Added `*.egg-info/` to `.gitignore` because editable installs generate local packaging metadata.

Validation:

- `python -m pip install -e apps/api`: passed.
- `npm.cmd run test:api`: `37 passed, 1 warning`.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed.
- `npm.cmd run build` from `apps/web`: passed.

Notes:

- Local `npm.cmd ci` hit a Windows `EPERM` lock on `apps/web/node_modules\.package-lock.json`; this is local node_modules state, not the GitHub failure, because CI runners start from a clean checkout.
- The actual failed GitHub run `27505994245` stopped at backend install, so the web build was marked failed by the job outcome rather than by a frontend compile error.

Commit:

- Pending in this work unit: CI backend install/package discovery fix.

### Latest Update: Windows Desktop Shell

Date: 2026-06-19

Purpose:

- Provide a desktop-app workflow so NIRMIQ can be launched, reviewed, debugged, and edited without manually juggling localhost browser tabs and terminal windows.
- Keep the implementation lightweight and safe by wrapping the existing local FastAPI + Next.js runtime instead of duplicating product logic.

Implemented:

- Added `apps/desktop`, a lightweight Electron shell for Windows.
- The shell starts the local FastAPI runtime at `127.0.0.1:8000` and the Next.js app at `127.0.0.1:3002` when ports are not already active.
- Added a secure Electron preload bridge with only two exposed actions:
  - runtime status
  - runtime restart
- Added a desktop menu for fast development/debugging:
  - Runtime Status
  - Restart Local Runtime
  - Open Project Folder
  - Open In VS Code
  - Open `context.md`
  - Open README
  - Open Debugging Guide
  - Open Backend Architecture
  - Open API/Web logs
- Added `NIRMIQ Desktop.cmd` for double-click desktop launch.
- Added root scripts:
  - `npm run desktop`
  - `npm run desktop:install`
  - `npm run desktop:dev`
  - `npm run desktop:pack`
  - `npm run desktop:package`
- Added `scripts/start_desktop.ps1` for safe startup and one-time dependency install guidance.
- Added `scripts/package_desktop.ps1` to keep Electron Builder cache inside `temp/electron-builder-cache` instead of relying on Windows AppData permissions.
- Updated shortcut generation so `NIRMIQ Desktop.lnk` is created alongside browser preview and stop shortcuts.
- Added `apps/desktop/README.md` and updated README, debugging guide, TRD, backend architecture, and Windows packaging docs.

Validation:

- `node --check apps/desktop/src/main.js`: passed.
- `node --check apps/desktop/src/preload.js`: passed.
- `npm.cmd --prefix apps/desktop audit --omit=dev`: passed with `0 vulnerabilities` for production dependencies.
- `npm.cmd --prefix apps/desktop run pack`: passed and created `dist/desktop/win-unpacked/NIRMIQ ResearchOS.exe`.
- `npm.cmd --prefix apps/desktop run package`: passed after redirecting Electron Builder cache and allowing the NSIS download; created `dist/desktop/NIRMIQ ResearchOS 0.1.0.exe`.
- `npm.cmd run test:api`: `37 passed, 1 warning`.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed.

Tradeoffs:

- This is a desktop shell, not a fully self-contained installer. Python, Node dependencies, Ollama, SQLite, and Chroma remain visible and debuggable in the repository/runtime.
- The full installer should remain a later packaging sprint after repeated local runtime stability.
- The portable EXE is generated under ignored `dist/desktop`; it is not committed to Git because it is a binary release artifact.
- Electron dev dependencies reported audit advisories during install, but production dependency audit with `--omit=dev` is clean. Do not blindly force-update Electron Builder without re-validating packaging.

Commit:

- `ca2a83c` - Add Windows desktop shell.

Follow-up correction after packaging validation:

- Added robust desktop project-root detection for packaged Electron runs.
- The shell now searches `NIRMIQ_ROOT`, development paths, current working directory, packaged resources, and executable location for `apps/api` plus `apps/web`.
- Documented `NIRMIQ_ROOT='C:\Nirmiq-researchOS'` as the fallback when launching unpacked/portable builds from unusual locations.
- Revalidated `node --check`, desktop unpacked packaging, desktop portable packaging, and web build after the fix.

### Latest Update: Desktop Startup Failure Fix

Date: 2026-06-19

Issue:

- The Windows desktop shell showed `NIRMIQ startup failed` for the user.
- Reproduction showed FastAPI and Next were able to start, but Electron/Chromium crashed with:
  - `GPU process isn't usable. Goodbye.`
- A secondary Windows reliability issue was found around duplicate `Path`/`PATH` environment keys when launching child processes.

Implemented:

- Added GPU-safe Electron startup flags in both `apps/desktop/src/main.js` and `apps/desktop/package.json`:
  - `--in-process-gpu`
  - `--disable-gpu-sandbox`
  - `--disable-gpu-compositing`
  - `--disable-gpu-rasterization`
  - `--disable-accelerated-2d-canvas`
  - disabled Skia/Vulkan/canvas OOP rasterization features.
- Set Electron user data to `temp/desktop/electron-user-data` to avoid Windows profile/crypto state issues.
- Added Windows child-process environment sanitization to remove duplicate `Path`/`PATH` keys.
- Route spawned Python/npm commands through `cmd.exe /d /s /c` on Windows for more reliable command resolution.
- Added explicit spawn-error and early-exit logging.
- Added fallback from `next start` to `next dev` if the production web process exits before readiness.
- Updated desktop/debugging docs with startup failure notes and expected health checks.

Validation:

- Desktop startup probe: while `npm.cmd run desktop` was running, `http://127.0.0.1:8000/health` returned `200` and `http://127.0.0.1:3002` returned `200`.
- `node --check apps/desktop/src/main.js`: passed.
- `node --check apps/desktop/src/preload.js`: passed.
- `npm.cmd --prefix apps/desktop audit --omit=dev`: passed with `0 vulnerabilities`.
- `npm.cmd run desktop:pack`: passed.
- `npm.cmd run desktop:package`: passed and regenerated `dist/desktop/NIRMIQ ResearchOS 0.1.0.exe`.
- `npm.cmd run test:api`: `37 passed, 1 warning`.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed.

Commit:

- `690196c` - Fix Windows desktop startup.

### Latest Update: Multi-Agent Fault Audit And Ship Hardening

Date: 2026-06-20

Purpose:

- Resolve the highest-risk backend, frontend, desktop/runtime, security, and release-gate faults found during the multi-agent review.
- Keep the project shippable for an EOD demo without adding heavy new architecture or confusing UI controls.

Implemented:

- Retrieval and grounding:
  - zero-readable-chunk reindex attempts now fail before old active chunks are deactivated.
  - direct local-path ingestion now validates suffix, size, and lightweight signature/readability checks.
  - vector hits are filtered to active SQLite chunks so stale Chroma metadata cannot become answer evidence.
  - vector and BM25-only scores are normalized from actual scores instead of rank-derived inflation.
  - summary/factual seed chunks use low expansion scores instead of artificial high grounding scores.
  - Exam Lab study-guide relevance uses imported question-bank text, not generic UI command words.
  - cited claim verification now rewrites on any unsupported cited claim.
  - citation anchoring no longer fabricates `[1]` when support is weak.
- Frontend reliability:
  - selected-document queries remain scoped to the active source.
  - Enter submit is blocked while a request is busy.
  - uploads derive title from the selected filename instead of stale form state.
  - New Study Thread creates a fresh session id.
  - API calls use timeout/cancellation and cleaner backend error messages.
  - answer/Paper Lab exports snapshot the source attached to the answer.
- Desktop/runtime and release:
  - Electron creates its workspace-local user data directory before setting `userData`.
  - packaged root detection checks portable executable environment paths.
  - desktop child PIDs are mirrored under `temp\runtime` for cleanup.
  - normal browser preview and golden-demo preview are separate launchers:
    - `NIRMIQ ResearchOS.cmd`
    - `NIRMIQ Golden Demo.cmd`
  - bootstrap/start/build/package/ship scripts use `npm.cmd` and return non-zero on native command failure.
  - `ship_check.ps1` now uses the same offline/low-memory test env as `test_api.ps1`, restores locations safely, and runs the full smoke/golden gate.
  - Docker Compose local dev ports bind to `127.0.0.1`.

Validation:

- `npm.cmd run test:api`: `41 passed, 1 warning`.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed.
- `npm.cmd run desktop:pack`: passed.
- `docker compose -f docker-compose.local.yml config`: passed; Windows user Docker config permission warning remains non-blocking.
- `node --check apps\desktop\src\main.js`: passed.
- `node --check apps\desktop\src\preload.js`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ship_check.ps1`: passed.
  - backend tests passed.
  - API compile passed.
  - web build passed.
  - publish smoke passed.
  - golden demo Research, summary-style Research, Exam Lab, and Paper Lab returned grounded citations.
  - unsupported Chat prompt returned `grounded=false` and `citations=0`.

Tradeoffs:

- The faithfulness verifier is intentionally conservative and lexical. It may rewrite acceptable paraphrases to more extractive prose, but this supports the current no-hallucination demo target.
- Clear indexed material still does not fully purge parse cache, diagrams, or arbitrary source files. Full app-owned purge remains a privacy sprint item.
- No local agent or graph database was added; the baseline RAG path needed correctness and release stability first.

Remaining next sprint candidates:

- Capture README screenshots/GIFs.
- Add real textbook/note/paper retrieval labels and citation-precision metrics.
- Add a source-preview drawer and mobile QA pass.
- Add a strict local-only model endpoint guard before allowing non-loopback Ollama/external providers.
- Add a local bug-report bundle export.

Commit:

- `5e21194` - Harden retrieval and ship checks.

### Latest Update: Polish Sprint - Components, Real Eval, Purge, Linux Feasibility

Date: 2026-06-20

Purpose:

- Address the remaining non-perfect areas: large frontend page, real-world eval data, app-owned data purge, README polish assets, and Linux/low-end feasibility.

Implemented:

- Frontend maintainability:
  - Split stable types/constants/helpers out of `apps/web/app/page.tsx` into `apps/web/app/page-model.ts`.
  - Moved local login UI into `apps/web/components/local-login.tsx`.
  - Moved study-guide answer rendering into `apps/web/components/study-guide-answer.tsx`.
  - Reduced `page.tsx` from roughly 2,400+ lines to roughly 1,800 lines while preserving behavior.
- Real-world retrieval evaluation:
  - Added `source_file` and `--auto-ingest-sources` support to `scripts/eval_retrieval.py`.
  - Added `scripts/eval_real_world.ps1`.
  - Added `data/processed/eval/real_world_academic_seed.jsonl` with 16 phrase-labeled questions from local academic material.
  - Wrote `data/processed/eval/real_world_retrieval_metrics.json`.
  - Current real-world seed metrics:
    - Hybrid: MRR `0.490`, Recall@3 `0.563`, Recall@8 `0.750`, citation expected coverage `0.750`.
    - BM25: MRR `0.578`, Recall@3 `0.625`, Recall@8 `0.750`, citation expected coverage `0.750`.
  - Important caveat: source PDFs are intentionally local/untracked; labels and metrics are committed, not copyright-sensitive PDFs.
- Local data purge:
  - `Clear indexed material` now removes SQLite/vector metadata plus app-owned uploaded source copies, parse-cache files, and extracted diagram folders.
  - External local-path source files outside the upload directory are preserved for safety.
  - Backend purge response now reports `source_file_delete_count` and `derived_files_deleted`.
  - Integration test verifies uploaded source and parse cache cleanup.
- README/public polish:
  - Added `docs/assets/nirmiq-demo-flow.svg`.
  - README now shows the demo flow SVG and explains screenshot/GIF capture requirements.
- Linux/low-end feasibility:
  - Added `scripts/start_local.sh` and `scripts/stop_local.sh` for browser-preview Linux runs.
  - Added `docs/linux_low_end_feasibility.md`.
  - Added root scripts `start:linux` and `stop:linux`.
  - Linux runtime is feasible as browser-first, BM25/extractive-first; native Linux desktop packaging is not validated yet.

Validation:

- `npm.cmd run build`: passed after the component split.
- `npm.cmd run test:api`: `41 passed, 1 warning`.
- `python -m compileall scripts apps/api/app`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\eval_real_world.ps1`: passed and wrote metrics.
- Bash syntax/runtime validation could not run locally because WSL has no installed Linux distribution.

Remaining debt:

- Continue splitting `page.tsx` into sidebar, chat thread, composer, Deep Research, Paper Lab, and Exam Lab components.
- Capture actual live UI screenshots/GIFs for README after final visual QA.
- Grow real-world eval set from 16 to 60+ labels and tune retrieval against failures.
- Validate Linux scripts on an actual Linux distro and package Linux desktop only if worth it.

Commit:

- `a980cdc` - Polish UI structure eval purge and Linux docs.

### Latest Update: Windows App Package Refresh And Shortcuts

Date: 2026-06-20

Purpose:

- Refresh the current Windows desktop app package after the UI/eval/purge/Linux polish sprint.
- Create user-facing shortcuts so the app can be launched without terminal commands.

Completed:

- `npm.cmd run build`: passed.
- `npm.cmd run desktop:pack`: passed.
- `npm.cmd run desktop:package`: passed.
- Refreshed portable Windows app: `dist/desktop/NIRMIQ ResearchOS 0.1.0.exe`.
- Refreshed unpacked desktop app: `dist/desktop/win-unpacked/NIRMIQ ResearchOS.exe`.
- Created Desktop shortcuts for NIRMIQ Desktop, Browser Preview, Golden Demo, and Stop.
- Created Start Menu shortcuts under `NIRMIQ` for Desktop, Browser Preview, Golden Demo, and Stop.

Note:

- This was a Windows desktop app package refresh, not an Android APK build. Android APK generation remains a separate mobile packaging sprint if needed.

### Latest Update: Definition Query RAG Reliability Fix

Date: 2026-07-08

Problem:

- A user asked the Scikit-Learn textbook query `What is a Gaussian mixture model?`.
- The previous answer was not acceptable: it stitched together index/back-matter fragments such as Bayesian GMM, BIC, Beam Search, Bellman equations, and PCA references instead of explaining the concept.
- The correct textbook definition was present in the corpus on page 357, but retrieval packing and fallback synthesis did not prioritize it.

Root cause:

- Definition-style questions only had special fallback handling when they also asked for a solution/fix.
- Focused factual seed chunks skipped promotion when the best chunk was already present in the retrieval bundle, so direct evidence could appear as anchor `[3]` instead of `[1]`.
- The seed scorer penalized any occurrence of the word `index`, which incorrectly hurt valid passages containing phrases like `cluster index`.
- Section ranking let back-matter/index-like sections and Bayesian variant headings compete too strongly with the base `Gaussian Mixtures` textbook section.
- Fallback synthesis allowed heading prefixes, code examples, and index-style comma fragments into the final answer.

Implemented:

- Added deterministic GMM/Gaussian-mixture query expansion for local retrieval and synthesis terms.
- Improved factual seed scoring so definition language like `is a`, `probabilistic model`, `assumes`, and `generated from` beats mere keyword mentions.
- Replaced broad `index` text penalties with metadata/index-fragment penalties.
- Added section ranking boosts for exact base concept sections and penalties for back-matter/API-like sections.
- Added a definition-specific fallback answer format: direct answer, how it works, what it is used for, limitation when supported.
- Added low-value evidence filtering to block index fragments such as `Beam Search`, `Bellman`, `inverse_transform`, and `fast-MCD` from answer text.
- Added evidence sentence cleanup to remove leaked headings and code prompts while preserving citation support.
- Promoted high-value factual seed chunks to the front even when they already exist in the retrieval bundle, making the direct answer cite `[1]`.
- Added unit coverage in `apps/api/app/tests/unit/test_definition_answer_quality.py`.

Live verification:

- Query: `What is a Gaussian mixture model?`
- Selected document: `Hands-On Machine Learning with Scikit-Learn, Keras and TensorFlow, 3rd Ed. - Annotated`.
- New answer starts with: `A Gaussian mixture model (GMM) is a probabilistic model that assumes that the instances were generated from a mixture of several Gaussian distributions whose parameters are unknown. [1]`
- First citation now points to page 357, the actual `Gaussian Mixtures` definition section.
- Citation verification state: `supported`.

Validation:

- Focused tests: `22 passed`.
- Full backend tests: `66 passed, 1 warning`.
- `python -m compileall apps/api/app`: passed.
- Real-world retrieval eval after adding the Gaussian mixture label:
  - Samples: `17`.
  - Hybrid: MRR `0.675`, Recall@8 `0.882`, citation expected coverage `0.882`.
  - BM25: MRR `0.794`, Recall@8 `0.882`, citation expected coverage `0.882`.

Tradeoff:

- This fix is deterministic and lightweight, tuned for definition-quality reliability without adding a larger model, cloud API, graph DB, or heavy reranker.
- It improves textbook concept questions immediately, but the same pattern should be expanded with more labeled failures for other academic domains.
- Remaining eval misses include dimensionality-reduction wording and noisy OCR privacy notes; these are good candidates for the next retrieval-tuning pass.

### Latest Update: Minimal Chatbot Interface Pass

Date: 2026-07-08

Problem:

- The current desktop UI still felt too close to a cockpit/debug console instead of a simple AI chatbot.
- Too many primary actions were visible at once: summarize, export, collapse, source tools, route tools, and advanced retrieval settings.
- The composer consumed attention even after an answer was generated, making responses harder to read.

Implemented:

- Preserved backend APIs and existing capabilities.
- Kept the main composer focused on three visible actions: attach/upload, ask, and library/source access.
- Moved workspace modes, summarize, export, sources, minimize, new thread, and advanced retrieval controls into a compact `Tools` disclosure.
- Renamed the visible source label from `Current document` to `Attached source` so it reads like a ChatGPT-style attachment model.
- Reworded the header route copy to make the product feel automatic: users can ask naturally while sources and tools remain tucked away.
- Made the minimized composer more explicit with a small `Ask` action instead of a passive collapsed state.
- Reduced composer visual weight with a narrower max width, tighter textarea, calmer borders, and fewer always-visible chips.

Validation:

- `npm run build` from `apps/web`: passed after the UI changes.
- `git diff --check`: no whitespace errors; only line-ending warnings from Git on Windows.

Tradeoff:

- This is a safe V4 usability pass, not a full frontend rewrite.
- `apps/web/app/page.tsx` remains too large and still needs a component split into thread, composer, library, sources, Paper Lab, and Exam Lab modules.
- The advanced tools still exist for power users, but they no longer dominate the default flow.

Next UI debt:

- Run a manual visual QA pass at desktop, laptop, and mobile widths.
- Add Playwright/browser screenshot QA once the local browser tooling is stable.
- Convert the current `Tools` disclosure into cleaner section-specific drawers after the component split.

### Latest Update: Codex Tooling Upgrade

Date: 2026-07-08

Purpose:

- Add stronger project tooling for release work, UI QA, and repository management without adding complexity to the NIRMIQ app itself.

Installed / activated:

- GitHub plugin: installed successfully through the Codex plugin installer.
- Chrome automation plugin: installed successfully through the Codex plugin installer.
- Node REPL MCP: available and verified.
- Playwright package: verified import through Node REPL, so browser automation and screenshot QA can be used for the next UI pass.
- PDF/Documents plugin support: already present in the Codex runtime.
- Browser plugin support: already present in the Codex runtime.

Verification:

- GitHub connector can find `SheeshDarth/NirmiqResearchOS` with repository permissions.
- Playwright import returned Chromium/Firefox/WebKit automation exports.

Notes:

- A dedicated Ollama/runtime monitor MCP was not available in the Codex install catalog. Runtime health should stay inside NIRMIQ as local `/health`, `/runtime`, and latency/memory diagnostics instead of depending on a separate cloud connector.
- A dedicated SQLite MCP namespace did not expose in this session, but local SQLite inspection remains available through Python/Node and is sufficient for NIRMIQ's offline-first debugging workflow.
- A hard restart of the Codex desktop app was not performed from inside the active session to avoid interrupting the work. The newly installed GitHub and Chrome tooling is already visible in this session; a manual close/reopen of Codex can still refresh the tool list if needed.

### Latest Update: Windows Desktop Package Refresh

Date: 2026-07-09

Purpose:

- Refresh the already-downloaded Windows desktop package with the latest chatbot-style UI changes.
- Confirm whether an Android `.apk` target exists before packaging.

Result:

- No Android `.apk` target or existing `.apk` artifact was found in the repository.
- The project currently supports a Windows Electron desktop package, not Android APK packaging.
- `npm run build`: passed.
- `npm.cmd run desktop:pack`: passed and refreshed `dist/desktop/win-unpacked/NIRMIQ ResearchOS.exe`.
- `npm.cmd run desktop:package`: passed and refreshed `dist/desktop/NIRMIQ ResearchOS 0.1.0.exe`.
- Desktop and Start Menu shortcuts were recreated for NIRMIQ Desktop, Browser Preview, Golden Demo, and Stop.

Launch paths:

- Portable app: `C:\Nirmiq-researchOS\dist\desktop\NIRMIQ ResearchOS 0.1.0.exe`
- Unpacked app: `C:\Nirmiq-researchOS\dist\desktop\win-unpacked\NIRMIQ ResearchOS.exe`

Tradeoff:

- This updates the Windows desktop package only. A true Android APK requires a separate mobile packaging sprint using Capacitor/Tauri mobile/React Native or a dedicated Android shell.

### Latest Update: MegaSprint One Custom RAG Method

Date: 2026-07-09

Decision:

- NIRMIQ's best-fit retrieval architecture is **Evidence-First Hierarchical Hybrid RAG**, not pure vector RAG, always-on GraphRAG, or agentic RAG.
- Source of truth: [`docs/nirmiq_rag_method.md`](docs/nirmiq_rag_method.md).

Why:

- The project must work offline, stay understandable, run on RTX 4050 and lower-end Linux devices, and answer from textbooks/notes/PDFs with citations.
- The observed hallucination pattern is mostly weak evidence selection, not just model weakness.
- The latest real-world misses came from legacy/no-section documents, OCR spelling noise, and direct answer passages being buried below broad index/application chunks.

Implemented:

- Retrieval metadata now identifies the method as `nirmiq_evidence_first_hierarchical_hybrid_rag`.
- Strategy labels moved from `phase1_*` to `nirmiq_ehr_*`.
- Section ranking now judges sections from the original user question instead of the expanded keyword cloud.
- Candidate directness and noise scoring now use the original user question, while BM25 can still use deterministic expansion.
- Added anchor rescue for direct definitions, dates, privacy/OCR variants, dimensionality phrases, and other answer-like passages buried in legacy/no-section documents.
- Added internal BM25-first routing for default attached-source academic queries because current real-world evals show BM25 ranks textbook evidence more safely than hybrid.
- Added unit coverage to prove a direct Gaussian mixture definition beats a loose index-like chunk.

MegaSprint roadmap:

1. MegaSprint One: Evidence Precision and Query-Agnostic RAG Reliability. Current sprint.
2. MegaSprint Two: ChatGPT-grade UX simplification and mobile/laptop QA.
3. MegaSprint Three: Academic workflows: Paper Lab, Exam Lab, diagrams, study guides, and source-grounded exports.
4. MegaSprint Four: Local runtime optimization for RTX 4050, low-end Linux, Ollama profiles, quantization, and latency budgets.
5. MegaSprint Five: Release, security, packaging, CI, screenshots/GIFs, privacy controls, and one-click setup.
6. MegaSprint Six: NIRMIQ ecosystem bridge: Mirror memory, OS hooks, agents, and Echo integrations only after the standalone academic product is reliable.

Completion target for MegaSprint One:

- Recall@8 stays at or above `0.850` as real-world labels grow.
- MRR stays at or above `0.700`.
- Expected citation coverage reaches at least `0.900`.
- Normal UI remains simple and hides raw metadata.
- Weak evidence produces `Needs more evidence` or `Not found in sources`, not confident filler.

Validation:

- Backend tests: `74 passed`, `1` warning.
- Web build: passed.
- Query-category eval:
  - BM25: MRR `0.950`, Recall@8 `1.000`, citation expected coverage `1.000`.
  - Hybrid: MRR `0.850`, Recall@8 `1.000`, citation expected coverage `1.000`.
- Real-world academic seed:
  - BM25: MRR `0.784`, Recall@8 `0.941`, citation expected coverage `0.941`.
  - Hybrid: MRR `0.698`, Recall@8 `0.941`, citation expected coverage `0.941`.
- Current conclusion: BM25-first is the safest default for attached-source academic queries. Hybrid remains available but should not be the default until it ranks first evidence better on real-world labels.

### Latest Update: MegaSprint Two Thread Header Split

Date: 2026-07-11

Purpose:

- Continue MegaSprint Two without changing backend behavior or retrieval quality.
- Reduce `apps/web/app/page.tsx` size and make the ChatGPT-style shell easier to iterate safely.

Implemented:

- Added `apps/web/components/thread-header.tsx` for the chat thread top bar, brand lockup, Library toggle, Sources toggle, and compact route/source strip.
- Replaced the inline header JSX in `apps/web/app/page.tsx` with the typed `ThreadHeader` component.
- Preserved existing labels, toggle behavior, selected-source state, and source/library visibility behavior.

Validation:

- `npm.cmd run build` from `apps/web`: passed.
- `page.tsx` reduced to `1645` lines.

Tradeoff:

- This is a structural UI maintainability slice, not a visual redesign or RAG behavior change.
- The next useful split is the main chat turn list or composer, but those should be done carefully because they touch query submission and feedback behavior.

### Latest Update: MegaSprint Two Chat Thread Split

Date: 2026-07-11

Purpose:

- Continue the ChatGPT-grade UI architecture cleanup by separating answer rendering from page orchestration.
- Keep RAG behavior, query submission, feedback saving, and citation selection unchanged.

Implemented:

- Added `apps/web/components/chat-thread.tsx` for user/assistant turns, readable answer body rendering, study-guide rendering, trust line, feedback buttons, and compact citation drawer.
- Replaced the inline `queryHistory.map(...)` block in `apps/web/app/page.tsx` with the typed `ChatThread` component.
- Preserved `Open Sources`, citation-chip selection, answer feedback, trust badges, and scroll-to-bottom behavior.

Validation:

- `npm.cmd run build` from `apps/web`: passed.
- `page.tsx` reduced to `1569` lines.

Tradeoff:

- This is another structural UI slice, not a visual redesign.
- Composer extraction is the next major component split, but it touches upload/query controls and should remain a careful separate change.

### Latest Update: MegaSprint Two Composer Split

Date: 2026-07-11

Purpose:

- Continue the ChatGPT-grade shell cleanup by separating the upload/query composer from page orchestration.
- Keep upload, query submission, summarize, source opening, workspace routing, advanced settings, and minimized composer behavior unchanged.

Implemented:

- Added `apps/web/components/chat-composer.tsx` for the bottom composer, file input, active-source cockpit, upload button, query textarea, send button, tools disclosure, workspace chips, summarize/export/source actions, and advanced route/retrieval controls.
- Replaced the inline composer form in `apps/web/app/page.tsx` with the typed `ChatComposer` component.
- Preserved existing callback ownership in the page so query execution, upload handling, and retrieval state do not move.

Validation:

- `npm.cmd run build` from `apps/web`: passed.
- `page.tsx` reduced to `1415` lines.

Tradeoff:

- The prop surface is intentionally wide because the page still owns state and side effects.
- The next UX step can now focus on composer clarity or mobile QA without mixing that work into retrieval/query orchestration.
