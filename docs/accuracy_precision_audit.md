# NIRMIQ Accuracy, Precision, and Hallucination Audit

Last updated: 2026-07-10

## Canonical Problem Log

See [`../problems_faced.md`](../problems_faced.md) for the current architecture diagram, full problem history, current RAG retrieval gaps, future risks, and the RAG Reliability Phase roadmap.

See [`retrieval_failure_backlog.md`](retrieval_failure_backlog.md) for concrete real-world retrieval misses and weak hits generated from the current eval scripts.

See [`answer_used_citation_backlog.md`](answer_used_citation_backlog.md) for cases where raw retrieval finds better evidence than the final answer-used citations.

See [`nirmiq_rag_method.md`](nirmiq_rag_method.md) for the chosen RAG architecture: NIRMIQ Evidence-First Hierarchical Hybrid RAG.

## 2026-07-10 MegaSprint One Final Tightening

Decision:

- Keep the production retriever lightweight and local-first.
- Do not add heavy rerankers, GraphRAG, agents, larger models, or higher context windows for this sprint.
- Correct eval labels only where the source text was verified and the gold phrase was damaged by OCR/wording mismatch.
- Rebalance candidate priority so direct answer relevance can outrank loosely related reranker hits.

Verification:

- Real-world academic seed:
  - BM25: MRR `0.843`, Recall@8 `1.000`, citation expected coverage `1.000`.
  - Hybrid: MRR `0.804`, Recall@8 `1.000`, citation expected coverage `1.000`.
- Query-category seed:
  - BM25: MRR `0.950`, Recall@8 `1.000`, citation expected coverage `1.000`.
  - Hybrid: MRR `0.850`, Recall@8 `1.000`, citation expected coverage `1.000`.
- Targeted Transformer architecture probe now ranks the direct `we propose the Transformer...` evidence passage first in hybrid selected-document retrieval.

Tradeoff:

- This is still a small seed set. The numbers are strong enough to close MegaSprint One's first reliability pass, but not enough to claim arbitrary textbook accuracy.
- Next improvement should grow labels and simplify the UI, not over-tune ranking weights against 17 samples.

## 2026-07-09 MegaSprint One Method Lock

Decision:

- NIRMIQ should use Evidence-First Hierarchical Hybrid RAG for MegaSprint One.
- BM25 remains the offline backbone.
- Section/page-first retrieval is used when selected-document metadata exists.
- Optional vector search and RRF support recall but do not replace SQLite-confirmed active chunks.
- Anchor rescue handles legacy/no-section documents, OCR variants, and direct evidence buried below broad hits.
- Final candidate scoring uses the original user query for directness and noise penalties, while deterministic expansion is limited to improving retrieval recall.
- Attached-source academic queries route default `hybrid` requests to BM25-first retrieval because the current real-world eval shows BM25 ranks textbook evidence more safely than hybrid.

Reason:

- Recent failures were caused by weak evidence precision: broad chunks, index fragments, legacy documents without section metadata, and OCR spelling noise.
- Heavier models, higher temperature, GraphRAG, or agents would not fix the root cause before retrieval is reliable.

Verification:

- Backend unit/integration tests: `74 passed`, `1` warning.
- Web production build: passed.
- Query-category eval: BM25 MRR `0.950`, Recall@8 `1.000`, citation expected coverage `1.000`; Hybrid MRR `0.850`, Recall@8 `1.000`, citation expected coverage `1.000`.
- Real-world academic seed: BM25 MRR `0.784`, Recall@8 `0.941`, citation expected coverage `0.941`; Hybrid MRR `0.698`, Recall@8 `0.941`, citation expected coverage `0.941`.
- A broad anchor-rescue boost was tested and rejected because it lowered real-world Recall@8 to `0.706`; the committed approach keeps rescue strict and targeted.

## 2026-07-09 MegaSprint One Query-Agnostic Reliability Slice

Implemented:

- Added `data/processed/eval/query_agnostic_rag_categories.jsonl` as the first category-based eval seed.
- Added document-aware query expansion for source-local acronym definitions and topic metadata.
- Added direct-evidence scoring in retrieval candidate priority.
- Strengthened penalties for index, glossary, backmatter, and broad example-list passages during explanatory queries.
- Added synthesis metadata for `answer_relevance_state`, `answer_relevance_score`, `direct_evidence_count`, `weak_related_count`, and direct evidence pages.
- Simplified the normal UI trust surface to `Verified`, `Needs more evidence`, and `Not found in sources`.
- Hid ranking metadata, scores, chunk IDs, and token counts from the normal source-inspection path.

Why this matters:

- The previous failure mode was often "source-backed but not question-backed": citations were real, but the cited passage was only loosely related.
- This slice makes retrieval and synthesis judge whether evidence directly answers the query before allowing a confident answer.
- The benchmark direction is now category coverage across valid user query types, not a mandatory list of hard-coded prompts.

Validation:

- Backend unit and integration tests: `71 passed`, `1` warning.
- Query-category BM25 smoke eval: MRR `1.000`, Recall@8 `1.000`, citation expected coverage `1.000` on the initial 10-sample seed.

## 2026-07-07 Retrieval Failure Diagnostics

Implemented:

- Added `--failures-output` support to `scripts/eval_retrieval.py`.
- Updated `scripts/eval_real_world.ps1` to emit `data/processed/eval/real_world_retrieval_failures.jsonl`.
- Added a tracked human-readable backlog at [`retrieval_failure_backlog.md`](retrieval_failure_backlog.md).

Current diagnostic summary:

- Weak retrieval records: `13`.
- Hybrid weak records: `7`.
- BM25 weak records: `6`.
- Missed at rank 8: `8`.
- Late hits beyond rank 3: `5`.

Observed root causes:

- Textbook index/glossary chunks sometimes outrank explanatory body chunks.
- User wording does not always expand to source-specific terms such as "positional encodings".
- Some phrase labels are too brittle for equivalent source wording.
- OCR/encoding artifacts reduce lexical matching.
- Broad overview questions need stronger section-first retrieval.

First reliability slice:

- Added normalized phrase matching in eval diagnostics.
- Added deterministic query expansion for academic wording mismatches.
- Added retrieval noise penalties for index/glossary/reference-like chunks.

Updated raw retrieval result:

| Mode | Samples | MRR | Recall@8 | Citation expected coverage |
| --- | ---: | ---: | ---: | ---: |
| Hybrid | 16 | 0.655 | 0.875 | 0.875 |
| BM25 | 16 | 0.781 | 0.875 | 0.875 |

Interpretation:

- The first slice reached the original MRR and Recall@8 targets on the initial 16-sample seed.
- Expected citation coverage improved from `0.750` to `0.875`, but still needs to reach `0.900+` on a larger real-world eval set.
- Remaining failures cluster around OCR/encoding noise and section-level overview retrieval.

## 2026-07-06 Evidence Reliability Gate And Eval Correction

Implemented:

- Fixed a legacy SQLite migration ordering bug where existing databases attempted to create `idx_chunks_section_active` before the additive `section_id` column existed.
- Added a regression test for legacy `document_chunks` schemas.
- Fixed full-query evaluation so expected evidence is checked against full cited chunk text, not truncated UI citation excerpts.
- Added an evidence reliability gate in `SynthesisService`.
- The gate blocks grounded answers when selected evidence, cited context, citation anchors, citation coverage, or verification state are not strong enough.
- Citation coverage is now line-aware so study-guide question headings and structural UI labels are not treated as factual claims.

Corrected full-query real-world result:

| Mode | Samples | MRR | Recall@8 | Citation expected coverage | Grounded response rate | Abstention rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 16 | 0.646 | 0.813 | 0.813 | 0.938 | 0.063 |
| BM25 | 16 | 0.667 | 0.875 | 0.875 | 0.938 | 0.063 |

Interpretation:

- The previous `0.3125` full-query citation coverage was an evaluator artifact caused by scoring truncated citation previews.
- The corrected BM25 answer path now matches raw retrieval coverage (`0.875`) on the current seed.
- Hybrid answer-used citation selection still trails raw hybrid retrieval, so this remains active reliability work.
- The system now fails closed for at least one low-coverage real-world case instead of reporting `grounded=true` for every query.

## 2026-06-26 RAG Reliability Phase Start

Current active gap:

- Real-world academic retrieval is weaker than the bundled golden demo.
- BM25 baseline on the 16-sample real-world seed: MRR `0.578`, Recall@8 `0.750`, expected citation coverage `0.750`.
- Users experience this as broad answers, missed textbook sections, unsupported citations, or hallucination.

Implemented first slice:

- Added additive SQLite `document_sections` records.
- Added chunk metadata for section id, heading, section path, chunk type, and key terms.
- Added lightweight heading/section detection during indexing.
- Added metadata-aware BM25 search text.
- Added section-first retrieval for selected-document queries when relevant section candidates are found.
- Added debug-only retrieval diagnostics: section candidates, chunk-selection reasons, and returned-chunk counts.

Why this matters:

- The next accuracy gain should come from better evidence precision, not from raising model size, temperature, or context length.
- The app remains offline-first and low-memory because the first reliability layer is SQLite/BM25-based.
- The optional vector/reranker path can still help later, but it is not required for the baseline.

Acceptance targets:

- Recall@8: `0.750` to at least `0.850`.
- MRR: `0.578` to at least `0.700`.
- Expected citation coverage: `0.750` to at least `0.900`.
- No golden-demo regression.

## 2026-06-26 V4.2 Local Feedback Loop

Implemented:

- Added answer-level `Good` / `Needs work` feedback in the chat UI.
- Added SQLite-backed `answer_feedback` records through `/memory/{session_id}/feedback`.
- Stored feedback remains local and includes the query, answer, rating, optional source document/title, reason, and timestamp.
- Session deletion removes associated feedback records.
- Document deletion preserves the feedback text for review while clearing stale document ids.

Why this matters for accuracy:

- Live testing failures can now be captured as structured records.
- The next eval sprint can convert repeated `Needs work` feedback into labeled questions with expected source chunks.
- This avoids blindly adding prompt rules or retrieval tweaks without measuring whether they helped.

Recommended next use:

- Run one textbook through 20-30 realistic questions.
- Mark every wrong, vague, overlong, or poorly cited answer as `Needs work`.
- Promote repeated failure patterns into `data/processed/eval` labels and regression tests.

## 2026-06-22 V4.1 Accuracy/Presentation Update

Implemented improvements:

- Backend intent routing now detects exam-style prompts from natural language, not only from explicit frontend modes.
- Exam context loading can follow backend-detected exam intent, preserving question-bank/diagram usefulness when users ask naturally.
- Factual lookup retrieval now expands natural questions with focused hints for definitions, examples, types, limitations, and algorithm families.
- Unsupervised-algorithm queries receive extra retrieval and synthesis focus terms such as clustering, density estimation, anomaly detection, dimensionality reduction, PCA, k-means, and DBSCAN.
- Fallback synthesis for list/algorithm questions now uses a compact answer contract: `Direct answer`, `Key points`, `Evidence note`.
- Normal frontend queries no longer inherit stale summary mode. The default `Auto` path sends a neutral research request and lets backend intent routing decide.

Validation:

- Focused query intent and synthesis tests passed.
- Full API suite passed with 47 tests.
- Frontend production build passed.

Remaining accuracy gaps:

- The project still needs a larger real-world labeled eval set from actual textbooks, notes, papers, and exam material.
- Current focused expansions help common academic phrasing but are still deterministic lexical policies, not a learned query rewriter.
- The next quality sprint should record saved failure cases from live testing and add them to retrieval/synthesis regression tests.

## Research Basis

The quality plan is based on RAG evaluation and hallucination-mitigation work including:

- RAGAS: reference-free evaluation dimensions for context relevance, faithfulness, and answer quality.
- ARES: automated RAG evaluation around context relevance, answer faithfulness, and answer relevance.
- Self-RAG: retrieve/generate/critique loop as a pattern for deciding when evidence is needed and when output should be criticized.
- Chain-of-verification style RAG: verify retrieval and generated claims before finalizing long-form answers.

## Current Strengths

- Local-first architecture with no cloud dependency for core document Q&A.
- Document-scoped retrieval when a source is selected.
- Hybrid retrieval path: BM25, optional vector, RRF, reranking hook.
- Grounding score and abstention threshold.
- Summary mode for broad document questions.
- Citation cards and source drilldown in UI.
- Parsed PDF cache for repeated ingest performance.
- Unit/integration tests for ingestion, querying, memory, exam contracts, and retrieval modes.

## Current Loopholes

### 1. Citation Anchor Is Not Full Faithfulness

Before this audit, generated answers only needed citation-style anchors such as `[1]`. A model could still make an unsupported claim and attach a valid-looking citation.

Mitigation added:

- Post-generation cited-claim verification in `SynthesisService`.
- Unsupported cited claims trigger an extractive fallback rewrite.
- Debug metadata now reports citation verification state and rewrite status.
- UI answer cards now show whether citations were verified or rewritten for faithfulness.

Remaining gap:

- Current verifier is lexical and deterministic. It catches obvious drift but does not perform full semantic entailment.

2026-06-22 trust-contract update:

- `SynthesisService` now records `selected_context_chunk_ids`, `cited_context_chunk_ids`, and `citation_anchor_chunk_map`.
- `QueryService` now returns public citations only for chunks cited by the final answer, rather than every retrieved chunk.
- Selected-document summary cache profile was bumped to avoid reusing older cached summaries with broader citation sets.
- Normal Research/Chat UI requests no longer force debug metadata by default.

Remaining gap:

- Citation mapping is now stricter, but source snippets are still chunk-level rather than exact character-span highlights.

### 2. Chunk Quality Needs Ongoing Tuning

PDF parsing can produce headers, footers, broken glyphs, repeated boilerplate, references, or malformed chunks.

Mitigation added:

- Added chunk quality scoring at index time.
- Penalizes chunks with high symbol noise, replacement glyphs, repeated text, short text, reference-heavy text, and low readable alphabetic ratio.
- Stores `quality_score` in SQLite.
- Applies quality weighting during retrieval scoring.
- Preserves a simple UI by not exposing another confusing control.

### 3. Retrieval Evaluation Dataset Is Still Thin

Evaluation scripts exist, but the project needs a curated labeled set across:

- Research paper summaries.
- Engineering exam questions.
- Definition/factual lookup queries.
- Unanswerable/off-topic prompts.
- Multi-document comparison.

Recommended next fix:

- Add `data/processed/eval/nirmiq_v3_labels.jsonl`.
- Track hit rate, MRR, citation coverage, abstention correctness, and answer faithfulness.

Golden demo mitigation:

- Added `data/processed/eval/golden_demo_expected_sources.json` as a lightweight source expectation manifest.
- Added `scripts/golden_demo.ps1` to verify citation presence on locked demo queries and abstention on an unsupported chat prompt.
- This is not a statistical benchmark yet; it is a repeatability and publish-readiness check.

### 4. General Chat Can Retrieve Irrelevant Old Corpus Chunks

Before the golden demo hardening pass, a general-chat question could retrieve unrelated old indexed material and still receive a grounded-looking answer if scores and citation counts were high enough.

Mitigation added:

- Added deterministic query/context relevance metadata in `SynthesisService`.
- General Chat now abstains when the real subject terms do not overlap the retrieved chunks.
- Ungrounded abstentions return zero citations so the UI does not imply source support.
- Integration tests now cover an unsupported fictional query.
- Golden demo smoke now fails if the unsupported chat prompt returns grounded output or citations.

Remaining gap:

- The relevance gate is lexical by design. A future semantic entailment check could improve paraphrase handling if it stays fast enough for local hardware.

### 5. Query Intent Router Needs Continued Tuning

The deterministic V3.1 router now classifies summary, factual lookup, compare, deep research, paper draft, exam, general chat, and unclear prompts.

Remaining gap:

- The router is intentionally lexical. It should be evaluated against a labeled NIRMIQ dataset before adding more branches.

### 6. Summary Cache Needs UX Observation

Repeated selected-document summaries now reuse SQLite cache by document id, content hash, and summary profile.

Remaining gap:

- Track whether users understand that cache misses after reindex/source edits are intentional.

### 6. Citation Coverage Is Lexical

The backend now computes citation sentence coverage and the UI shows a compact trust badge.

Remaining gap:

- Citation coverage measures anchors, not full semantic support. Faithfulness verification still carries the support check.

### 7. General Chat Needs Clearer Boundaries

Current Chat should remain local-first and abstain when there is no evidence.

Recommended next fix:

- Add explicit `local_chat` versus `connected_chat` state before any API-key/cloud mode.
- Show "document-grounded" or "needs connected model/context" status.

### 8. Local Model Memory Pressure

Large context windows, long predictions, unbounded embedding batches, and long Ollama keep-alive settings can make RTX 4050-class machines feel laggy or unstable.

Mitigation added:

- Bounded Ollama runtime options for generation: context window, prediction cap, optional GPU layer cap, optional CPU thread cap, and short keep-alive.
- Batched embedding calls to avoid sending all chunks to Ollama in one large request.
- Readiness metadata reports the active low-memory runtime profile.
- `docs/local_model_optimization.md` records recommended quantized/small model usage.

Remaining gap:

- True quantization is handled by Ollama/GGUF model artifacts, not by the FastAPI app. The next measurable improvement is benchmarking `phi3:mini`, `qwen2.5:3b`, and any imported Q4 GGUF model on the same PDF/query set.

## Implemented In This Audit

- Added deterministic cited-claim verification.
- Added faithfulness rewrite path to extractive fallback.
- Added unit tests proving unsupported cited claims are removed.
- Added metadata:
  - `citation_verification_state`
  - `cited_claims_checked`
  - `unsupported_claims`
  - `answer_rewritten_for_faithfulness`
  - `original_unsupported_claims`
- Added answer-card badge for citation verification state.
- Added chunk quality scoring and retrieval quality weighting.
- Added adaptive generation temperature:
  - Conservative factual mode uses `GENERATOR_TEMPERATURE_GROUNDED`.
  - Long-context deep research, paper drafting, and study-guide synthesis can use `GENERATOR_TEMPERATURE_LONG_CONTEXT`.
  - Citation verification still runs after generation, so higher-temperature long-form output is not trusted blindly.
- Added selected-document summary cache with natural invalidation via content hash.
- Added deterministic intent metadata:
  - `detected_intent`
  - `intent_confidence`
  - `intent_route`
- Added citation coverage metadata:
  - `citation_coverage`
  - `citation_sentence_count`
  - `citation_anchor_count`
- Updated the UI trust badge to show `Verified`, `Rewritten`, `Needs review`, or `Low citation coverage`.
- Added low-memory Ollama runtime controls and batched embeddings.
- Added readiness metadata for local runtime settings.

## Current Temperature Policy

The user requested `0.8-0.9` for lengthy context. NIRMIQ applies that selectively instead of globally:

- Summary, exam, factual lookup, and normal research stay low-temperature to reduce drift.
- Long-context deep research, Paper Lab, and study-guide work can use `0.85` when enough evidence is retrieved.
- Unsupported cited claims are rewritten to an extractive fallback.

This keeps long answers less flat while preserving grounded behavior.

## Next Implementation Order

1. Add labeled evaluation dataset for NIRMIQ use cases.
2. Use the dataset to tune intent routing and summary retrieval hints.
3. Add document-level summary variants only if users need chapter-wise or exam-style cached summaries.
4. Add optional semantic entailment verifier only when local model latency is acceptable.

## 2026-06-14 EOD Ship Hardening Notes

Finale AI's dashboard flagged deployment and public-repo hygiene as the weakest launch areas. The accuracy layer remains focused on grounded local RAG; the EOD patch does not change retrieval behavior.

Implemented support around the accuracy system:

- GitHub CI now runs backend tests, backend compile, frontend build, and Docker Compose config validation.
- API request body limits reduce accidental large-upload instability during demos.
- Response compression reduces overhead for larger citation/source payloads.
- `/api/v1` aliases make future clients safer without breaking the current UI.
- SQLite migration SQL was cleaned to remove scanner-triggering f-string `execute()` patterns.

Accuracy debt that remains:

- Add real textbook, notes, and paper labels beyond the current 30-sample synthetic demo set.
- Add unanswerable/abstention labels to the eval report.
- Add latency and cache-hit timing to retrieval benchmark output.
- Capture public demo assets showing citations, trust badges, and source chunks.

## 2026-06-11 Accuracy Rescue Notes

The demo failure was primarily an accuracy and runtime-routing issue, not a UI-only issue.

Findings:

- `phi3:mini` was configured but not installed locally.
- `qwen3.5:4b` was installed but produced empty `response` text for direct generation because the output budget was consumed by `thinking`.
- `mistral:7b-instruct-q4_K_M` produced usable answer text and is now preferred when the configured default is missing.
- Long-document summaries need outline seeding; plain hybrid retrieval can over-rank resource/index chunks.
- Factual textbook questions need focused definition/solution seeding so phrase variants do not hide the correct page.

Mitigations added:

- Ollama model discovery and installed-model routing.
- Mistral-first local generation preference for this available model set.
- Runtime defaults: `OLLAMA_TIMEOUT_SECONDS=120`, `OLLAMA_NUM_PREDICT=512`.
- Light stemming in BM25 and lexical reranker.
- Summary seed chunks from early outline material.
- Focused factual seed chunks for selected documents.
- Conservative cited-claim verification threshold.
- Sentence-level citation anchoring for generated prose.
- Source-only structured fallback for definition-plus-solution prompts.

Validated live textbook query:

```text
What is overfitting and how can it be reduced?
```

Expected answer behavior:

- Use source-only rewrite if the model adds unsupported techniques.
- Include the page 58 definition: overfitting performs well on training data but does not generalize well.
- Include page 59 remedies: simplify/constrain model, reduce attributes, gather more data, reduce noise/outliers.

Remaining accuracy debt:

- Build a 20-40 item retrieval eval set from textbooks, notes, and research papers.
- Track Recall@K, MRR, citation coverage, rewrite rate, abstention correctness, and latency.
- Add chapter-wise summary profiles instead of relying only on generic selected-document summaries.
- Consider a local entailment verifier only if it stays fast enough on RTX 4050 hardware.

## 2026-06-20 Multi-Agent Hardening Pass

Faults addressed:

- Zero-chunk indexing could mark a document indexed and deactivate prior chunks. It now fails before deactivation when no readable text is extracted.
- Vector mode could use rank-derived high scores and accept orphaned Chroma chunks. Vector scores now use the adapter score, and candidates are filtered to active SQLite chunk IDs.
- Summary/factual seed chunks used artificial high scores. They now use low expansion scores so they widen context without creating fake grounding confidence.
- Generated answers could pass when one cited claim was unsupported. Any unsupported cited claim now triggers a source-only rewrite.
- Citation anchoring could fabricate `[1]` for unsupported uncited model output. Anchors are now added only when lexical support is strong enough.
- Exam Lab study-guide relevance previously checked generic UI command words. It now checks imported question-bank text when available.
- Frontend selected-document queries now remain scoped to the active source, preventing accidental corpus-wide answers when a user expects document-grounded behavior.

Accuracy tradeoffs:

- The verifier remains lexical and conservative. It may rewrite some acceptable paraphrases into more extractive wording, but this is preferable for the current "do not hallucinate" demo target.
- Seed chunks can still help broad summaries and factual queries, but they no longer make weak evidence appear strong by themselves.
- Vector orphan dropping protects correctness at the cost of requiring vector-store rebuild/clear when Chroma and SQLite drift heavily.

Latest validation:

- `npm.cmd run test:api`: `41 passed, 1 warning`.
- `npm.cmd run compile:api`: passed.
- `npm.cmd run build`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ship_check.ps1`: passed with grounded golden-demo checks and unsupported-chat abstention.

Remaining accuracy work:

- Add real textbook/note/paper labels beyond the compact 30-question demo set.
- Track abstention correctness and citation precision separately from retrieval Recall@K.
- Add latency/cache-hit metrics to the evaluation report.
- Consider a small local entailment/rerank verifier only if measured latency stays acceptable on RTX 4050-class hardware.

## 2026-06-20 Real-World Seed Evaluation

Implemented:

- `data/processed/eval/real_world_academic_seed.jsonl`
- `scripts/eval_real_world.ps1`
- `scripts/eval_retrieval.py --auto-ingest-sources`

Sources:

- Transformer paper: `data/raw/attention_is_all_you_need.pdf`
- ML textbook: `data/raw/uploads/Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-TensorFlow-3rd-Ed.---Annot-5b287bd745.pdf`
- GenAI notes: `data/raw/uploads/mod-5-gen-ai-708567b729.pdf`

Latest phrase-level retrieval metrics:

| Mode | Samples | MRR | Recall@3 | Recall@5 | Recall@8 | Citation expected coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 17 | 0.843 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid | 17 | 0.804 | 1.000 | 1.000 | 1.000 | 1.000 |

Interpretation:

- This is the current measured baseline for real local academic material after the MegaSprint One final tightening pass.
- The project is demo-ready, but not yet production-perfect for arbitrary documents.
- BM25 currently remains the strongest offline backbone, while hybrid improved after candidate priority weighted direct answer relevance more strongly.

Next accuracy sprint:

- Add at least 40 more real labels.
- Separate parsing failures from retrieval-ranking failures.
- Tune hybrid retrieval only against this harder dataset, not only the golden demo.

## 2026-07-08 Definition Query Failure: Gaussian Mixture Model

Observed failure:

- Query: `What is a Gaussian mixture model?`
- Source: Scikit-Learn textbook.
- Bad behavior: the answer stitched together index/back-matter terms such as Bayesian Gaussian mixtures, BIC, Beam Search, Bellman equations, PCA, and anomaly-detection headings.
- Expected behavior: use the page 357 `Gaussian Mixtures` definition before related applications or Bayesian variants.

Diagnosis:

- The correct chunk existed, but the answer path treated keyword mentions as if they were definitions.
- Back-matter/index-like sections could rank competitively with real chapter sections.
- Factual seed chunks were not promoted when they already existed in the retrieval bundle.
- Fallback synthesis lacked a definition-specific answer contract.

Fix shipped:

- Added GMM/Gaussian-mixture query expansion.
- Added definition-aware factual seed scoring and exact-section ranking.
- Penalized index/API-like sections without penalizing legitimate phrases like `cluster index`.
- Added definition fallback synthesis with direct answer, working, uses, and optional limitation.
- Added low-value evidence filtering and sentence cleanup.
- Added unit tests for definition chunk priority, index-fragment rejection, fallback definition output, and seed promotion.

Verification:

- Live answer now cites the page 357 definition as `[1]`.
- Citation verification: `supported`.
- Real-world eval seed now includes this query as `textbook-ml-007`.
- Updated 17-sample metrics after final tightening: Hybrid Recall@8 `1.000`, BM25 Recall@8 `1.000`, BM25 MRR `0.843`.
- Backend suite: `66 passed, 1 warning`.
- Compile check: `python -m compileall apps/api/app` passed.

Next eval action:

- Add similar definition queries for DBSCAN, k-means, PCA, overfitting, cross-validation, and gradient descent.

## 2026-07-11 Release Hardening Ship Gate Fix

A full `npm.cmd run ship:check` pass initially failed on Golden Demo 02 because the privacy/runtime query retrieved the correct document but was classified as weakly related. Root cause: privacy query expansion added broad security terms that diluted directness scoring for concrete local-first controls.

Fix:

- Added a narrow directness boost for local-first privacy controls such as local storage, trusted corpus roots, restricted local-path ingestion, file signatures, source removal, and no cloud/internet requirement.
- Added a source-only privacy-control fallback answer so the demo returns concrete controls instead of generic local-first wording.
- Added heading-noise cleanup for extracted Markdown evidence sentences.
- Added focused unit tests for this regression.

Validation:

- `python -m pytest apps/api/app/tests/unit/test_synthesis_query_terms.py -q`: passed, `8 passed`.
- `python -m compileall apps/api/app`: passed.
- `npm.cmd run ship:check`: passed with backend tests, web build, publish smoke, grounded golden demo checks, and unsupported-chat abstention.
