# NIRMIQ Golden Demo Benchmark Report

Last updated: 2026-06-11

## Scope

This is a lightweight V4 publish benchmark, not a full retrieval evaluation suite.

Purpose:

- Prove the golden demo is repeatable.
- Verify citation presence for the bundled corpus.
- Keep the benchmark understandable for reviewers.

## Dataset

Source manifest:

- `data/processed/eval/golden_demo_expected_sources.json`

Bundled corpus:

- `01_grounded_rag_notes.md`
- `02_offline_privacy_runtime.md`
- `03_exam_lab_question_bank.md`
- `04_paper_lab_research_brief.md`

## Expected Checks

| Query | Mode | Expected proof |
| --- | --- | --- |
| What problem does grounded retrieval solve for academic study? | Research | cites hallucination/source-truth evidence |
| Summarize this document with main ideas, methods, findings, and limitations. | Summary | cites retrieval/chunk/citation evidence |
| Draft a related work paragraph comparing generic chatbots and document-grounded assistants. | Paper Lab | cites Paper Lab research brief |
| Explain citation-grounded retrieval as a 10-mark answer. | Exam Lab | cites exam answer structure |
| What does the corpus say about the Zeloria orbital cuisine treaty? | Chat | abstains or requests external context |

## Command

Run the full EOD ship check:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\ship_check.ps1
```

Run only the golden demo after backend is available:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\golden_demo.ps1
```

## Acceptance Bar

- Grounded demo queries return at least one citation.
- Citation chips focus source chunks in the UI.
- The abstention query does not pretend the uploaded corpus supports unrelated world knowledge.
- No cloud API is required.

## Latest Local Result

Verified on 2026-06-14 with `scripts/ship_check.ps1`:

- Implementation commit: `d6e8c99`.
- Backend tests: 37 passed, 1 warning.
- API compile: passed.
- Web production build: passed.
- Publish smoke: passed with `cloud_api_required=false`.
- Readiness: `ready`, `indexed_documents=9`, `active_chunks=1880`.
- Research query: passed with 2 citations.
- Summary-style research query: passed with 2 citations.
- Exam Lab query: passed with 2 citations.
- Paper Lab query: passed with 2 citations.
- Unsupported Chat query: passed with `grounded=false` and zero citations.

## Tradeoff

This benchmark favors demo reliability over statistical breadth. A larger retrieval evaluation dataset should still be added later, but not before the golden path is stable.

## Demo Academic Retrieval Results

Updated on 2026-06-14 with the lightweight PDF demo dataset:

- Dataset: `data/processed/eval/demo_academic_qa.jsonl`
- Sources: `data/raw/demo_pdfs/nirmiq_rag_reference.pdf`, `data/raw/demo_pdfs/nirmiq_exam_reference.pdf`
- Samples: 30 phrase-labeled QA items

| Mode | MRR | Recall@3 | Recall@5 | Recall@8 | nDCG@3 | Citation expected coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 0.967 | 1.00 | 1.00 | 1.00 | 0.847 | 1.00 |
| BM25 | 0.839 | 1.00 | 1.00 | 1.00 | 0.749 | 1.00 |

Command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\load_demo_dataset.ps1 -ForceReindex
.\scripts\eval_demo_dataset.ps1
```

Detailed report: `docs/retrieval_eval_results.md`.

## Real-World Seed Benchmark

Updated on 2026-06-20 with actual local academic material:

- Dataset: `data/processed/eval/real_world_academic_seed.jsonl`
- Sources:
  - `data/raw/attention_is_all_you_need.pdf`
  - `data/raw/uploads/Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-TensorFlow-3rd-Ed.---Annot-5b287bd745.pdf`
  - `data/raw/uploads/mod-5-gen-ai-708567b729.pdf`
- Samples: 16 phrase-labeled QA items

The source PDFs are local/untracked by design. Keep copyright-sensitive textbooks and personal notes out of Git; commit labels and metrics only.

| Mode | MRR | Recall@3 | Recall@5 | Recall@8 | Citation expected coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 0.490 | 0.563 | 0.688 | 0.750 | 0.750 |
| BM25 | 0.578 | 0.625 | 0.688 | 0.750 | 0.750 |

Command:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\eval_real_world.ps1
```

Interpretation:

- The golden demo remains the reviewer proof path.
- The real-world seed is the accuracy-improvement benchmark.
- These numbers are not yet launch-marketing quality; they are useful because they expose where the next retrieval tuning sprint should focus.
