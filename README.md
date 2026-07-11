# NIRMIQ ResearchOS

> Upload. Understand. Verify. Learn.

[![NIRMIQ CI](https://github.com/SheeshDarth/NirmiqResearchOS/actions/workflows/ci.yml/badge.svg?branch=v3-foundation)](https://github.com/SheeshDarth/NirmiqResearchOS/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Local first](https://img.shields.io/badge/local--first-yes-64d8bd.svg)

![NIRMIQ ResearchOS mark](apps/web/public/brand/nirmiq-ais-mark.svg)

![NIRMIQ local academic intelligence flow](docs/assets/nirmiq-demo-flow.svg)

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

## Engineering Problem Log

NIRMIQ keeps a living engineering problem log in [`problems_faced.md`](problems_faced.md). It documents past failures, current RAG retrieval gaps, future risks, the hallucination root cause analysis, and the RAG Reliability Phase roadmap.

## Active Engineering Tracks

- [`docs/overnight_work_plan.md`](docs/overnight_work_plan.md): focused sprint plan for demo reliability, retrieval evaluation, citation selection, UI clarity, and release readiness.
- Ascension OS foundation now lives outside this repository at `C:\Users\Siddharth\Documents\Ascension OS` so NIRMIQ ResearchOS remains focused on academic document intelligence.

## Current V4 Foundation

Implemented in the current repository:

- Bundled `Load Golden Demo` flow with four local academic Markdown sources.
- Electron desktop shell that starts the local runtime and opens NIRMIQ in a Windows app window.
- Desktop diagnostics menu for runtime status, logs, VS Code, project docs, and data folder access.
- Locked reviewer prompts for Research, Summary, Paper Lab, Exam Lab, and abstention behavior.
- Golden demo smoke script that fails if unsupported chat prompts return grounded answers.
- Local answer export as Markdown with citations.
- Whole-thread Markdown export from local session memory.
- Local answer feedback capture with `Good` / `Needs work` signals for future retrieval evaluation.
- Upload PDFs, text, Markdown, and images.
- Ingest local-path documents from trusted corpus roots.
- Summarize selected PDFs with citations.
- Ask grounded questions against selected sources.
- Inspect answer-used source passages and page references without exposing ranking metadata by default.
- Use four workspaces: Research, Chat, Paper Lab, and Exam Lab.
- Run hybrid retrieval with BM25, optional vector search, RRF, and reranking hooks.
- Continue the RAG Reliability Phase with textbook-aware section metadata, section-first retrieval diagnostics, query-agnostic eval categories, and answer relevance metadata inside debug retrieval metadata.
- Use selected-document summary caching keyed by document id, content hash, and summary profile.
- Route query intent deterministically for summary, lookup, compare, deep research, paper, exam, chat, and unclear prompts.
- Show compact trust signals only as `Verified`, `Needs more evidence`, or `Not found in sources`.
- Fall back or abstain when direct source evidence, answer-used citations, or citation verification are weak.
- Abstain in Chat when retrieved material is unrelated to the actual question subject.
- Use Paper Lab for citation clusters, related-work matrix, suggested outline, and Markdown draft export.
- Use Exam Lab for marks-oriented answers, study guides, question-bank support, and printable custom PDFs.
- Check local publish readiness through `/health/readiness` and `scripts/publish_smoke.ps1`.
- Run with a low-memory local model profile: bounded Ollama context, bounded prediction length, short keep-alive, and batched embeddings.
- Use Local Data controls to clear current thread memory or clear indexed material while leaving source files on disk.
- Hardened retrieval/runtime path from the latest audit:
  - empty-text reindex attempts fail safely without wiping prior active chunks.
  - vector-only stale chunks are dropped unless they still exist as active SQLite chunks.
  - summary/factual seed chunks no longer inflate grounding confidence.
  - Exam Lab study guides judge relevance against imported question-bank text, not generic UI command words.
  - Docker Compose publishes only on `127.0.0.1` for local-first safety.
  - release scripts now fail on native command errors instead of producing false-green checks.

## What Works Now

- Upload and index PDF, Markdown, text, and image files locally.
- Ask selected-document questions with citations and trust metadata.
- Summarize selected PDFs with summary caching.
- Inspect evidence chunks in the Deep Research panel.
- Run Research, Chat, Paper Lab, and Exam Lab modes from one workspace.
- Export grounded answers/drafts as local Markdown.
- Export the current thread as local Markdown.
- Save answer-quality feedback locally for later accuracy tuning.
- Generate Exam Lab custom PDFs from grounded responses.
- Clear thread memory and indexed material from the UI for privacy/reset demos.
- Run local smoke checks, backend tests, and frontend production build.
- Evaluate retrieval on a bundled 30-question demo dataset.
- Evaluate query behavior through `data/processed/eval/query_agnostic_rag_categories.jsonl`, covering definitions, explanations, comparisons, procedures, limitations, visuals, summaries, exam answers, paper drafting, and unanswerable prompts.
- Run GitHub CI for backend tests, API compile, frontend build, and Docker Compose validation.
- Run optional Docker dev containers with checked-in API and web Dockerfiles.
- Use `/api/v1/*` routes while preserving the original local API route paths.
- Enforce local request body limits, response compression, and scanner-clean SQLite migrations.
- Run the full publish gate with `npm.cmd run ship:check` or `NIRMIQ Ship Check.cmd`, including tests, compile, web build, smoke, and golden-demo abstention checks.

## Known Retrieval Status

The golden demo is strong, and the harder real-world seed now shows measurable improvement after the first RAG reliability slice:

| Real-world seed | BM25 MRR | Recall@8 | Citation expected coverage |
| --- | ---: | ---: | ---: |
| Before reliability slice | 0.578 | 0.750 | 0.750 |
| MegaSprint One final BM25 | 0.843 | 1.000 | 1.000 |
| MegaSprint One final Hybrid | 0.804 | 1.000 | 1.000 |

This means the current reliability slice reaches the MRR, Recall@8, and citation coverage targets on the current 17-sample seed. The set is still small, so this is a serious progress signal, not a production-grade accuracy claim. BM25 remains the safest offline backbone, while hybrid is improving as a secondary signal instead of acting as the sole source of truth.

The core issue is not just model quality. Most hallucination risk comes from weak evidence selection: broad chunks, limited section awareness, lexical mismatch, and insufficient real-world labels. The canonical problem log is [`problems_faced.md`](problems_faced.md).

Chosen RAG method: [`NIRMIQ Evidence-First Hierarchical Hybrid RAG`](docs/nirmiq_rag_method.md). This keeps BM25 as the offline backbone, uses section/page-first narrowing when metadata exists, treats vector search as optional support, rescues buried direct evidence in legacy documents, and verifies citations before showing a confident answer.

Latest MegaSprint One reliability update:

- Retrieval now uses document-aware expansion for acronyms and source terminology.
- Candidate ranking includes an internal direct-evidence score so answerable passages beat loose mentions.
- Candidate priority was rebalanced so direct answer passages can outrank loosely related reranker hits.
- The real-world eval labels were corrected where OCR/wording damage hid valid source evidence.
- Legacy/no-section documents now get an anchor-rescue pass for direct definitions, dates, privacy/OCR variants, and exact answer cues.
- Default attached-source academic queries route to BM25-first retrieval internally while vector/hybrid remains optional.
- Broad index, glossary, backmatter, and example-list sections are penalized for explanatory questions.
- Synthesis now separates direct evidence, weak related mentions, and true source misses.
- Normal UI hides raw metadata and presents only the trust state plus optional source passages.

## Next Phase: RAG Reliability

What is being improved next:

- Grow real-world eval labels from `17` to at least `40`.
- Convert saved `Needs work` feedback into local eval candidates.
- Expand the query-agnostic category eval set with real textbook, notes, paper, and exam cases.
- Continue improving textbook-aware retrieval metadata: chapter, section, heading, page range, captions, definitions, and key terms.
- Improve section/page-first retrieval before chunk ranking.
- Keep BM25-only fallback fully usable for offline and low-end devices.
- Track chunk-selection reasons, section candidates, citation coverage, unsupported claims, latency, and memory behavior.

Acceptance targets:

- Preserve Recall@8 at or above `0.850` as the eval set grows.
- Preserve MRR at or above `0.700` as the eval set grows.
- Preserve expected citation coverage at or above `0.900` as the eval set grows.
- Preserve the golden demo results and the no-Ollama/no-Chroma fallback path.

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
- Supporting evidence.
- Compact trust status.

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
npm.cmd run desktop:smoke
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

Run the repeatable desktop smoke check:

```powershell
cd C:\Nirmiq-researchOS
npm.cmd run desktop:smoke
```

This launches the Electron shell, waits for local API/web readiness, confirms NIRMIQ branding, verifies `cloud_api_required=false`, and then cleans up the smoke-started runtime.

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

Or double-click:

```text
NIRMIQ Golden Demo.cmd
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

## Linux And Low-End Devices

Linux is feasible through browser-preview mode. On low-end devices, keep the app BM25/extractive-first and leave Ollama optional.

```bash
python -m pip install -e apps/api
npm --prefix apps/web install
bash scripts/start_local.sh
```

Open `http://127.0.0.1:3002`.

Stop:

```bash
bash scripts/stop_local.sh
```

Details: [Linux and low-end feasibility](docs/linux_low_end_feasibility.md).

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
| Hybrid | 0.983 | 1.00 | 1.00 | 1.00 | 0.869 | 1.00 |
| BM25 | 0.983 | 1.00 | 1.00 | 1.00 | 0.859 | 1.00 |

Details:

- [Demo dataset](docs/demo_dataset.md)
- [Retrieval evaluation results](docs/retrieval_eval_results.md)
- [NIRMIQ RAG method](docs/nirmiq_rag_method.md)
- [MegaSprint Two UX plan](docs/megasprint_two_plan.md)
- [MegaSprint Three academic workflow plan](docs/megasprint_three_plan.md)
- [Benchmark report](docs/benchmark_report.md)
- [Linux and low-end feasibility](docs/linux_low_end_feasibility.md)
- [Engineering problem log and RAG Reliability roadmap](problems_faced.md)

Real-world seed eval now also exists for actual local academic material:

- `data/raw/attention_is_all_you_need.pdf`
- `data/raw/uploads/Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-TensorFlow-3rd-Ed.---Annot-5b287bd745.pdf`
- `data/raw/uploads/mod-5-gen-ai-708567b729.pdf`
- `data/processed/eval/real_world_academic_seed.jsonl`

Note: the real-world source PDFs are local/private or copyright-sensitive and are intentionally not committed. The labels and metrics are committed so the evaluation method is visible; replace `source_file` paths with your own local academic PDFs to reproduce or expand it.

Latest phrase-level real-world retrieval result:

| Mode | Samples | MRR | Recall@3 | Recall@5 | Recall@8 | Citation expected coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 17 | 0.843 | 1.000 | 1.000 | 1.000 | 1.000 |
| Hybrid | 17 | 0.804 | 1.000 | 1.000 | 1.000 | 1.000 |

Latest refresh: 2026-07-12. The current failure log contains no active weak retrieval records on this 17-sample seed.

Run:

```powershell
.\scripts\eval_real_world.ps1
```

This seed set is intentionally harder than the golden demo and is the baseline for the RAG Reliability Phase. The goal is to improve retrieval precision and citation coverage before increasing model size, temperature, or context length.

Full-query real-world evaluation now scores expected evidence against full cited chunks, not truncated UI citation previews:

| Mode | MRR | Recall@8 | Citation expected coverage | Grounded response rate | Abstention rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hybrid | 0.573 | 0.688 | 0.688 | 0.938 | 0.063 |
| BM25 | 0.583 | 0.688 | 0.688 | 0.938 | 0.063 |

## Screenshots And GIFs

Committed visual asset:

- `docs/assets/nirmiq-demo-flow.svg`

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
npm.cmd run ship:check
npm.cmd run desktop:smoke
```

Windows double-click alternative:

```text
NIRMIQ Ship Check.cmd
```

`ship:check` runs backend tests, API compile, frontend production build, local smoke check, and the golden demo. `desktop:smoke` separately validates the Electron shell startup path.

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
