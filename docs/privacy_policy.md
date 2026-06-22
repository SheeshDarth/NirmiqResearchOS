# NIRMIQ ResearchOS Privacy Policy

Last updated: 2026-06-20

## Local-first privacy position

NIRMIQ ResearchOS is designed as an offline-first academic document intelligence workspace. In the current MVP, documents, chunks, sessions, memories, question banks, and diagram metadata are stored locally on the user's machine.

## Data stored locally

NIRMIQ may store:

- Local document paths and document titles.
- Parsed document chunks and citation excerpts.
- SQLite session messages and memory summaries.
- Exam profiles, imported question banks, and diagram metadata.
- Extracted source diagram image files under `data/processed/diagrams`.
- Parsed-page cache files under `data/cache/parsed_pages`.
- Uploaded source copies under the configured upload directory.
- Local browser profile name for the client-side login gate.

## Data not intentionally collected by this MVP

This MVP does not intentionally collect:

- Payment data.
- Analytics events.
- Multi-user account data.
- Cloud telemetry.
- Hosted authentication credentials.

## Model and API usage

The intended default is local inference through Ollama. If future versions add optional online API providers, users should be clearly asked before document content or prompts are sent to any third-party service.

## User responsibility

Users should not ingest confidential, regulated, or third-party restricted documents unless they understand the local storage implications and have rights to process those documents.

## Deleting local data

In the current local MVP:

- `Clear thread` removes the current local conversation memory.
- `Clear indexed material` removes document metadata, chunks, summaries, jobs, exam artifacts, vector entries, parse-cache files, extracted diagrams, and app-owned uploaded source copies.
- NIRMIQ does not delete arbitrary external local-path source files outside the upload directory because doing so would be unsafe.

Manual fallback: stop the app, then remove local database/index/runtime folders under `data/sqlite`, `data/indexes`, `data/cache`, and `data/processed` if a full reset is needed.
