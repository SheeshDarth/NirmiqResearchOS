# NIRMIQ Ship Readiness Notes

Last updated: 2026-06-14

## Current Ship Target

NIRMIQ ResearchOS is ready to ship as a local-first portfolio/demo MVP.

It is not yet positioned as a hosted multi-user SaaS.

## Finale AI Dashboard Takeaways

Finale AI scored the repository at `72.9`.

Dimension scores:

- Security: `80`
- Reliability: `91`
- Deployment: `58`
- Architecture: `88`
- Cost Risk: `0`

Interpretation:

- Architecture and reliability are strong enough for an MVP demo.
- Deployment credibility was the main public-release gap.
- Cost risk is excellent because the system is local/offline-first by default.

## EOD Hardening Implemented

- Added GitHub Actions CI for backend tests, backend compile, frontend build, and Docker Compose config validation.
- Added `.github/CODEOWNERS`.
- Added MIT `LICENSE`.
- Added root `package.json` command hub.
- Added API and web Dockerfiles.
- Updated `docker-compose.local.yml` to build checked-in containers.
- Added `.dockerignore`.
- Added `/api/v1/*` route aliases while preserving existing local routes.
- Added request body limit enforcement.
- Added response compression.
- Added production-opt-in HSTS and CSP toggles.
- Removed scanner-triggering SQLite f-string `execute()` patterns.
- Added API hardening tests.

## What Is Safe To Claim

- Offline-first document intelligence system.
- Local FastAPI backend is part of the runtime, not a cloud dependency.
- Upload, ingest, retrieve, summarize, cite, and export workflows exist.
- Paper Lab and Exam Lab foundations exist.
- Demo dataset and retrieval metrics exist.
- Core app works without ChatGPT/OpenAI API usage.
- Optional Ollama improves local generation when models are installed.

## What Not To Claim Yet

- Production hosted authentication.
- Multi-user SaaS isolation.
- Encrypted local vault.
- Cloud sync.
- Internet search.
- Enterprise deployment.
- Fully automated paper generation without user review.

## Release Checklist

Before linking publicly:

```powershell
cd C:\Nirmiq-researchOS
npm.cmd run test:api
npm.cmd run compile:api
npm.cmd run build
npm.cmd run ship:check
docker compose -f docker-compose.local.yml config
```

Recommended proof assets:

- Screenshot: login/home.
- Screenshot: upload/index ready.
- Screenshot: grounded answer with citations.
- Screenshot: Evidence Trail chunk focus.
- Screenshot: Paper Lab draft package.
- Screenshot: Exam Lab answer/custom PDF.
- GIF: upload -> ask -> citation trail.

## Remaining Ship Debt

- Capture README screenshots/GIFs.
- Expand the retrieval eval set from 10 to 30-40 questions.
- Add local data purge/export UI.
- Add chapter-wise summaries for long textbooks.
- Add optional local log bundle export instead of cloud error tracking.
- Add hosted-auth design only if public multi-user deployment becomes a goal.
