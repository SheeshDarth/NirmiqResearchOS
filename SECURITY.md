# Security Policy

## Supported Scope

NIRMIQ Academic Intelligence is currently a local-first, single-user portfolio/demo MVP.
The supported security scope is the local application runtime, local file handling,
upload validation, diagnostics, and privacy-safe data controls.

The local profile/login screen is a UX gate, not production authentication.

## Reporting Security Issues

Please do not open a public issue with sensitive details.

Preferred path:

- Open a private GitHub security advisory if available.
- Or contact the maintainer through the GitHub profile for `@SheeshDarth`.

Include:

- Affected commit or release.
- Reproduction steps.
- Impact.
- Whether local files, prompts, source excerpts, logs, or credentials are exposed.

## Local-First Privacy Contract

By default, NIRMIQ should not send uploaded documents, prompts, answers, chunks, or
diagnostics to cloud services.

Current core behavior:

- Documents are stored locally.
- SQLite, parsed chunks, cache, diagrams, sessions, and feedback are local.
- Ollama is optional and local.
- External provider/API-key behavior is not part of the current core runtime.
- Diagnostics are generated locally and exclude raw logs, prompts, answers, document
  text, filenames, full local paths, uploads, and databases.

## Known Security Limits

- No production authentication.
- No hosted multi-user isolation.
- No encrypted local vault yet.
- No signed commercial installer yet.
- Local SQLite and app-owned extracted artifacts are not encrypted at rest.

More detail: [`docs/security.md`](docs/security.md) and
[`docs/privacy_policy.md`](docs/privacy_policy.md).
