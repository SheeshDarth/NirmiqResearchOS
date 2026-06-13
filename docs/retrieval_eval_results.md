# Retrieval Evaluation Results

Date: 2026-06-13

Dataset: `data/processed/eval/demo_academic_qa.jsonl`

Sources:

- `data/raw/demo_pdfs/nirmiq_rag_reference.pdf`
- `data/raw/demo_pdfs/nirmiq_exam_reference.pdf`

Scope:

- 10 sample questions.
- Phrase-level expected evidence labels.
- Covers RAG retrieval, citation expectations, hallucination control, retrieval metrics, exam answer formatting, study-guide behavior, diagram policy, and offline privacy.

## Latest Local Results

Command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\load_demo_dataset.ps1 -ForceReindex
.\scripts\eval_demo_dataset.ps1
```

Results:

| Mode | Samples | MRR | Recall@3 | Recall@5 | Recall@8 | nDCG@3 | nDCG@5 | nDCG@8 | Citation Expected Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 10 | 0.95 | 1.00 | 1.00 | 1.00 | 0.708 | 0.695 | 0.695 | 1.00 |
| BM25 | 10 | 0.90 | 1.00 | 1.00 | 1.00 | 0.642 | 0.629 | 0.629 | 1.00 |

Interpretation:

- Hybrid retrieval ranked the first relevant evidence slightly earlier than BM25 on this dataset.
- Both modes found expected evidence within the top 3 chunks for every sample question.
- Phrase-level citation expected coverage is 1.0, meaning at least one retrieved/cited source matched the expected evidence phrase for every query.

Limitations:

- This is a small recruiter/demo dataset, not a full benchmark.
- The PDFs are synthetic and intentionally compact so reviewers can index them quickly.
- Next evaluation step: add 20-40 labels from real engineering notes, research papers, and exam-style PDFs.

## Metrics Definitions

- Recall@K: whether expected evidence appears within the top K retrieved chunks.
- MRR: rewards placing the first expected evidence chunk earlier.
- nDCG@K: rewards ranking multiple expected evidence phrases near the top.
- Citation expected coverage: whether returned evidence/citations contain expected support.
