# NIRMIQ Product Requirements Document

Last updated: 2026-07-15

## Product Name

NIRMIQ Academic Intelligence

## Ecosystem Context

NIRMIQ Academic Intelligence is the academic document intelligence workspace under the broader NIRMIQ umbrella. The wider ecosystem may include NIRMIQ OS, NIRMIQ Mirror, NIRMIQ Intelligence Engine, NIRMIQ Agent System, NIRMIQ Research Assistant, and NIRMIQ Echo. This product must still work independently for users who only want academic document intelligence.

## One-Line Promise

Turn personal academic material into grounded answers, cited research drafts, and exam-ready study outputs while keeping the source of truth local.

## Target Users

- Engineering students working with PDFs, notes, textbooks, and question banks.
- Early researchers building literature reviews and paper drafts.
- Solo learners who want a local assistant that explains documents with citations.
- Portfolio reviewers evaluating retrieval engineering, backend architecture, and AI product judgment.

## Core Problem

Students and early researchers often have scattered PDFs, lecture notes, screenshots, and question banks. Generic chatbots are fast but can hallucinate, cloud upload may be uncomfortable, and citation tracking is weak. NIRMIQ solves this by making the user document corpus the primary source of truth.

## Product Pillars

- Grounded intelligence: answers cite local sources.
- Academic workflow fit: research, chat, paper lab, and exam lab are separate paths.
- Local-first trust: documents stay on the user machine by default.
- Evidence visibility: users can inspect sources instead of trusting black-box output.
- Low-friction UX: ChatGPT-like interaction, not a dashboard maze.
- Measured reliability: answer quality improves through local retrieval metrics, query-category evals, direct-evidence ranking, feedback-to-eval loops, and citation checks rather than cloud dependency.

## V3 Scope

- Captivating landing screen explaining the product.
- Local profile login with phone/email.
- Clear workspace choice after login.
- Research workspace for document explanation, summarization, and deep research.
- Chat workspace for general conversation, local-first and document-aware.
- Paper Lab workspace for citation-heavy academic writing workflows.
- Exam Lab workspace for marks-oriented answers, study guides, and printable custom PDFs.
- Minimized composer mode for better response reading.
- Citation drawer/source cockpit shown only when useful.
- V3.1 summary cache for repeated selected-document summaries.
- Deterministic intent routing for summary, factual lookup, compare, paper, exam, and chat prompts.
- Compact trust badge for citation verification and citation coverage.
- MegaSprint One compact trust states: `Verified`, `Needs more evidence`, and `Not found in sources`.
- Safer selected-source behavior: when a document is selected, default questions remain scoped to that source.
- Honest evidence behavior: stale vector hits, zero-text reindex failures, and unsupported cited claims must not produce trusted answers.
- V4.2 local answer feedback: users can mark answers as `Good` or `Needs work` so bad responses become a local improvement dataset.
- RAG Reliability Phase: selected-document queries gain textbook-aware section metadata and hidden retrieval diagnostics so the system can improve precision without exposing more controls to users.
- Query-agnostic reliability: valid user questions are routed by intent/category and judged by direct source support, not by a small mandatory prompt list.
- Chosen RAG method: NIRMIQ Evidence-First Hierarchical Hybrid RAG, documented in [`docs/nirmiq_rag_method.md`](docs/nirmiq_rag_method.md). Product behavior should feel simple to users while internally using section-first retrieval, BM25-first offline search, optional vector support, direct-evidence rescue, direct-answer candidate priority, citation verification, and abstention.
- MegaSprint One final reliability snapshot: on the current 17-sample real-world seed, BM25 reaches MRR `0.843` and Hybrid reaches MRR `0.804`, with Recall@8 and expected citation coverage at `1.000`; this is a strong MVP signal, not a broad production accuracy claim.

## V4 Golden Demo Scope

- Bundled offline demo corpus under `data/raw/golden_demo`.
- One-click `Load Golden Demo` action in the app.
- Locked reviewer prompts for Research, Summary, Paper Lab, Exam Lab, and abstention.
- Compact Deep Research proof strip showing intent, citation coverage, cache state, and source type.
- Local Markdown answer export with citations.
- Publish script `scripts/golden_demo.ps1` for repeatable corpus indexing and smoke queries.
- General Chat abstention proof: unsupported prompts should return no grounded answer and no citations.

## V3 Non-Goals

- Real hosted auth.
- Payments.
- Multi-user cloud accounts.
- Kubernetes, enterprise observability, or analytics dashboards.
- Full graph database migration.
- Fully polished production legal system.

## Key User Flows

### First Run

1. User sees the NIRMIQ Academic Intelligence landing screen.
2. User enters name plus email or phone.
3. User chooses a workspace: Research, Chat, Paper Lab, or Exam Lab.
4. User uploads or selects a document.
5. User asks, summarizes, drafts, or prepares exam material.

### Research

1. Select a PDF.
2. Click Summarize PDF or ask a custom question.
3. Read grounded answer.
4. Open Sources only if citation detail is needed.
5. Minimize composer while reading long responses.
6. Mark the answer as useful or needing work when it should influence later tuning.

### Chat

Chat is the general assistant lane. In the current local MVP, it should use local context and uploaded documents when relevant, and abstain when the answer needs knowledge outside the corpus. In a future connected mode, the user may provide their own API key for internet/cloud model access with explicit consent.

### Paper Lab

1. Upload papers or notes.
2. Ask for outlines, related-work matrix, methodology draft, limitations, or citation-backed paragraphs.
3. Inspect citations, related-work matrix rows, and citation clusters.
4. Copy a grounded Markdown paper draft with outline, matrix, answer, and citations.
5. Future V5 exports can target DOCX or LaTeX.

### Exam Lab

1. Upload notes, textbooks, diagrams, and question banks.
2. Select answer style, marks, and content depth.
3. Generate answer, revision notes, important questions, or study guide.
4. Generate a printable custom PDF from the current grounded response.

## Success Metrics

- A user can summarize a PDF in under one minute after indexing.
- Grounded answers include useful citations when evidence exists.
- The app abstains on unrelated questions instead of hallucinating.
- Composer minimization increases visible reading area.
- Local build and backend tests stay green.
- Full ship gate passes before public/demo pushes.
- Demo flow can be completed without internet.
- Golden demo can be warm-started from bundled files without internet.
- Reviewer can inspect a citation and focus the exact source chunk.
- Reviewer can export a grounded answer with citations as a local Markdown artifact.
- Direct filesystem ingestion cannot accidentally index private files outside trusted corpus roots.
- Longer research drafts feel useful without sacrificing citation verification.
- Repeated selected-document summaries return faster from cache.
- Users can see a simple answer trust signal without opening debug metadata.
- Paper Lab can produce a grounded Markdown draft package instead of only a chat answer.
- Local model runtime remains bounded through low-memory Ollama settings and embedding batches.
- Direct local-path ingestion and Docker dev defaults respect the local-first privacy contract.
- Real-world academic retrieval improves against measured baselines instead of relying on larger models as the first fix.

## Why Users Choose NIRMIQ

NIRMIQ is not a generic upload-and-chat clone. It is a local academic intelligence workspace that combines retrieval engineering, citation transparency, paper workflows, and exam workflows in one focused system. Its advantage is trust: the document corpus remains the source of truth, and users can inspect why an answer was produced.

## Next Phase: RAG Reliability

Product goal:

Make answers feel more accurate, focused, and source-faithful on real textbooks, notes, and papers while keeping the interface as simple as a chatbot.

Why this matters:

- The golden demo proves the flow works.
- Real textbooks reveal harder retrieval failures: BM25 MRR `0.578`, Recall@8 `0.750`, and expected citation coverage `0.750`.
- Users experience these retrieval gaps as hallucination, vague answers, boring summaries, or citations that do not support the exact claim.

Planned product behavior:

- When the user selects a document, NIRMIQ should first identify the most relevant chapter/section/page region, then answer from chunks inside that region.
- If evidence is weak, NIRMIQ should ask for a narrower question or abstain instead of producing a confident generic answer.
- Trust states stay visible, but detailed retrieval metadata remains hidden unless Deep Research/debug panels are opened.
- Answer feedback becomes a local improvement signal, not analytics.

Acceptance targets:

- Recall@8 at least `0.850`.
- MRR at least `0.700`.
- Expected citation coverage at least `0.900`.
- Golden demo and offline fallback behavior must not regress.

## V4 Candidate Upgrades

- SQLite concept graph for GraphRAG-lite expansion.
- Safe local agent orchestrator with typed retrieval/synthesis tools.
- Paper Lab DOCX/LaTeX export after Markdown behavior is validated.
- Exam Lab answer templates by marks and diagram-aware study guides.
- Optional encrypted local vault after the current purge/reset controls are proven across releases.
- Larger retrieval evaluation dataset for NIRMIQ academic use cases after the first reliability pass.
- Streaming answers after synthesis reliability is stable.

## 2026-06-11 Accuracy Rescue Acceptance Update

Added acceptance criteria for demo reliability:

- A selected textbook with active chunks must answer a factual definition/solution question using relevant textbook pages.
- Missing configured local models must not silently degrade answer quality when another answer-capable local model is installed.
- Generated answers must be citation-anchored sentence by sentence where possible.
- Unsupported specific claims must be rewritten to source-only fallback instead of being shown as verified.
- Stale library rows must not appear as healthy indexed material.

Validated source:

- `Hands-On Machine Learning with Scikit-Learn, Keras and TensorFlow`
- Clean document id: `e9b7b4ff-b679-44db-a2cf-bbb945caee22`
- Active chunks: `1833`

## 2026-06-20 Hardening Acceptance Update

Added acceptance criteria for ship reliability:

- Empty/unreadable reindex attempts fail safely and preserve previous active chunks.
- Direct local-path ingestion validates file type, file size, and lightweight signatures before indexing.
- Retrieval ignores orphaned vector-store hits when SQLite no longer marks the chunk active.
- Summary/factual seed chunks improve context selection without inflating grounding scores.
- Exam Lab study guides use imported question-bank text to judge relevance.
- Frontend requests time out gracefully and avoid duplicate busy submissions.
- Normal preview and golden-demo preview are separate so users can work without accidental demo preload.
- Release scripts and desktop packaging scripts must fail non-zero on command errors.

Validated on 2026-06-20:

- Backend tests: `41 passed, 1 warning`.
- API compile: passed.
- Web build: passed.
- Desktop unpacked package: passed.
- Full `scripts/ship_check.ps1`: passed.
