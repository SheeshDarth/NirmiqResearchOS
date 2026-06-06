# Evaluation Guidelines — NIRMIQ Academic Intelligence System

## Goal

Make retrieval and grounding measurable.

NIRMIQ must prove it reduces hallucinations.

---

## Evaluation Dataset

Create:

```text
data/eval/
├─ documents/
├─ queries.jsonl
├─ expected_citations.jsonl
└─ results/
```

---

## Query Record Format

```json
{
  "id": "q001",
  "question": "Explain deadlock prevention.",
  "document_ids": ["os_notes_unit3"],
  "expected_pages": [12, 13],
  "expected_keywords": ["mutual exclusion", "hold and wait", "circular wait"],
  "answer_type": "exam"
}
```

---

## Metrics

### Recall@K

Checks whether expected source appears in top K.

### MRR

Measures ranking quality.

### Citation Coverage

Checks whether final answer cites retrieved evidence.

### Grounding Strength

Heuristic from:
- retrieval scores
- rerank scores
- citation coverage
- answer-source overlap

### Hallucination Flag

Detects:
- uncited claims
- unsupported named concepts
- answer without source overlap

---

## Required Evaluation Scripts

```text
evaluation/
├─ retrieval_eval.py
├─ citation_eval.py
├─ grounding_eval.py
├─ latency_eval.py
└─ run_all.py
```

---

## MVP Evaluation Target

Before UI polish:
- run at least 30 queries
- compare vector-only vs hybrid
- measure citation coverage
- measure latency

---

## Portfolio Value

Show benchmark table in README:
- Vector-only baseline
- Hybrid retrieval
- Hybrid + rerank
- Hybrid + rerank + compression

This proves engineering depth.
