# Retrieval Evaluation Results

Date: 2026-06-14

Dataset: `data/processed/eval/demo_academic_qa.jsonl`

Sources:

- `data/raw/demo_pdfs/nirmiq_rag_reference.pdf`
- `data/raw/demo_pdfs/nirmiq_exam_reference.pdf`

Scope:

- 30 sample questions.
- Phrase-level expected evidence labels.
- Covers RAG retrieval, citation expectations, hallucination control, retrieval metrics, exam answer formatting, study-guide behavior, diagram policy, offline privacy, and local data controls.

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
| Hybrid | 30 | 0.967 | 1.00 | 1.00 | 1.00 | 0.847 | 0.840 | 0.844 | 1.00 |
| BM25 | 30 | 0.839 | 1.00 | 1.00 | 1.00 | 0.749 | 0.743 | 0.743 | 1.00 |

Interpretation:

- Hybrid retrieval ranked the first relevant evidence earlier than BM25 on this expanded dataset.
- Both modes found expected evidence within the top 3 chunks for every sample question.
- Phrase-level citation expected coverage is 1.0, meaning at least one retrieved/cited source matched the expected evidence phrase for every query.

Limitations:

- This is a compact recruiter/demo dataset, not a full benchmark.
- The PDFs are synthetic and intentionally compact so reviewers can index them quickly.
- A real-world seed set now exists, but it is still small and should grow before claims are made about broad academic accuracy.

## Real-World Academic Seed Results

Date: 2026-06-20

Dataset: `data/processed/eval/real_world_academic_seed.jsonl`

Sources:

- `data/raw/attention_is_all_you_need.pdf`
- `data/raw/uploads/Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-TensorFlow-3rd-Ed.---Annot-5b287bd745.pdf`
- `data/raw/uploads/mod-5-gen-ai-708567b729.pdf`

Note: these source PDFs are intentionally local/untracked because public repositories should not commit private or copyright-sensitive academic material. The labels and metrics are committed; replace the `source_file` paths with local documents to reproduce or expand the benchmark.

Scope:

- 16 phrase-labeled questions.
- Covers a real research paper, a full ML textbook PDF, and local GenAI notes.
- Uses `source_file` labels plus `--auto-ingest-sources`, so document IDs do not need to be manually copied.

Command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\eval_real_world.ps1
```

Results:

| Mode | Samples | MRR | Recall@3 | Recall@5 | Recall@8 | nDCG@3 | nDCG@5 | nDCG@8 | Citation Expected Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 16 | 0.490 | 0.563 | 0.688 | 0.750 | 0.285 | 0.343 | 0.366 | 0.750 |
| BM25 | 16 | 0.578 | 0.625 | 0.688 | 0.750 | 0.352 | 0.395 | 0.417 | 0.750 |

Interpretation:

- This result is intentionally more realistic and less polished than the golden demo score.
- BM25 slightly beats hybrid on this seed set because Ollama embeddings are disabled in the low-memory/offline profile and exact academic terms dominate these labels.
- Recall@8 and citation expected coverage at `0.75` show the current system is useful, but not yet "production perfect" for arbitrary academic material.

Next tuning targets:

- Add 40-80 more labels across textbooks, lecture notes, scanned PDFs, and research papers.
- Track which questions fail because of parsing noise versus retrieval ranking.
- Tune summary/factual expansion and source diversity using this harder set instead of only the golden demo.

## Metrics Definitions

- Recall@K: whether expected evidence appears within the top K retrieved chunks.
- MRR: rewards placing the first expected evidence chunk earlier.
- nDCG@K: rewards ranking multiple expected evidence phrases near the top.
- Citation expected coverage: whether returned evidence/citations contain expected support.
