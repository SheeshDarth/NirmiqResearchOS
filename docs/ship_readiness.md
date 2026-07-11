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
- Add real engineering/textbook labels beyond the current 30-question synthetic demo set.
- Add optional uploaded-source-file purge after safe file ownership checks.
- Add chapter-wise summaries for long textbooks.
- Add optional local log bundle export instead of cloud error tracking.
- Add hosted-auth design only if public multi-user deployment becomes a goal.

## 2026-07-12 Release Hardening Refresh

Current release gate status:

- `npm.cmd run ship:check`: passed.
- Backend tests: `89 passed`, `1 warning`.
- Web build: passed.
- Publish smoke: passed.
- Golden demo: passed, including unsupported-chat abstention.
- `npm.cmd run desktop:pack`: passed.
- `npm.cmd run desktop:package`: passed and refreshed `dist/desktop/NIRMIQ ResearchOS 0.1.0.exe`.
- `npm.cmd run desktop:smoke`: passed; API/web readiness and `cloud_api_required=false` were verified through the Electron shell.
- `npm.cmd run eval:demo`: passed with MRR `0.983` and Recall@8 `1.000` for both Hybrid and BM25.
- `scripts\eval_real_world.ps1`: passed with BM25 MRR `0.843`, Hybrid MRR `0.804`, Recall@8 `1.000`, and no active weak retrieval records.

The project remains positioned as a local-first portfolio/demo MVP. Remaining release-hardening priorities are live README screenshots/GIFs, a larger real-world eval set, signed/icon-branded desktop packaging, and manual visual QA inside the desktop window.
