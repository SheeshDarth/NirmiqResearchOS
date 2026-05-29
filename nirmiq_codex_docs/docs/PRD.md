# Product Requirements Document — NIRMIQ ResearchOS

## Product Name

NIRMIQ ResearchOS

## Product Type

Student-first document intelligence chatbot.

## One-Line Vision

A trustworthy academic chatbot that answers from uploaded documents, proves its sources, and helps students understand and prepare for exams.

---

## Problem

Students upload PDFs, slides, notes, textbooks, lab manuals, PYQs, and academic documents into generic AI tools.

Common failures:
- hallucinated answers
- missing citations
- token exhaustion
- forgotten uploaded context
- poor multi-document reasoning
- weak exam preparation support
- confusing long responses
- no way to verify source evidence

NIRMIQ exists to solve this.

---

## Target Users

### Primary User

College students.

Needs:
- understand notes
- ask questions from documents
- prepare exam answers
- summarize units
- generate revision notes
- verify answers from source material

### Secondary User

Research students.

Needs:
- compare documents
- synthesize concepts
- trace evidence
- extract insights
- reduce reading time

### Tertiary User

Self-learners.

Needs:
- upload learning material
- ask doubts
- create study notes
- follow topic connections

---

## Core User Stories

### Document Upload

As a student, I want to upload documents so that NIRMIQ can answer questions from them.

Acceptance:
- supports PDF initially
- stores document metadata
- tracks ingestion status
- prevents duplicate ingestion

---

### Grounded Q&A

As a student, I want answers from my uploaded documents so that I can trust the output.

Acceptance:
- every answer cites evidence
- unsupported claims are avoided
- low-confidence answers are marked
- source snippets are retrievable

---

### Exam Preparation

As a student, I want exam-style answers so that I can study faster.

Acceptance:
- answers are structured
- key points are highlighted
- source references are included
- no unsupported generic textbook filler

---

### Deep Research View

As a student, I want to inspect how the answer was produced.

Acceptance:
- shows documents used
- shows retrieved chunks
- shows grounding strength
- shows related concepts
- shows citation trail

---

### Session Continuity

As a student, I want NIRMIQ to remember the current study thread.

Acceptance:
- session history persists
- recent context is considered
- memory does not override document evidence

---

## MVP Scope

Must have:
- PDF upload
- ingestion pipeline
- chunking
- embeddings
- BM25 retrieval
- vector retrieval
- RRF fusion
- reranking
- grounded answer generation
- citations
- confidence score
- chat UI
- advanced evidence panel
- session history

Should have:
- exam answer mode
- revision note mode
- retrieval debug metadata
- lightweight memory summaries

Could have later:
- OCR-heavy documents
- DOCX/PPTX support
- handwritten notes
- knowledge graph
- mobile PWA polish
- voice input

Not now:
- authentication
- payments
- cloud sync
- collaboration
- marketplace
- agent automation
- public sharing

---

## Success Metrics

### Retrieval

- Recall@5 improves over vector-only baseline
- MRR tracked per evaluation set
- Citation coverage above 90% for supported answers

### Answer Quality

- low hallucination rate
- clear abstention on insufficient evidence
- student-readable explanations

### Performance

- works on RTX 4050 laptop
- acceptable latency for local inference
- no unnecessary model co-loading

### Product

- student can upload notes
- ask exam questions
- get cited answers
- inspect evidence trail

---

## Product Positioning

NIRMIQ is not ChatGPT replacement.

NIRMIQ is a grounded academic knowledge engine for student-owned documents.

Tagline:

> Upload. Understand. Verify. Learn.
