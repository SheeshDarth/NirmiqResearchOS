# NIRMIQ Academic Intelligence System

![NIRMIQ Academic Intelligence System mark](apps/web/public/brand/nirmiq-ais-mark.svg)

NIRMIQ Academic Intelligence System is a local-first academic intelligence workspace for grounded document research, citation-backed paper drafting, and exam preparation.

It is built to run on a student laptop, stay useful offline, and keep uploaded material as the source of truth. A ChatGPT/OpenAI-linked account is not required for the core product.

## What It Does

- Upload PDFs, text, Markdown, and images.
- Summarize documents with citations.
- Ask grounded questions against selected sources.
- Inspect evidence chunks and source pages.
- Use Research, Chat, Paper Lab, and Exam Lab workspaces.
- Draft Paper Lab sections with related-work matrix, citation clusters, and Markdown export.
- Generate Exam Lab answers, study guides, and printable custom PDFs.
- Run locally with a FastAPI backend, Next.js, SQLite, optional Chroma, and optional Ollama.

## Why It Is Different

Most PDF chat apps stop at upload-and-answer. NIRMIQ focuses on:

- Local-first privacy.
- Citation-aware answers.
- Abstention when evidence is weak.
- Retrieval metadata for debugging and evaluation.
- Paper and exam workflows tailored for engineering students.
- Low-VRAM local inference strategy for RTX 4050-class hardware.
- Cloud/API-provider usage is future optional enhancement only, not the default or required path.

## Current V4 Foundation

Implemented:

- Hybrid retrieval: BM25, optional vector retrieval, RRF, reranking hook.
- Grounded synthesis with citation verification and fallback rewrites.
- Chunk quality scoring to reduce noisy PDF/OCR chunks.
- Selected-document summary cache by content hash.
- Deterministic query intent routing.
- Compact trust badge: `Verified`, `Rewritten`, `Needs review`, or `Low citation coverage`.
- V4 Paper Lab citation workspace:
  - suggested paper outline
  - related-work matrix
  - citation clusters
  - Markdown draft copy export

## Quick Start

Backend:

```powershell
cd C:\Nirmiq-researchOS\apps\api
python -m pip install -e .
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
cd C:\Nirmiq-researchOS\apps\web
npm install
npm run dev
```

Open:

- Web: `http://127.0.0.1:3002`
- Local backend: `http://127.0.0.1:8000`
- Readiness: `http://127.0.0.1:8000/health/readiness`

## Publish Smoke Check

After backend and frontend are running:

```powershell
cd C:\Nirmiq-researchOS
.\scripts\publish_smoke.ps1
```

## Tests

```powershell
cd C:\Nirmiq-researchOS
$env:PYTHONPATH='apps/api'
python -m pytest apps/api/app/tests/unit apps/api/app/tests/integration -q
python -m compileall apps/api/app
cd apps/web
npm run build
```

## Demo Flow

1. Open the app and enter local profile details.
2. Upload or select a PDF.
3. Click `Summarize PDF`.
4. Inspect citations in `Sources`.
5. Switch to `Paper Lab`.
6. Ask for a related-work or methodology section.
7. Show the Paper Lab outline and related-work matrix.
8. Click `Copy Markdown Draft`.
9. Switch to `Exam Lab` and generate a study guide or custom PDF.

## Important Docs

- [Publish checklist](docs/publish_checklist.md)
- [Backend architecture](backend_architecture.md)
- [Product requirements](prd.md)
- [Technical requirements](trd.md)
- [Accuracy and hallucination audit](docs/accuracy_precision_audit.md)
- [Internship impact plan](docs/internship_impact_plan.md)
- [NIRMIQ ecosystem](docs/nirmiq_ecosystem.md)

## Notes

- The local profile screen is a UX gate, not production authentication.
- Core document Q&A works without cloud APIs.
- Ollama is optional; deterministic fallback paths keep the app usable when local models are offline.
- Any connected ChatGPT/OpenAI account mode should be opt-in only and used as an add-on for response improvement, not as the main operating path.
- Target GitHub repository name: `NirmiqAcademicIntelligenceSystem`.
