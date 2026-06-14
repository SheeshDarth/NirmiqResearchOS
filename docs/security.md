# NIRMIQ ResearchOS Security Notes

Last updated: 2026-06-14

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
- Runtime/generated database and vector files ignored by Git.
- SQLite migration identifiers are allowlisted to avoid dynamic user-controlled SQL identifiers.
- Local Data controls in the UI:
  - Export current thread as Markdown.
  - Clear current thread memory and snapshots.
  - Clear indexed document metadata, chunks, summaries, jobs, exam artifacts, and vector entries.

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
- Local documents and extracted diagrams remain on disk.
- If optional cloud/API providers are added later, explicit consent, redaction controls, and visible mode labels are required.
- SQLite and raw document files are not encrypted at rest yet.
- `Clear indexed material` does not delete arbitrary source files from disk. This is intentional to avoid unsafe filesystem deletion.
- No external error-tracking service is enabled because default telemetry would conflict with the local-first privacy contract.
- HSTS is disabled by default because local HTTP development should not set HTTPS-only browser policy.

## Recommended next security work

1. Add real authentication only if hosted or multi-user deployment is introduced.
2. Add encrypted local vault support for SQLite and extracted assets.
3. Add optional secure source-file purge for uploaded files only, with explicit confirmation.
4. Add provider consent screens before sending content to external APIs.
5. Add audit log export for document operations.
6. Add optional local encryption for SQLite, raw uploads, extracted diagrams, and parse cache.
7. Add local bug-report bundle export for logs without sending telemetry to a third party.
