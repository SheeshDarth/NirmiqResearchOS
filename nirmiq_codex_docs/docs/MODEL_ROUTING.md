# Model Routing — NIRMIQ ResearchOS

## Goal

Use the smallest effective model for each task.

Avoid unnecessary VRAM pressure.

---

## Local Model Roles

| Task | Model |
|---|---|
| Embedding | nomic-embed-text |
| General academic answer | Phi-3 Mini |
| Coding-heavy answer | DeepSeek Coder 6.7B |
| Reranking | bge-reranker-base |
| OCR | Tesseract |

---

## Routing Policy

### General Study Query

Use:
- hybrid retrieval
- Phi-3 Mini generation

---

### Coding Query

Use:
- hybrid retrieval
- DeepSeek Coder generation only if needed

---

### Summary Query

Use:
- Phi-3 Mini
- compressed context

---

### Exam Answer

Use:
- precision retrieval profile
- structured answer prompt
- strict citation enforcement

---

## VRAM Rules

Do not co-run:
- reranker on GPU
- large generator on GPU

Default:
- keep reranker CPU-first
- generator local via Ollama
- embeddings batched

---

## Future

ModelRouter may later support:
- cloud fallback
- Proxima evaluation routing
- device-based profiles

Not required for MVP.
