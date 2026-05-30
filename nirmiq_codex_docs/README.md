# NIRMIQ Academic Intelligence System

Student-first document intelligence chatbot.

## Vision

Upload academic documents. Ask questions. Get grounded answers with evidence.

## Problem

Generic AI tools hallucinate, lose document context, hit token limits, and give uncited answers.

NIRMIQ solves this through:
- hybrid retrieval
- reranking
- citation validation
- grounded synthesis
- session memory
- local inference

## Current Status

Phase 1 foundation is mostly complete.

See:
- docs/CURRENT_PROGRESS.md
- docs/NEXT_TASKS.md
- prompts/CODEX_MASTER_SCALE_UP_PROMPT.md

## Design Language

Academic Intelligence System Workspace.

See:
- docs/UI_GUIDELINES.md
- design/tokens.css

## Core Stack

- FastAPI
- Next.js PWA
- SQLite
- ChromaDB
- Ollama
- PyMuPDF
- Tesseract
- BM25
- RRF
- bge-reranker-base
