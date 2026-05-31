# NIRMIQ Accuracy, Precision, and Hallucination Audit

Last updated: 2026-05-31

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

### 2. Chunk Quality Is Not Scored Yet

PDF parsing can produce headers, footers, broken glyphs, repeated boilerplate, references, or malformed chunks.

Recommended next fix:

- Add chunk quality scoring at index time.
- Penalize chunks with high symbol noise, repeated headers, low alphabetic ratio, or mostly references.
- Store `quality_score` in SQLite and use it during retrieval ranking.

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

### 4. No Query Intent Router Beyond Simple Mode Rules

The UI mode helps, but arbitrary prompts still need stronger routing.

Recommended next fix:

- Deterministic intent classifier: summary, factual lookup, compare, paper draft, exam answer, unanswerable/general.
- Route each intent to a retrieval profile, citation policy, and response template.

### 5. No Document Summary Cache Yet

Repeated summaries currently re-run retrieval and synthesis.

Recommended next fix:

- Cache document-level summaries by document id, index version, and summary profile.
- Invalidate on reindex.

### 6. No Citation Coverage Score In UI

Backend now tracks faithfulness metadata, but the user still needs simple visibility.

Recommended next fix:

- Show `Verified`, `Rewritten`, or `Needs review` badge near the answer.
- Keep raw debug metadata hidden unless requested.

### 7. General Chat Needs Clearer Boundaries

Current Chat should remain local-first and abstain when there is no evidence.

Recommended next fix:

- Add explicit `local_chat` versus `connected_chat` state before any API-key/cloud mode.
- Show “document-grounded” or “needs connected model/context” status.

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

## Next Implementation Order

1. Add chunk quality scoring and retrieval ranking penalty.
2. Add labeled evaluation dataset for NIRMIQ use cases.
3. Add document summary cache.
4. Add deterministic query intent router.
5. Add citation coverage score.
6. Add optional semantic entailment verifier only when local model latency is acceptable.
