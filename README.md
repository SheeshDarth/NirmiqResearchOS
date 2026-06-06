# NIRMIQ Academic Intelligence System

![NIRMIQ Academic Intelligence System mark](apps/web/public/brand/nirmiq-ais-mark.svg)

Offline-first adaptive academic intelligence system focused on grounded retrieval and low-VRAM local inference.

Product name: **NIRMIQ Academic Intelligence System**.

## Current Status

Phase 1 is complete, the student chat MVP is active, and the Version 2.0 Academic Intelligence System Workspace is live:
- repository skeleton established
- FastAPI backend layered by routers/services/adapters/domain
- SQLite schema bootstrap wired
- ingestion/query/memory API contracts scaffolded, including session timeline history and document drilldown
- functional local ingestion -> chunk indexing -> lexical retrieval loop added
- hybrid retrieval baseline added (BM25 + optional Chroma vector + RRF + rerank)
- retrieval and synthesis tuning centralized in `RetrievalPolicy`
- custom Next.js study workspace added with Study Thread, Study Material, Evidence Trail, Study Context, Compare, and Eval panels
- document drilldown, citation jump links, and query/session comparison are now in the workspace
- Phase 1 foundation is complete and Phase 2 workflow polish is complete
- Phase 3 quality pass is active with citation excerpts, source scores, answer diff visibility, and retrieval diversity tuning
- Phase 4 grounding pass is active with score-aware synthesis metadata and a compact grounding summary badge in the query panel
- retrieval profiles are available: `fast`, `balanced`, `precision`
- study modes are available: `research`, `summary`, `deep_research`, `general_chat`, `research_paper`, `exam_answer`, `revision_notes`, `important_questions`, `compare_concepts`, `study_guide`
- ChatGPT-like upload is available from the composer for PDFs, text, Markdown, and image files
- broad PDF summary prompts such as "Explain the PDF" are routed through grounded summary mode
- parsed PDF pages are cached by content hash for faster repeated local reindexing
- tests use isolated temporary SQLite/Chroma paths so local user documents are not polluted by fixtures

## Quick Start (Scaffold)

1. Backend:
   - `cd apps/api`
   - `python -m pip install -e .`
   - optional vector retrieval: `python -m pip install -e .[vector]`
   - optional OCR fallback: `python -m pip install -e .[ocr]`
   - `python -m uvicorn app.main:app --reload`
2. Frontend:
   - `cd apps/web`
   - `npm install`
   - `npm run dev`
   - Open `http://127.0.0.1:3002`

Current local review URL:
- `http://127.0.0.1:3002`

## Local Tests

- `cd apps/api`
- `python -m pytest app/tests/unit/test_health_contract.py app/tests/integration -q`

## Retrieval Evaluation

- Label file format: `data/processed/eval/qa_labels.jsonl`
- Example template: `data/processed/eval/qa_labels.example.jsonl`
- Run:
  - `python scripts/eval_retrieval.py --dataset data/processed/eval/qa_labels.jsonl --k 3 5 8 --modes hybrid bm25 vector`
  - or `scripts/eval_retrieval.ps1`
  - use `scripts/eval_grounded.ps1` for full-query grounding metrics
- Paste the JSON output into the local console's Eval report viewer to inspect metrics without leaving the app.

## Query Retrieval Modes

- `POST /query` supports `retrieval_mode`:
  - `hybrid` (default)
  - `bm25`
  - `vector`
- Use this for quick A/B checks on grounded response behavior.

## Retrieval Tuning

- `RETRIEVAL_MAX_CONTEXT_TOKENS` controls the synthesis context budget.
- `RETRIEVAL_MIN_GROUNDING_SCORE` controls when synthesis will abstain.

## Ingestion Observability

- `GET /ingest/{document_id}` for current status and latest job.
- `GET /ingest/{document_id}/jobs` for full ingestion job history.

## Ollama Toggle Notes

- Generation path defaults to `USE_OLLAMA_GENERATION=true` with fallback when Ollama is offline.
- Embedding path defaults to `USE_OLLAMA_EMBEDDINGS=true` with automatic fallback to deterministic hash embeddings.
- Reranker defaults to `USE_OLLAMA_RERANKER=false` to keep latency low; enable when you want model-based reranking.
- OCR fallback auto-triggers on low-text pages when Tesseract + OCR deps are available.

## Architecture

See [docs/phase1_foundational_architecture.md](docs/phase1_foundational_architecture.md).

## NIRMIQ Ecosystem

See [docs/nirmiq_ecosystem.md](docs/nirmiq_ecosystem.md) for how this standalone Academic Intelligence System fits under the broader NIRMIQ umbrella.

## Repository Rename Note

Target GitHub repository name: `NirmiqAcademicIntelligenceSystem`.

Current remote may still point to the previous repository URL until GitHub repository settings are renamed manually or GitHub CLI is available.

## Portfolio Impact Plan

See [docs/internship_impact_plan.md](docs/internship_impact_plan.md) for the project positioning, technical differentiators, demo script, metrics, and roadmap.
