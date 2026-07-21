# NIRMIQ Academic Intelligence v0.5 Release Notes

Release date: 2026-07-15

Release type: local-first portfolio/demo MVP for Windows

## Highlights

- Query-agnostic Evidence-First Hierarchical Hybrid RAG with a BM25-safe offline backbone.
- Chat-first academic workspace with Research, Chat, Paper Lab, Exam Lab, uploads, citations, and source inspection.
- Windows Electron shell with one-click local runtime startup, branded icon, recovery page, Release Doctor, and portable packaging.
- Explicit local privacy controls for one thread, indexed material, or a complete NIRMIQ-local reset.
- Privacy-safe diagnostics ZIP with no raw logs, document/conversation content, database, uploads, filenames, or full paths.

## Reliability Evidence

- Backend: `163 passed`, `1` third-party deprecation warning.
- API compile: passed.
- Next.js production build: passed; `/` first-load JavaScript `118 kB`.
- Publish smoke and desktop smoke: passed with `cloud_api_required=false`.
- Golden Research, Summary, Paper Lab, and Exam Lab routes: grounded with citations.
- Unsupported corpus query: abstained with zero citations.
- Strict 40-case BM25 metrics: MRR `0.868`, Recall@8 `0.921`, expected citation coverage `0.921`, faithfulness `0.985`, answerability correctness `1.000`.

## Windows Artifact

- File: `dist/desktop/NIRMIQ Academic Intelligence 0.5.0.exe`
- Size: `71,405,018` bytes
- SHA-256: `800FECA2FF2BB56247629495EF41A2160F12FD961DC6C5607044122A1A65527F`
- Source-shell and portable launch smoke: passed
- Signing: not configured; this is not represented as a signed commercial installer

## Privacy And Recovery

- Indexed-material purge now removes orphaned NIRMIQ-owned uploads, parse-cache entries, and diagrams as well as database/vector records.
- External original files are preserved.
- Full reset also removes sessions, messages, memory snapshots, feedback, exam profiles, and browser-local profile values.
- Diagram storage is configurable and isolated in tests so release checks cannot touch a developer's live extracted diagrams.
- Safe diagnostics are generated inside the ship gate and checked for private workspace/user-home paths.

## Known Limits

- Native Linux desktop packaging is not yet verified; Linux browser mode remains the supported low-end path and now has an Ubuntu CI smoke.
- The Windows executable is unsigned.
- Arbitrary-document perfection is not claimed; scans, equations, diagrams, and noisy notes need a larger evaluation corpus.
- Ollama is optional. Deterministic cited synthesis remains available when no local model is running.

## Upgrade And Run

```powershell
cd C:\Nirmiq-researchOS
.\scripts\bootstrap.ps1
npm.cmd run doctor
npm.cmd run desktop
```

For the repeatable reviewer path:

```powershell
npm.cmd run start:golden
npm.cmd run ship:check
```
