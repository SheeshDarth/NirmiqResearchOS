# NIRMIQ Academic Intelligence System: Internship Impact Plan

Last updated: 2026-06-06

## Positioning

NIRMIQ is not a generic AI chatbot. It is a local-first academic intelligence workspace for students and early researchers who need source-grounded answers from their own PDFs, notes, question banks, diagrams, and research papers.

The project should be presented as:

> A privacy-preserving local RAG system optimized for academic workflows: document understanding, citation-backed synthesis, engineering paper drafting, exam preparation, and retrieval evaluation on constrained consumer hardware.

## Why This Is Internship-Worthy

Hiring teams should be able to see backend depth, retrieval thinking, product judgment, and local systems awareness in one project.

The strongest signals are:

- End-to-end system ownership: Next.js PWA, FastAPI, SQLite, Chroma, retrieval services, synthesis orchestration, and tests.
- Real retrieval engineering: BM25, optional vector search, Reciprocal Rank Fusion, citation packing, grounding score, document-scoped retrieval, and evaluation scripts.
- Local-first constraints: offline usage, RTX 4050-friendly model choices, optional Ollama, fallback synthesis, and low-dependency design.
- Academic product specificity: summaries, paper lab, exam lab, question banks, diagrams, citations, and evidence drilldown.
- Reliability mindset: clear abstention behavior, debug metadata, regression tests, upload tests, and context documentation.

## Differentiator

Most portfolio RAG apps stop at "upload PDF and ask questions." NIRMIQ should go further by proving:

- Can the system explain why it answered?
- Can it show exact evidence?
- Can it refuse when evidence is weak?
- Can it help write paper sections without inventing citations?
- Can it support exam-ready answers from the exact uploaded notes?
- Can it run locally on realistic student hardware?
- Can retrieval quality be measured and improved?

## Current Capability Baseline

- Upload PDF, text, Markdown, and image files.
- Parse PDFs with PyMuPDF.
- Optional OCR path for images and scanned PDFs.
- Store document metadata, chunks, sessions, memory, exam profiles, question banks, and diagram metadata in SQLite.
- Use BM25 plus optional Chroma vector retrieval.
- Fuse retrieval candidates with RRF.
- Generate grounded responses with citations.
- Summarize broad PDF/document prompts.
- Show evidence cards and answer citations in the UI.
- Support Research, Chat, Paper Lab, and Exam Lab workspaces.
- Run local fallback synthesis when Ollama is unavailable.
- Cache parsed PDF pages by content hash for faster repeated reindexing.
- Cache selected-document summaries by content hash.
- Route query intent deterministically.
- Generate Paper Lab metadata for outline, related-work matrix, citation clusters, and Markdown draft export.

## Performance Strategy

Priority is not raw model size. Priority is useful grounded answers on a laptop.

Near-term optimizations:

- Cache parsed PDF pages by content hash. Completed.
- Cache document-level summaries after first generation. Completed for selected-document summaries.
- Add chunk quality scoring to down-rank boilerplate, headers, page numbers, broken glyphs, and references-only chunks. Completed.
- Add query intent detection before retrieval: summary, compare, exam, paper, factual lookup, general chat. Completed.
- Use lower retrieval budgets for fast chat and higher budgets only for deep research/paper mode.
- Add source diversity rules for Paper Lab to avoid over-citing one page or section.
- Add response streaming only after generation reliability is stable.

## Retrieval Quality Strategy

Do not add TigerGraph or a full graph database yet. That would add operational weight before the baseline is fully measured.

Preferred path:

1. Chunk quality scoring.
2. Query intent routing.
3. Document summary cache.
4. Concept extraction into SQLite tables.
5. GraphRAG-lite expansion from SQLite concepts.
6. Citation verification against retrieved chunks.
7. Optional cross-encoder reranker only when VRAM allows.

This gives most of the useful graph behavior while preserving offline simplicity.

## Product Roadmap

### Sprint 1: Trust And Usability

- Fix upload, scroll, PDF summary, and source selection. Mostly completed.
- Add "selected source" visibility near the composer.
- Add one-click "Summarize selected PDF."
- Add "copy answer with citations."
- Add local data purge for uploaded file bytes and extracted diagram files.

### Sprint 2: Retrieval Quality

- Add chunk quality scoring.
- Add document summary cache.
- Add citation verification pass.
- Add evaluation labels for engineering PDFs, notes, and question banks.
- Expose retrieval metrics in a clean developer panel.

### Sprint 3: Paper Lab

- Add paper outline builder. Initial deterministic version completed.
- Add related-work matrix. Initial V4 foundation completed.
- Add citation clustering. Initial V4 foundation completed.
- Add thesis/methodology/limitations draft modes.
- Add export to Markdown first, then DOCX/LaTeX later. Markdown copy export completed.

### Sprint 4: Exam Lab

- Improve question-bank import.
- Add answer-format templates by marks.
- Add diagram-aware study guides.
- Add important-question ranking from notes and question bank overlap.

### Sprint 5: Portfolio Packaging

- Add demo dataset and scripted walkthrough.
- Add architecture diagrams and performance screenshots.
- Add retrieval evaluation report.
- Add a short technical case study: problem, design decisions, tradeoffs, metrics, limitations.

## Metrics To Show

- PDF ingest time before/after parse cache.
- Retrieval hit rate on local labeled questions.
- Citation coverage percentage.
- Abstention correctness for unrelated queries.
- Average response latency by mode.
- Memory/storage footprint.
- Ollama fallback behavior when local model is unavailable.

## Demo Script

1. Upload a research paper PDF.
2. Ask "Explain the PDF" and show grounded summary with citations.
3. Click a citation and inspect the source chunk.
4. Switch to Paper Lab and draft a related-work section.
5. Copy the Paper Lab Markdown draft and show outline/matrix/citations.
6. Switch to Exam Lab, import questions, and generate a marks-ready answer.
7. Show retrieval metadata/evaluation output.
8. Disconnect generation or vector dependencies and show graceful local fallback.

## Engineering Principles

- Working software beats theoretical architecture.
- Local-first before cloud.
- SQLite before graph database.
- Measured retrieval before bigger models.
- Citation-backed answers before fluent answers.
- Simple services before deep abstractions.
- RTX 4050 stability before model ambition.
