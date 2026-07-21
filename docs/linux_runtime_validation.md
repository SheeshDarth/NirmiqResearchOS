# Linux Runtime Validation

Status: Remaining Job 5 started on 2026-07-21.

## Purpose

Validate NIRMIQ's low-end Linux path honestly:

- Browser-preview mode, not native Linux desktop packaging.
- FastAPI on loopback.
- Next.js build on Linux.
- BM25/offline retrieval with citations.
- Ollama, embeddings, reranking, vector search, and cloud APIs disabled.

This proves the supported low-end path without expanding the project into another
packaging sprint.

## Implemented

- Added `scripts/linux_ci_smoke.sh`.
- Added `npm run smoke:linux`.
- Added a GitHub Actions `ubuntu-latest` job named `Linux browser-mode offline smoke`.
- The Linux job installs the FastAPI backend, compiles backend code, syntax-checks the
  Linux smoke script, installs the web app, builds Next.js on Linux, starts the local API,
  ingests a local markdown source, queries through `POST /query`, and asserts:
  - grounded response
  - at least one citation
  - effective BM25 retrieval mode
  - low-end/BM25/GPU-relevant answer content
- Smoke logs are retained as a short-lived CI artifact.

## Local Verification

Validated from the Windows workspace:

- Git Bash syntax check for `scripts/linux_ci_smoke.sh`: passed.
- Local HTTP smoke using the same offline/BM25 idea: passed with a grounded response and
  citations.

Local WSL Bash still cannot run because the machine has WSL installed without a Linux
distribution. That is no longer treated as Linux proof; Ubuntu CI owns the Linux-host
validation.

## Boundaries

- Native Linux desktop packaging is still unverified.
- ARM Linux and very small RAM devices remain untested.
- The smoke uses a markdown source to avoid OCR/Tesseract and prove the lowest-memory
  text path.
- This is a runtime portability proof, not an arbitrary-document accuracy benchmark.

## Next

- After the CI run passes on `main`, record the run ID and commit hash in `context.md`.
- Consider a later native Linux desktop packaging sprint only if browser-preview mode is
  not enough for the intended demo or release.
