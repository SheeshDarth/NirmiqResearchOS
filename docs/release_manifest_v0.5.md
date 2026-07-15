# NIRMIQ Release Manifest v0.5

Verified: 2026-07-15

Platform: Windows 11, Python 3.12.10, Node.js 24.12.0

Release position: local-first portfolio/demo MVP

## Source State

- Branch: `main`
- Reliability baseline commit: `121f7ec`
- Public query API shape: unchanged
- Cloud model/API requirement: none
- Optional local generation: Ollama
- Deterministic offline fallback: supported

## Preflight

`npm.cmd run doctor` passed all critical checks:

- 12 checks executed.
- 0 failures.
- 1 optional warning: Ollama was installed but not running.
- Python, Node.js, npm, FastAPI, PyMuPDF, Uvicorn, Next.js, Electron, SQLite, local ports, and local-only defaults passed.

The doctor is integrated into the normal Windows launcher. Missing optional Ollama does not block startup because BM25 retrieval and deterministic cited synthesis remain supported.

## Release Gate

`npm.cmd run ship:check` passed:

- Backend unit/integration tests: `160 passed`, `1` third-party deprecation warning.
- API compile: passed.
- Next.js production build: passed.
- Route `/` first-load JavaScript: `117 kB`.
- API health/readiness smoke: passed.
- Indexed local state during smoke: `18` documents and `9443` active chunks.
- `cloud_api_required`: `false`.
- Golden Research routes: grounded with citations.
- Golden Exam Lab route: grounded with citations.
- Golden Paper Lab route: grounded with citations.
- Unsupported corpus question: abstained with zero citations.

`npm.cmd run desktop:smoke` passed:

- Electron launched the local API and web runtime.
- Backend health and SQLite readiness passed.
- Web shell returned current NIRMIQ branding.
- Desktop-started processes were cleaned up after the check.

## Retrieval Reliability

Strict 40-case answer-quality evaluation completed through `scripts/eval_answer_quality.ps1`:

| Metric | Result | Gate |
| --- | ---: | ---: |
| MRR | `0.868` | `>= 0.700` |
| Recall@8 | `0.921` | `>= 0.850` |
| Expected citation coverage | `0.921` | `>= 0.900` |
| Answer-quality pass rate | `0.825` | tracked |
| Overall answer score | `0.906` | tracked |
| Readability | `0.939` | tracked |
| Faithfulness | `0.985` | tracked |
| Answerability correctness | `1.000` | tracked |

Known measured debt remains seven answer-quality failures, concentrated in summary/enumeration readability and mechanism/procedure relevance. These are documented limitations, not hidden release failures.

## Windows Artifact

`npm.cmd run desktop:package` passed:

- Artifact: `dist\desktop\NIRMIQ Academic Intelligence 0.5.0.exe`
- Format: portable Windows x64 executable.
- Size: `71,405,762` bytes.
- SHA-256: `8BC4AC0A836724BE6121A467A6685A46F059EC97D43342FF674934755FE3EAF6`.
- Embedded icon: verified against the source-controlled NIRMIQ Academic Intelligence mark.
- Portable launch smoke: passed with health, SQLite readiness, offline contract, web-shell verification, and clean port release.
- Code signing: not configured; the artifact must not be presented as a signed commercial installer.
- Startup recovery: local Retry, Run Doctor, and Open Logs actions replace a broken web view when runtime startup fails.

## Honest Release Boundary

Safe claims:

- Local-first document ingestion, retrieval, synthesis, citations, and session continuity work.
- The core does not require a cloud API, account, Chroma, reranker, or Ollama.
- Windows browser and Electron startup paths are verified.
- Retrieval and answer quality are measured on committed local datasets.

Do not claim yet:

- Accuracy on every arbitrary document or query.
- Signed commercial Windows installer.
- Native Linux desktop package verification.
- Hosted authentication, cloud sync, encrypted vault, or multi-user isolation.
