# NIRMIQ Product Requirements Document

Last updated: 2026-06-06

## Product Name

NIRMIQ ResearchOS

## Ecosystem Context

NIRMIQ ResearchOS is the academic document intelligence workspace under the broader NIRMIQ umbrella. The wider ecosystem may include NIRMIQ OS, NIRMIQ Mirror, NIRMIQ Intelligence Engine, NIRMIQ Agent System, NIRMIQ Research Assistant, and NIRMIQ Echo. This product must still work independently for users who only want academic document intelligence.

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

## V3 Non-Goals

- Real hosted auth.
- Payments.
- Multi-user cloud accounts.
- Kubernetes, enterprise observability, or analytics dashboards.
- Full graph database migration.
- Fully polished production legal system.

## Key User Flows

### First Run

1. User sees NIRMIQ ResearchOS landing screen.
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
- Demo flow can be completed without internet.
- Direct filesystem ingestion cannot accidentally index private files outside trusted corpus roots.
- Longer research drafts feel useful without sacrificing citation verification.
- Repeated selected-document summaries return faster from cache.
- Users can see a simple answer trust signal without opening debug metadata.
- Paper Lab can produce a grounded Markdown draft package instead of only a chat answer.

## Why Users Choose NIRMIQ

NIRMIQ is not a generic upload-and-chat clone. It is a local academic intelligence workspace that combines retrieval engineering, citation transparency, paper workflows, and exam workflows in one focused system. Its advantage is trust: the document corpus remains the source of truth, and users can inspect why an answer was produced.

## V4 Candidate Upgrades

- SQLite concept graph for GraphRAG-lite expansion.
- Safe local agent orchestrator with typed retrieval/synthesis tools.
- Paper Lab DOCX/LaTeX export after Markdown behavior is validated.
- Exam Lab answer templates by marks and diagram-aware study guides.
- Local data purge/export controls.
- Retrieval evaluation dataset for NIRMIQ academic use cases.
- Streaming answers after synthesis reliability is stable.
