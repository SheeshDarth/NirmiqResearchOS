# Security and Privacy — NIRMIQ Academic Intelligence System

## Privacy Principle

Student documents stay local by default.

---

## MVP Privacy Rules

- No cloud upload by default
- No external API required for core use
- Local SQLite storage
- Local Chroma storage
- Local model inference preferred

---

## File Safety

Validate:
- file type
- file size
- path traversal
- duplicate content hash

Store uploads under:
`data/raw`

Do not execute uploaded files.

---

## Future Cloud Use

If cloud fallback is added later:
- must be explicit
- must show warning
- must allow opt-out
- must not be default
