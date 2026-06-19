# NIRMIQ ResearchOS

> Upload. Understand. Verify. Learn.

[![NIRMIQ CI](https://github.com/SheeshDarth/NirmiqResearchOS/actions/workflows/ci.yml/badge.svg?branch=v3-foundation)](https://github.com/SheeshDarth/NirmiqResearchOS/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Local first](https://img.shields.io/badge/local--first-yes-64d8bd.svg)

![NIRMIQ ResearchOS mark](apps/web/public/brand/nirmiq-ais-mark.svg)

**NIRMIQ ResearchOS** is an offline-first academic document intelligence system built for students, researchers, and builders who need reliable answers from their own material.

It is not just a PDF chatbot.

It is a grounded academic knowledge assistant that helps users upload documents, ask questions, prepare for exams, draft research sections, retrieve source-backed answers, and understand complex content without hallucinated responses.

Core product direction: **NIRMIQ ResearchOS is the academic intelligence workspace inside the broader NIRMIQ ecosystem.**

## Why NIRMIQ Exists

Students and early researchers increasingly use AI to understand PDFs, lecture notes, textbooks, slides, lab manuals, previous-year questions, screenshots, and research papers.

Most generic AI tools fail in the exact places academic work needs trust:

- They hallucinate confident answers.
- They lose uploaded document context.
- They hit token limits on long material.
- They provide uncited explanations.
- They struggle with messy PDFs and technical notes.
- They cannot reliably prove where an answer came from.
- They are not optimized for exam preparation or paper writing.

NIRMIQ ResearchOS was created to solve this problem.

The goal is simple:

> Give users accurate, source-grounded answers from their uploaded documents.

## Core Vision

NIRMIQ ResearchOS is a lightweight, offline-first, adaptive academic intelligence system capable of:

- Document understanding.
- Grounded question answering.
- Citation-aware responses.
- Whole-document summarization.
- Exam preparation.
- Research-paper drafting support.
- Multi-document retrieval.
- Contextual session memory.
- Low-hallucination synthesis.
- Local-first AI inference.

## Offline-First Contract

NIRMIQ uses a local FastAPI backend as part of the app runtime. This is **not** a cloud API dependency.

Core behavior is designed to work locally:

- Uploaded documents remain on the user's machine by default.
- The app can run without a ChatGPT/OpenAI-linked account.
- Ollama is optional for local generation.
- Deterministic fallback paths keep the app usable when local models are unavailable.
- Any future connected model/API-key mode must be opt-in and clearly disclose when document content leaves the machine.

## What Makes It Different

Most RAG apps follow a basic flow:

```text
Upload PDF
Chunk text
Embed chunks
Retrieve chunks
Ask LLM
Hope it does not hallucinate
```

NIRMIQ uses a more reliable academic flow:

```text
Upload document
Parse and normalize
Adaptive chunking
Hybrid retrieval
BM25 plus optional vector search
Reciprocal Rank Fusion
Reranking and context packing
Citation mapping
Grounded answer generation
Citation coverage and verification
Student-friendly response
```

The focus is not just answering.

The focus is answering with evidence.

## Current V4 Foundation

Implemented in the current repository:

- Bundled `Load Golden Demo` flow with four local academic Markdown sources.
- Electron desktop shell that starts the local runtime and opens NIRMIQ in a Windows app window.
- Desktop diagnostics menu for runtime status, logs, VS Code, project docs, and data folder access.
- Locked reviewer prompts for Research, Summary, Paper Lab, Exam Lab, and abstention behavior.
- Golden demo smoke script that fails if unsupported chat prompts return grounded answers.
- Local answer export as Markdown with citations.
- Whole-thread Markdown export from local session memory.
- Upload PDFs, text, Markdown, and images.
- Ingest local-path documents from trusted corpus roots.
- Summarize selected PDFs with citations.
- Ask grounded questions against selected sources.
- Inspect evidence chunks, pages, and source details.
- Use four workspaces: Research, Chat, Paper Lab, and Exam Lab.
- Run hybrid retrieval with BM25, optional vector search, RRF, and reranking hooks.
- Use selected-document summary caching keyed by document id, content hash, and summary profile.
- Route query intent deterministically for summary, lookup, compare, deep research, paper, exam, chat, and unclear prompts.
- Show compact trust signals: `Verified`, `Rewritten`, `Needs review`, or `Low citation coverage`.
- Fall back to extractive grounded answers when evidence or citation verification is weak.
- Abstain in Chat when retrieved material is unrelated to the actual question subject.
- Use Paper Lab for citation clusters, related-work matrix, suggested outline, and Markdown draft export.
- Use Exam Lab for marks-oriented answers, study guides, question-bank support, and printable custom PDFs.
- Check local publish readiness through `/health/readiness` and `scripts/publish_smoke.ps1`.
- Run with a low-memory local model profile: bounded Ollama context, bounded prediction length, short keep-alive, and batched embeddings.
- Use Local Data controls to clear current thread memory or clear indexed material while leaving source files on disk.

## What Works Now

- Upload and index PDF, Markdown, text, and image files locally.
- Ask selected-document questions with citations and trust metadata.
- Summarize selected PDFs with summary caching.
- Inspect evidence chunks in the Deep Research panel.
- Run Research, Chat, Paper Lab, and Exam Lab modes from one workspace.
- Export grounded answers/drafts as local Markdown.
- Export the current thread as local Markdown.
- Generate Exam Lab custom PDFs from grounded responses.
- Clear thread memory and indexed material from the UI for privacy/reset demos.
- Run local smoke checks, backend tests, and frontend production build.
- Evaluate retrieval on a bundled 30-question demo dataset.
- Run GitHub CI for backend tests, API compile, frontend build, and Docker Compose validation.
- Run optional Docker dev containers with checked-in API and web Dockerfiles.
- Use `/api/v1/*` routes while preserving the original local API route paths.
- Enforce local request body limits, response compression, and scanner-clean SQLite migrations.

## Planned Next

- Larger retrieval eval set from real engineering notes, papers, and exam PDFs.
- Chapter-wise and section-wise summaries for long textbooks.
- Screenshot/GIF assets for the public README.
- Local data purge/export UI.
- GraphRAG-lite concept expansion only after baseline retrieval metrics justify it.
- Optional connected model mode only with explicit user consent and privacy disclosure.

## Workspaces

### Research

For regular and deep research over uploaded documents.

Use it to:

- Summarize a PDF.
- Explain a concept from a source.
- Ask technical questions.
- Compare ideas across material.
- Inspect citations only when needed.

### Chat

For general conversation in a local-first assistant lane.

Current MVP behavior:

- Uses uploaded documents when relevant.
- Can use session context.
- Abstains when there is not enough local evidence.
- Does not require an external AI provider.

Future connected behavior should be opt-in only.

### Paper Lab

For engineering students and early researchers building citation-backed academic work.

Current foundation supports:

- Paper section drafting from retrieved sources.
- Related-work matrix previews.
- Citation clusters.
- Suggested outline.
- Copyable Markdown draft package.

### Exam Lab

For exam preparation from uploaded notes, textbooks, PDFs, diagrams, and question banks.

Current foundation supports:

- Exam-style answers.
- Study-guide generation.
- Important question workflows.
- Printable custom PDF output from grounded responses.

## Evidence Trail

Every strong answer should be traceable.

NIRMIQ surfaces:

- Source document.
- Page number.
- Chunk reference.
- Supporting evidence.
- Grounding status.
- Citation coverage.

This lets users verify the answer instead of blindly trusting it.

## Tech Stack

Backend:

- FastAPI.
- Python.
- SQLite.
- ChromaDB as optional vector storage.
- PyMuPDF.
- Tesseract OCR adapter.
- BM25 retrieval.
- Ollama adapter for local generation.

Frontend:

- Next.js.
- TypeScript.
- PWA-ready app structure.

Retrieval and synthesis:

- BM25 lexical retrieval.
- Optional semantic vector retrieval.
- Reciprocal Rank Fusion.
- Reranking hooks.
- Context packing.
- Citation-aware grounded synthesis.
- Citation coverage metadata.
- Faithfulness rewrite fallback.

Model strategy:

- Local-first inference.
- RTX 4050-friendly constraints.
- Low VRAM preference.
- Optional Ollama models such as Phi-3 Mini, Qwen2.5 3B, DeepSeek Coder 6.7B, and `nomic-embed-text`.

## Architecture

```text
Next.js frontend
Local FastAPI backend
Ingestion service
Indexing service
Retrieval service
Memory service
Synthesis service
Verification and trust layer
SQLite plus optional Chroma storage
```

## Repository Structure

```text
C:\Nirmiq-researchOS
apps/
  api/                  FastAPI backend
  web/                  Next.js frontend
data/
  raw/                  Uploaded/local source documents
  processed/            Parsed pages, chunks, diagrams, eval data
  indexes/              Local retrieval/vector indexes
  sqlite/               Local database files
docs/                   Product, security, publish, and architecture docs
scripts/                Local startup, smoke, and evaluation scripts
nirmiq_codex_docs/      Codex planning and handoff knowledge base
README.md               GitHub-facing project overview
context.md              Current project memory and implementation log
```

## Quick Start

Install once:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\bootstrap.ps1
```

Root command hub:

```powershell
cd C:\Nirmiq-researchOS
npm.cmd run start
npm.cmd run start:golden
npm.cmd run desktop
npm.cmd run ship:check
```

Run the desktop app:

```powershell
cd C:\Nirmiq-researchOS
npm.cmd run desktop:install
npm.cmd run desktop
```

Or double-click:

```text
NIRMIQ Desktop.cmd
```

The desktop shell starts the same local FastAPI and Next.js runtime, then opens NIRMIQ in an app window. It also includes menu shortcuts for runtime status, logs, VS Code, project files, `context.md`, the README, and debugging docs.

Run local preview:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\start_local.ps1 -OpenBrowser
```

Or double-click:

```text
NIRMIQ ResearchOS.cmd
```

Run local preview and warm-start the bundled golden demo:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\start_local.ps1 -GoldenDemo -OpenBrowser
```

Stop processes started by the launcher:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\stop_local.ps1
```

Or double-click:

```text
NIRMIQ Stop.cmd
```

Create desktop shortcuts:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\create_windows_shortcut.ps1 -Desktop
```

Useful local URLs after the app starts:

- Web: `http://127.0.0.1:3002`
- Local backend: `http://127.0.0.1:8000`
- Readiness: `http://127.0.0.1:8000/health/readiness`

## Docker Dev Run

Docker is optional. The Windows PowerShell launcher is the primary local path.

Fresh Docker dev start:

```powershell
cd C:\Nirmiq-researchOS
docker compose -f docker-compose.local.yml up
```

Then open:

- Web: `http://127.0.0.1:3002`
- API health: `http://127.0.0.1:8000/health`

Notes:

- The compose file builds checked-in API and web Dockerfiles.
- Ollama is disabled by default in Docker compose so the demo works without GPU passthrough.
- For best local model performance on Windows, use `scripts/start_local.ps1` instead of Docker.

## Demo Dataset And Retrieval Results

NIRMIQ includes a small, original PDF demo dataset for recruiters and reviewers:

- `data/raw/demo_pdfs/nirmiq_rag_reference.pdf`
- `data/raw/demo_pdfs/nirmiq_exam_reference.pdf`
- `data/processed/eval/demo_academic_qa.jsonl`

Load and evaluate:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\start_local.ps1
.\scripts\load_demo_dataset.ps1 -ForceReindex
.\scripts\eval_demo_dataset.ps1
```

Latest local retrieval results on 30 labeled questions:

| Mode | MRR | Recall@3 | Recall@5 | Recall@8 | nDCG@3 | Citation expected coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 0.967 | 1.00 | 1.00 | 1.00 | 0.847 | 1.00 |
| BM25 | 0.839 | 1.00 | 1.00 | 1.00 | 0.749 | 1.00 |

Details:

- [Demo dataset](docs/demo_dataset.md)
- [Retrieval evaluation results](docs/retrieval_eval_results.md)
- [Benchmark report](docs/benchmark_report.md)

## Screenshots And GIFs

Recommended public README assets:

- Upload PDF.
- Ask grounded question.
- Open citation trail.
- Compare answer runs.

Capture checklist: [Demo assets guide](docs/demo_assets.md).

## Publish Smoke Check

Strongest EOD check:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\ship_check.ps1
```

This runs backend tests, API compile, frontend production build, local smoke check, and the golden demo.

If backend and frontend are already running and you only want the lightweight smoke:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\publish_smoke.ps1
```

Expected:

- Local backend health returns `ok`.
- Readiness reports local-first status.
- Readiness reports `cloud_api_required=false`.
- Web shell includes NIRMIQ branding.

## Ship Readiness

Current public-release posture:

- Intended release type: local-first portfolio/demo MVP.
- Not intended yet: hosted multi-user SaaS.
- CI: `.github/workflows/ci.yml` verifies backend tests, compile, web build, and Docker Compose config.
- Ownership: `.github/CODEOWNERS` routes project ownership to `@SheeshDarth`.
- License: MIT.
- Security: request body limits, baseline security headers, optional production HSTS/CSP toggles, CORS allowlist, upload sniffing, and local-path ingestion restrictions.
- API stability: existing routes are preserved, with `/api/v1` aliases available for future clients.

## Golden Demo

The fastest way to review NIRMIQ is the bundled offline golden demo.

One-command path:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\run_local.ps1 -GoldenDemo -OpenBrowser
```

Backend-only warm-start:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\golden_demo.ps1
```

Then open `http://127.0.0.1:3002`, log in with a local profile, and click `Load Golden Demo`.

The golden path proves:

- Local corpus indexing without internet.
- Research answers with citations.
- Evidence chips that open focused source chunks.
- Paper Lab citation-backed drafting.
- Exam Lab marks-oriented answers.
- Abstention behavior for unsupported general questions.
- Local Markdown export of answer plus citations.
- Selected source removal as the privacy/purge moment.

Primary demo docs:

- [Golden demo script](docs/demo_script.md)
- [Golden benchmark report](docs/benchmark_report.md)
- [Folio competitive review](docs/folio_competitive_review.md)
- [Windows app packaging](docs/windows_app_packaging.md)
- [Publish checklist](docs/publish_checklist.md)

## Tests

```powershell
cd C:\Nirmiq-researchOS
.\scripts\test_api.ps1
npm.cmd run compile:api
npm.cmd run build
```

## Demo Flow

1. Open the app.
2. Enter local profile details.
3. Upload or select a PDF.
4. Click `Summarize PDF`.
5. Inspect citations in `Deep Research`.
6. Switch to `Paper Lab`.
7. Ask for a related-work or methodology section.
8. Show the outline, citation clusters, and related-work matrix.
9. Click `Copy Markdown Draft`.
10. Switch to `Exam Lab` and generate a study guide or custom PDF.

## Evaluation Goals

NIRMIQ aims to measure answer quality instead of relying on vibes.

Useful metrics:

- Recall@K.
- MRR.
- Citation coverage.
- Grounding strength.
- Abstention correctness.
- Hallucination flags.
- Retrieval latency.
- Context token usage.

## Philosophy

```text
Trust over fluency
Evidence over guessing
Retrieval quality over model size
Student learning over AI showmanship
Offline access over cloud dependency
```

## Important Docs

- [Publish checklist](docs/publish_checklist.md)
- [Ship readiness notes](docs/ship_readiness.md)
- [Demo dataset](docs/demo_dataset.md)
- [Retrieval evaluation results](docs/retrieval_eval_results.md)
- [Demo assets guide](docs/demo_assets.md)
- [Backend architecture](backend_architecture.md)
- [Product requirements](prd.md)
- [Technical requirements](trd.md)
- [UI/UX specification](UI_UX.md)
- [Debugging guide](debugging.md)
- [Accuracy and hallucination audit](docs/accuracy_precision_audit.md)
- [Local model optimization](docs/local_model_optimization.md)
- [Internship impact plan](docs/internship_impact_plan.md)
- [NIRMIQ ecosystem](docs/nirmiq_ecosystem.md)

## Current Status

This project is under active development.

NIRMIQ ResearchOS is being built as a solo-developer AI systems project focused on practical student problems, local AI infrastructure, trustworthy document intelligence, and publishable portfolio value.

## Author

Built by Siddharth as part of the NIRMIQ ecosystem.

## License

MIT. See [LICENSE](LICENSE).
