# NIRMIQ Accuracy, Precision, and Hallucination Audit

Last updated: 2026-06-10

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
| Hybrid | 16 | 0.490 | 0.563 | 0.688 | 0.750 | 0.750 |
| BM25 | 16 | 0.578 | 0.625 | 0.688 | 0.750 | 0.750 |

Interpretation:

- This is the honest baseline for real local academic material.
- The project is demo-ready, but not yet production-perfect for arbitrary documents.
- BM25 currently wins on this seed because exact academic phrase labels dominate and Ollama embeddings remain off in the low-memory profile.

Next accuracy sprint:

- Add at least 40 more real labels.
- Separate parsing failures from retrieval-ranking failures.
- Tune hybrid retrieval only against this harder dataset, not only the golden demo.
