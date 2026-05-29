# Deployment Guidelines — NIRMIQ ResearchOS

## MVP Deployment

Target:
local laptop deployment.

---

## Local Services

Required:
- FastAPI backend
- Next.js frontend
- SQLite
- ChromaDB local
- Ollama

---

## Run Order

1. Start Ollama
2. Pull required models
3. Run backend
4. Run frontend
5. Upload test PDF
6. Run query

---

## Docker

Use Docker only for local convenience.

Do not add:
- Kubernetes
- cloud deployment
- production infra
- distributed services

---

## Environment

Use:
`.env.example`

Required values:
- database path
- Chroma path
- Ollama base URL
- default generation model
- retrieval profile

---

## Launch Checklist

- tests pass
- health endpoint works
- PDF upload works
- indexing works
- query works
- citations visible
- advanced panel works
- README updated
