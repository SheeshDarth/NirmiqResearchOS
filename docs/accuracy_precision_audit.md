# NIRMIQ Accuracy, Precision, and Hallucination Audit

Last updated: 2026-06-06

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

### 4. Query Intent Router Needs Continued Tuning

The deterministic V3.1 router now classifies summary, factual lookup, compare, deep research, paper draft, exam, general chat, and unclear prompts.

Remaining gap:

- The router is intentionally lexical. It should be evaluated against a labeled NIRMIQ dataset before adding more branches.

### 5. Summary Cache Needs UX Observation

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
