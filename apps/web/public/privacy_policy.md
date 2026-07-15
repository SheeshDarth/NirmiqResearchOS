# NIRMIQ Academic Intelligence Privacy Policy

Last updated: 2026-07-15

## Local-first privacy position

NIRMIQ Academic Intelligence is designed as an offline-first academic document intelligence workspace. In the current MVP, documents, chunks, sessions, memories, question banks, and diagram metadata are stored locally on the user's machine.

## Data stored locally

NIRMIQ may store:

- Local document paths and document titles.
- Parsed document chunks and citation excerpts.
- SQLite session messages and memory summaries.
- Exam profiles, imported question banks, and diagram metadata.
- Extracted source diagram image files under `data/processed/diagrams`.
- Parsed-page cache files under `data/cache/parsed_pages`.
- Uploaded source copies under the configured NIRMIQ upload directory.
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

- `Clear thread` removes the current local conversation memory.
- `Clear indexed material` removes document metadata, chunks, summaries, jobs, exam artifacts, vector entries, parse cache, extracted diagrams, and NIRMIQ-owned uploaded copies.
- `Reset all local data` also removes all local sessions, feedback, exam profiles, and browser-local profile values.
- External original files selected from outside NIRMIQ's upload directory are intentionally preserved.

## Diagnostics and support

The optional safe diagnostics export contains runtime/status summaries only. It excludes raw logs, environment variables, databases, uploads, document text, prompts, answers, source excerpts, filenames, and full local paths. It is created locally and is never uploaded automatically.
