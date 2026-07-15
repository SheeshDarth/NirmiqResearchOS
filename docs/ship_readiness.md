# NIRMIQ Ship Readiness Notes

Last updated: 2026-07-15

## Current Ship Target

NIRMIQ Academic Intelligence is ready to ship as a local-first portfolio/demo MVP.

It is not yet positioned as a hosted multi-user SaaS.

## Current Verified Release Evidence

The canonical dated result is [`release_manifest_v0.5.md`](release_manifest_v0.5.md).

- Release doctor: `12` checks, `0` failures, `1` non-blocking Ollama warning.
- Backend suite: `160 passed`, `1` third-party deprecation warning.
- API compile and Next.js production build: passed.
- First-load JavaScript: `117 kB`.
- Publish and Electron desktop smoke: passed with `cloud_api_required=false`.
- Strict 40-case metrics: MRR `0.868`, Recall@8 `0.921`, expected citation coverage `0.921`, faithfulness `0.985`, answerability correctness `1.000`.
- Portable Windows package rebuilt and launch-tested successfully as `NIRMIQ Academic Intelligence 0.5.0.exe` with the NIRMIQ icon.

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

- Screenshot: chat start/golden source ready.
- Screenshot: grounded answer with citations.
- Screenshot: Evidence Trail/source drawer.
- Screenshot: Paper Lab draft package.
- Screenshot: Exam Lab answer/custom PDF.
- GIF: upload -> ask -> citation trail.

## Remaining Ship Debt

- Keep README screenshots current after UI changes and capture an optional GIF.
- Grow the 40-case answer-quality set with scans, diagrams, equations, and noisy notes.
- Add a redacted local diagnostics bundle instead of cloud error tracking.
- Add chapter-wise summaries for long textbooks.
- Obtain code signing only when a certificate is available.
- Validate native Linux packaging on a real Linux host.
- Add hosted-auth design only if public multi-user deployment becomes a goal.

## Historical Release Evidence

Earlier dated results remain available through Git history. The canonical current evidence is [`release_manifest_v0.5.md`](release_manifest_v0.5.md), which replaces stale test counts and package names in this page.

The project remains positioned as a local-first portfolio/demo MVP. It is not represented as an arbitrary-document accuracy guarantee, signed commercial installer, or hosted multi-user service.
