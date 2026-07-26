# Hard-Document Offline Evaluation

Last updated: 2026-07-26

## Purpose

This gate verifies that NIRMIQ can ingest and answer from file structures that are harder than a clean text PDF while remaining fully local and low-memory.

It is intentionally separate from the 40-case academic answer benchmark. The 40-case set tests broader query behavior; this suite tests difficult file handling plus generic formula/table reasoning.

## Coverage

`scripts/generate_hard_document_fixtures.py` creates reproducible local fixtures under `temp/hard-document-fixtures`:

- A four-page textbook-like PDF with a definition, formula, table, and embedded feedback-chain diagram.
- A two-page raster-only scanned PDF with a definition and ordered calibration procedure.
- A handwriting-style image note with preparation and correction instructions.

`data/processed/eval/hard_document_qa.jsonl` contains nine labels:

- Definition.
- Equation/calculation.
- Table comparison.
- Diagram/caption lookup.
- Two scanned-PDF questions.
- Two handwriting questions.
- One unsupported question that must abstain.

The fixtures contain original synthetic text and images. No private or copyrighted textbook is committed.

## Requirements

- Python backend dependencies, including `apps/api[ocr]`.
- A working Tesseract executable.
- Windows: the adapter discovers `C:\Program Files\Tesseract-OCR\tesseract.exe` automatically.
- Other systems: place `tesseract` on PATH or set `TESSERACT_CMD` to the executable.

## Run

```powershell
cd C:\Nirmiq-researchOS
npm.cmd run eval:hard-docs
```

The script deletes only its isolated `temp/hard-document-eval` runtime, regenerates fixtures, ingests through the production services, runs full `POST /query` orchestration in BM25 mode, verifies the stored text and extracted diagram, then publishes canonical JSON only if every gate passes.

Fixture generation suppresses fresh PDF identifiers so repeated runs are byte-stable. The generated manifest and canonical report include SHA-256 fingerprints for all four assets.

## Offline Configuration

- Ollama generation: disabled.
- Ollama embeddings: disabled.
- Ollama reranker: disabled.
- Vector retrieval: disabled.
- Retrieval: BM25.
- Low-memory mode: enabled.
- OCR: local Tesseract.

## Current Result

| Samples | MRR | Recall@3 | Recall@8 | Expected citation coverage | Quality pass | Faithfulness | Answerability |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.978 | 1.000 |

Pipeline checks also pass for scan OCR, handwriting OCR, equation indexing, table indexing, embedded-diagram extraction, and unsupported-query abstention.

The existing 40-case academic benchmark was rerun after these changes and remained `40/40`, with MRR `0.934`, Recall@8 `1.000`, expected citation coverage `1.000`, faithfulness `0.995`, and answerability correctness `1.000`.

## Canonical Artifacts

- Dataset: `data/processed/eval/hard_document_qa.jsonl`.
- Metrics: `data/processed/eval/hard_document_metrics.json`.
- Pipeline report: `data/processed/eval/hard_document_pipeline_report.json`.
- Failure records: `data/processed/eval/hard_document_failures.jsonl`.

The pipeline report also records Python, PyMuPDF, Pillow, pytesseract, Tesseract, and installed OCR-language versions. GitHub Actions pins Tesseract `5.5.0.20241111` and retains the report, metrics, failures, and manifest for 30 days under the evaluated commit SHA.

An empty failure file means this specific gate passed. It does not mean every future document is solved.

## Acceptance Gates

- Recall@8 at least `0.95`.
- Expected citation coverage at least `0.95`.
- Answer-quality pass at least `0.88`.
- Answerability correctness exactly `1.00`.
- Every OCR, indexing, and diagram check must pass.

## Clean-Runner Evidence

- Candidate commit: `7ac3d230a618a214e3c19322b08c73ac7523507b`.
- GitHub Actions run: `29698536495`.
- Result: passed on Windows in `2m22s`.
- Run URL: `https://github.com/SheeshDarth/NirmiqResearchOS/actions/runs/29698536495`.
- The run installed pinned Tesseract, executed the backend and hard-document gates, retained the evidence artifact, passed release doctor and the production web build, and validated Docker Compose.
- Windows is the clean-runner baseline for this job; native Linux validation is tracked separately.
- The final five-advisor LLM Council approved closure with no in-scope blocker.
- Keep this suite frozen as a regression gate. Its implementation-authored fixtures do not establish arbitrary-document generalization; independently sourced documents remain a separate hardening task.

## Limitations And Next Work

- Generated handwriting is cleaner than many real notes.
- The scan set does not yet cover skew, blur, mixed languages, marginalia, or multi-column pages.
- Formula coverage is textual; mathematical layout understanding is not yet a symbolic math engine.
- Diagram coverage verifies extraction and caption-grounded lookup, not computer-vision interpretation.
- Independent real textbooks, scans, and user questions are still required before broad accuracy claims.
- Sprint Five adds a separate local-only unseen scan holdout for prompt-engineering and website-building PDFs; see [`next_version_sprint_five_unseen_ocr_sources.md`](next_version_sprint_five_unseen_ocr_sources.md). It improves confidence on two real scan sources but does not replace this reproducible gate.
