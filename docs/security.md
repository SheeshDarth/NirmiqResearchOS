# NIRMIQ Academic Intelligence Security Notes

Last updated: 2026-07-15

## Current security model

NIRMIQ currently runs as a local single-user application. The login screen is a local profile gate for UX and accidental access reduction. It is not production authentication.

## Security improvements already added

- Local-first data storage.
- API CORS restricted to configured local web origins.
- API and web security headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy` denying camera, microphone, and geolocation.
- Response compression for larger local API responses.
- Request body size limit through `MAX_REQUEST_BODY_BYTES`.
- Production-only security header toggles:
  - `ENABLE_HSTS=true`
  - `ENABLE_CONTENT_SECURITY_POLICY=true`
- Diagram asset serving by asset ID with path validation to prevent arbitrary file serving.
- Local path ingestion is restricted by default to configured corpus roots.
- Uploads are content-sniffed for common spoofing cases before indexing.
- Direct local-path ingestion now applies the same suffix, size, and lightweight signature/readability checks as uploaded files.
- Empty-text indexing failures stop before old active chunks are deactivated, preventing accidental loss of previously usable evidence.
- Vector hits are accepted only when the chunk still exists as an active SQLite chunk, so stale Chroma metadata cannot silently re-enter answers.
- Docker Compose local dev ports bind to `127.0.0.1` only.
- Release/startup scripts now fail on native command errors instead of hiding broken installs/builds.
- Runtime/generated database and vector files ignored by Git.
- SQLite migration identifiers are allowlisted to avoid dynamic user-controlled SQL identifiers.
- Local Data controls in the UI:
  - Export current thread as Markdown.
  - Clear current thread memory and snapshots.
  - Clear indexed document metadata, chunks, summaries, jobs, exam artifacts, vector entries, parse-cache files, extracted diagrams, and app-owned uploaded source copies.
  - Reset all app-local documents, sessions, feedback, exam profiles, and browser profile values while preserving external originals.
- App-owned diagram storage is configurable and isolated in tests; recursive purge is fenced to safe child directories inside the workspace.
- Safe diagnostics export contains status summaries and aggregate log markers only. It never packages raw logs or user document/conversation data and performs a final private-path check before compression.

## V3 Local Data Protection Protocol

NIRMIQ is designed to protect the user from accidental data leakage while preserving simple offline workflows.

- Default API host remains `127.0.0.1`.
- Direct local-path ingestion is allowed only under `LOCAL_INGEST_ALLOWED_ROOTS`.
- `SECURITY_ALLOW_ARBITRARY_LOCAL_PATHS=false` by default.
- Uploaded files are copied into the project raw-data area before indexing.
- PDF/image/text uploads are checked against lightweight file signatures or UTF-8 readability.
- The app does not send document content to cloud APIs in the default local mode.
- If external provider support is added later, it must be opt-in per provider and must clearly label when content leaves the machine.
- A ChatGPT/OpenAI-linked account is not required for core NIRMIQ operation.
- Connected model access, if added later, is an optional enhancement path only and must never replace the local/offline default.

## Security limitations

- No production authentication yet.
- No role-based access control.
- Local SQLite database is not encrypted by default.
- External local-path source files remain on disk unless the user deletes them outside NIRMIQ.
- Uploaded source copies owned by NIRMIQ are deleted by the indexed-material purge path.
- Parse cache and extracted diagrams owned by NIRMIQ are deleted by the indexed-material purge path.
- If optional cloud/API providers are added later, explicit consent, redaction controls, and visible mode labels are required.
- SQLite and raw document files are not encrypted at rest yet.
- `Clear indexed material` does not delete arbitrary source files outside the app upload directory. This is intentional to avoid unsafe filesystem deletion.
- No external error-tracking service is enabled because default telemetry would conflict with the local-first privacy contract.
- HSTS is disabled by default because local HTTP development should not set HTTPS-only browser policy.

## Recommended next security work

1. Add real authentication only if hosted or multi-user deployment is introduced.
2. Add encrypted local vault support for SQLite and extracted assets.
3. Add provider consent screens before sending content to external APIs.
4. Add an optional local audit log for destructive document operations.
5. Add optional local encryption for SQLite, raw uploads, extracted diagrams, and parse cache.
6. Add a strict "local-only model endpoint" guard before allowing non-loopback Ollama or external model hosts.
