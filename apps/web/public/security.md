# NIRMIQ Academic Intelligence System Security Notes

Last updated: 2026-05-29

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
- Diagram asset serving by asset ID with path validation to prevent arbitrary file serving.
- Runtime/generated database and vector files ignored by Git.

## Security limitations

- No production authentication yet.
- No role-based access control.
- Local SQLite database is not encrypted by default.
- Local documents and extracted diagrams remain on disk.
- If optional cloud/API providers are added later, explicit consent and redaction controls are required.

## Recommended next security work

1. Add real authentication only if hosted or multi-user deployment is introduced.
2. Add encrypted local vault support for SQLite and extracted assets.
3. Add allowed-ingestion-root controls to limit which local folders can be indexed.
4. Add document deletion and secure purge flows.
5. Add provider consent screens before sending content to external APIs.
6. Add audit log export for document operations.
