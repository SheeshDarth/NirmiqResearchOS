# Retrieval Guidelines — NIRMIQ ResearchOS

## Goal

Provide accurate, citation-backed answers from uploaded documents.

Retrieval quality is the core product advantage.

---

## Mandatory Retrieval Stack

Use:
- BM25 lexical retrieval
- Chroma vector retrieval
- Reciprocal Rank Fusion
- Reranking
- Context compression
- Citation mapping

Never rely only on vector search.

---

## Retrieval Flow

```text
Query
  ↓
Normalize
  ↓
BM25 top-K
  ↓
Vector top-K
  ↓
RRF fusion
  ↓
Rerank top-N
  ↓
Deduplicate
  ↓
Pack context
  ↓
Generate cited answer
```

---

## Retrieval Profiles

### FAST

Use when:
- low latency needed
- small documents
- quick revision

Settings:
- lower top-K
- minimal rerank
- smaller context

---

### BALANCED

Default.

Use when:
- normal study chat
- exam preparation
- medium documents

Settings:
- moderate top-K
- rerank enabled
- citation diversity

---

### PRECISION

Use when:
- answer must be highly grounded
- multiple documents involved
- research comparison requested

Settings:
- higher top-K
- stronger rerank
- larger context
- stricter abstention

---

## Citation Rules

Every answer must include:
- document title
- page number when available
- chunk reference
- supporting snippet if debug enabled

If citation cannot be mapped:
- do not cite fake source
- lower confidence
- abstain if needed

---

## Abstention Rules

Abstain when:
- retrieved chunks are irrelevant
- citation anchors missing
- retrieval scores too low
- context contradicts itself
- answer requires outside knowledge

Default abstention:

> I do not have enough evidence in the uploaded documents to answer this reliably.

---

## Context Packing Rules

Prioritize:
1. high rerank score
2. citation diversity
3. document diversity
4. chunk adjacency
5. low duplication

Avoid:
- repeated chunks
- irrelevant metadata
- excessive long context
- dumping entire pages

---

## Evaluation Metrics

Track:
- Recall@K
- MRR
- Citation Coverage
- Context Precision
- Grounding Strength
- Latency
- Token Budget
