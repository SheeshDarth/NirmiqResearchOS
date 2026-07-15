# MegaSprint Five Plan: Release Confidence And Public Proof

Last updated: 2026-07-15
Status: active; Blocks 1-3 complete, Block 4 next

## Goal

Turn the verified local-first MVP into a repeatable, understandable release for reviewers and real local users without adding cloud dependencies or crowding the chat interface.

## Release Principles

- The offline core must start and answer without Ollama, Chroma, a reranker, or a cloud key.
- Setup failures must name the failing dependency or port instead of surfacing as `Failed to fetch`.
- Security and privacy controls stay local and understandable.
- Release proof must be reproducible from commands, screenshots, metrics, and CI rather than marketing claims.
- Packaging work must not change public query APIs or normal chat behavior.

## Blocks

### Block 1: Preflight And One-Click Startup

Status: complete on 2026-07-15.

- Add a fast release doctor for Python, Node, dependencies, local ports, data directories, privacy-sensitive environment overrides, and optional Ollama.
- Integrate the doctor into browser startup while allowing an explicit developer bypass.
- Add `npm run doctor` and a double-click `NIRMIQ Doctor.cmd`.
- Keep optional local-generation warnings non-blocking because deterministic offline synthesis is a supported path.

### Block 2: Release Evidence Refresh

Status: complete on 2026-07-15. Current evidence is recorded in [`release_manifest_v0.5.md`](release_manifest_v0.5.md).

- Run the ship gate, desktop smoke, golden demo, strict retrieval evaluation, and package checks.
- Record current test counts, bundle size, runtime profile, and offline proof in one release manifest.
- Refresh README screenshots only after manual desktop/browser QA confirms they match the current UI.

### Block 3: Desktop Packaging Polish

Status: complete on 2026-07-15.

- Align package version, product name, icon, and output naming.
- Improve startup failure presentation and make logs accessible without exposing private source paths.
- Validate the portable Windows build from a clean launch.
- Keep code signing as explicit release debt unless a certificate is available.

### Block 4: Privacy And Recovery

Status: next.

- Verify purge removes app-owned uploads, parse cache, diagrams, chunks, vectors, summaries, and session data according to documented scope.
- Add a local diagnostics bundle that redacts full source paths and user document text.
- Verify export and purge flows in browser and desktop shells.

### Block 5: Public Review Package

- Refresh screenshots/GIF, demo script, benchmark report, ship-readiness page, and release notes.
- Add a concise `What works / Known limits` release section.
- Validate Windows one-click startup and document the still-unverified native Linux packaging boundary.

## Acceptance Gate

- `npm.cmd run doctor` passes on the development machine without requiring Ollama.
- One-click browser startup gives actionable setup errors and reaches local API/web readiness.
- Backend tests, compile, web build, publish smoke, golden demo, and desktop smoke pass.
- The strict 40-case BM25 benchmark stays above MRR `0.700`, Recall@8 `0.850`, and expected citation coverage `0.900`.
- README screenshots match the shipped UI.
- Release docs make no hosted-auth, cloud-sync, encrypted-vault, or arbitrary-document perfection claims.

## Non-Goals

- No hosted deployment or multi-user authentication.
- No cloud model requirement.
- No graph database or agent framework.
- No new normal-user retrieval controls.
- No unsigned binary presented as a trusted commercial installer.
