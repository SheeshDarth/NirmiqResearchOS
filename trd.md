# NIRMIQ Technical Requirements Document

Last updated: 2026-05-30

## Project

NIRMIQ Academic Intelligence is an offline-first academic workspace for grounded document research, general chat, paper drafting, and exam preparation. The implementation target is a solo-developer MVP that runs well on a local laptop with RTX 4050-class constraints.

## Runtime Requirements

- Frontend: Next.js PWA at `apps/web`.
- Backend: FastAPI at `apps/api`.
- Storage: SQLite for metadata, memory, sessions, exam artifacts, and document chunks.
- Vector storage: ChromaDB optional path for semantic retrieval.
- Retrieval: BM25, optional vector retrieval, Reciprocal Rank Fusion, reranking hooks, citation packing.
- Parsing: PyMuPDF for PDFs, Tesseract OCR as optional fallback for low-text/scanned pages and images.
- Local inference: Ollama generation and embeddings when available, deterministic/fallback paths when unavailable.
- Hardware priority: low VRAM, graceful fallback, fast local demos.

## Functional Requirements

- Upload PDFs, text, Markdown, and images through a ChatGPT-like composer.
- Ingest uploaded or local-path documents into raw storage, parsed pages, chunks, indexes, and document metadata.
- Ask grounded questions against selected documents.
- Summarize a whole PDF even when the prompt is broad.
- Show citations only when useful, with source page/chunk detail.
- Support four workspace modes: Research, Chat, Paper Lab, Exam Lab.
- Provide a local login/profile gate using name plus email or phone.
- Let users minimize the composer/search box to read long responses.
- Let Exam Lab generate printable custom PDF study material from grounded answers.
- Keep session continuity through SQLite-backed message history and memory snapshots.

## Non-Functional Requirements

- Offline-first: core document Q&A should work without internet.
- Privacy-first: documents remain local by default.
- Maintainable: prefer fewer services and explicit orchestration.
- Stable: backend tests must isolate temp SQLite/Chroma/cache paths.
- Grounded: response generation must cite retrieved chunks or abstain when context is weak.
- Fast enough for demos: repeated PDF parsing should use content-hash page cache.

## API Requirements

- `GET /health`: service health and dependency status.
- `POST /ingest`: ingest document by source path.
- `POST /ingest/upload`: upload file and ingest it.
- `GET /ingest/{document_id}`: document status and latest job.
- `GET /ingest/{document_id}/jobs`: ingestion job history.
- `GET /documents`: indexed document library.
- `GET /documents/{document_id}/chunks`: source drilldown.
- `POST /query`: grounded query flow with retrieval mode/profile/mode/session.
- `GET /memory/{session_id}`: session memory snapshot.
- Exam routes for profiles, question banks, and study/exam artifacts.

## Retrieval Requirements

- Use hybrid retrieval by default.
- Support `bm25`, `vector`, and `hybrid` modes.
- Use retrieval profiles: `fast`, `balanced`, `precision`.
- Route broad overview prompts to summary behavior.
- Use document-scoped fallback when a selected document exists and broad prompts retrieve low lexical scores.
- Include debug metadata for evaluation and development.
- Avoid graph databases in V3 unless the measured baseline proves SQLite concept graph expansion is insufficient.

## Security And Privacy Requirements

- Local profile login is not real authentication yet; it is a UX gate and personalization layer.
- Future hosted auth must follow OWASP guidance: generic errors, safe session handling, rate limits, and secure reset/verification flows.
- Uploaded documents must stay local unless the user explicitly enables an external provider.
- Any future API-key mode must make cloud usage obvious before sending content.
- Provide local data purge/export controls before broader beta use.

## V3 Acceptance Criteria

- Landing screen explains NIRMIQ Academic Intelligence clearly.
- Login accepts display name plus email or phone.
- Workspace section choice is clear: Research, Chat, Paper Lab, Exam Lab.
- Composer adapts placeholder/action to the current section.
- Composer can be minimized and restored.
- Research summary works on an indexed PDF.
- Exam Lab exposes custom PDF generation from the current grounded answer.
- Web build passes.
- Backend unit/integration tests pass.
- `context.md` and handoff docs are updated after the work.

