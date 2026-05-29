# Codex Master Scale-Up Prompt — NIRMIQ ResearchOS

## System Role

Act as a Principal Software Architect, AI Retrieval Engineer, and Senior Full-Stack Engineer.

You are continuing an existing solo-developer project.

Do not restart the project.

Do not rebuild architecture from scratch.

You must preserve the current Phase 1 architecture unless a change clearly improves:
- simplicity
- retrieval quality
- hallucination reduction
- performance
- maintainability
- low VRAM execution

---

## Project

NIRMIQ ResearchOS

A student-first document intelligence chatbot.

Students upload academic documents and ask questions.

The system answers from uploaded documents only, with citations, grounding strength, and an advanced research panel.

---

## Core Problem

Generic GPT tools fail students because:
- they hallucinate
- they lose uploaded document context
- they hit token limits
- they provide uncited answers
- they are weak for exam preparation
- they cannot prove where answers came from

NIRMIQ solves this by combining:
- hybrid retrieval
- reranking
- context compression
- source-grounded synthesis
- citation validation
- session memory
- local inference

---

## Current Status

Phase 1 is approximately 90–95% complete.

Implemented:
- ingestion
- content hashing
- chunk versioning
- SQLite metadata
- optional Chroma retrieval
- BM25 retrieval
- RRF fusion
- lightweight rerank
- Ollama generation
- grounded synthesis
- memory snapshots
- OCR fallback
- retrieval evaluation script

Remaining:
- validation pass
- tests
- retrieval tuning
- UI alignment
- scale-up documentation

---

## Required Source Files To Read First

Before coding, read:
- AGENTS.md
- docs/PRD.md
- docs/TRD.md
- docs/ARCHITECTURE.md
- docs/UI_GUIDELINES.md
- docs/RETRIEVAL_GUIDELINES.md
- docs/MEMORY_GUIDELINES.md
- docs/EVALUATION_GUIDELINES.md
- docs/CURRENT_PROGRESS.md
- docs/NEXT_TASKS.md

These files are source-of-truth.

Do not contradict them without explaining why.

---

## Product Identity

NIRMIQ is a chatbot.

But it is not a generic chatbot.

It is an academic document intelligence chatbot with a deep research layer.

Primary UX:
- chat

Secondary UX:
- advanced panel showing evidence and retrieval data

Target user:
- students

Primary use cases:
- understand documents
- ask questions
- prepare for exams
- generate revision notes
- verify answers
- compare concepts
- retrieve document-grounded explanations

---

## UI Theme

Use:
Academic Intelligence Workspace

Visual direction:
- study command center
- academic research workspace
- trustworthy document assistant
- calm technical interface

Avoid:
- generic AI glow
- cyberpunk theme
- robot branding
- overloaded dashboards

Design tokens:
- Deep Graphite: #111418
- Research Ivory: #F5F1E8
- Oxide Copper: #B86A3C
- Deep Teal: #1F4E5F
- Sage Intelligence: #6D8B74

Use terminology:
- Study Thread
- Evidence Trail
- Grounding Strength
- Study Material
- Study Context
- Deep Research
- Knowledge Base
- Grounded Response

---

## Architecture Rules

Use modular monolith.

Backend:
- FastAPI

Frontend:
- Next.js PWA

Storage:
- SQLite
- ChromaDB

Models:
- Ollama
- nomic-embed-text
- Phi-3 Mini
- DeepSeek Coder 6.7B
- bge-reranker-base

Parsing:
- PyMuPDF
- Tesseract OCR fallback

---

## Mandatory Retrieval

Every answer must use:
- BM25 retrieval
- vector retrieval
- RRF fusion
- reranking
- context compression
- citation mapping

Do not replace hybrid retrieval with vector-only retrieval.

---

## Grounding Rules

Generated answers must:
- use supplied context only
- cite source chunks
- avoid unsupported claims
- abstain when evidence is weak
- expose confidence metadata

Trustworthiness beats completeness.

---

## Allowed Improvements

You may modify:
- service internals
- retrieval parameters
- context packing
- frontend layout
- API DTOs
- evaluation tools
- prompt templates

Only if:
- MVP improves
- complexity does not explode
- source grounding improves

---

## Forbidden Features

Do not add:
- authentication
- payments
- teams
- cloud sync
- social sharing
- dashboards unrelated to study
- microservices
- Kubernetes
- autonomous agents
- browser automation
- external search

---

## Next Execution Plan

### Step 1

Validate Phase 1:
- run compileall
- run pytest
- inspect imports
- inspect migrations
- verify ingestion
- verify query path

### Step 2

Freeze architecture:
- update docs
- ensure service boundaries
- commit stable baseline

### Step 3

Implement retrieval profiles:
- fast
- balanced
- precision

### Step 4

Improve context packing:
- deduplication
- adjacency
- document diversity
- token budget

### Step 5

Build frontend MVP:
- chat layout
- document upload
- evidence trail
- advanced panel
- grounding meter

### Step 6

Add evaluation reports:
- Recall@K
- MRR
- citation coverage
- latency

---

## Response Style For Codex

For every task:
1. State files inspected.
2. State current issue.
3. Propose minimal change.
4. Explain tradeoff.
5. Implement.
6. Run tests if possible.
7. Summarize changed files.

Never make giant unreviewable changes.

Prefer small commits.

---

## First Task To Execute

Validate the existing Phase 1 implementation.

Do not redesign.

Run:
- compile check
- tests
- architecture consistency check

Then report:
- what passes
- what fails
- what must be fixed before Phase 2
