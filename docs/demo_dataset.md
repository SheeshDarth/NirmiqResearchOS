# Demo Academic QA Dataset

This folder contains the lightweight recruiter/demo evaluation set for NIRMIQ ResearchOS.

## Sources

- `data/raw/demo_pdfs/nirmiq_rag_reference.pdf`
- `data/raw/demo_pdfs/nirmiq_exam_reference.pdf`

Both PDFs are original synthetic demo documents created for this repository. They are small enough to index quickly and safe to use in GitHub demos.

## Labels

- `data/processed/eval/demo_academic_qa.jsonl`
- 30 questions total.
- Covers hybrid retrieval, citation behavior, hallucination control, retrieval metrics, exam answer formats, study guides, diagram handling, and offline privacy.
- Includes local trust controls such as delete, export, and clear indexed material.

Each row includes:

- `id`
- `source_file`
- `category`
- `query`
- `expected_answer`
- `expected_phrases`

The evaluation script supports phrase-level evidence matching so labels do not depend on random document IDs generated during ingestion.

## How To Use

Start the app and ingest the demo PDFs:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\start_local.ps1 -OpenBrowser
.\scripts\load_demo_dataset.ps1
```

Then run retrieval evaluation:

```powershell
python scripts/eval_retrieval.py --dataset data/processed/eval/demo_academic_qa.jsonl --k 3 5 8 --modes hybrid bm25 --output data/processed/eval/demo_retrieval_metrics.json
```

For answer-level smoke metrics, add `--full-query` after the PDFs are indexed.
