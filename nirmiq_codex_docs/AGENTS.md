# NIRMIQ ResearchOS — Agent Rules

## Identity

NIRMIQ ResearchOS is a student-first document intelligence system.

It is not a generic chatbot.

It solves a real student problem:
- uploaded documents lose context
- GPT answers hallucinate
- token limits break long study material
- students need exam-ready answers from their own files

Core promise:

> Upload documents. Ask questions. Get grounded answers with evidence.

---

## Non-Negotiable Principles

- Offline-first where possible
- Source-grounded answers only
- Citation-first response design
- Retrieval quality over model size
- Low hallucination over fluent guessing
- MVP before extra features
- Student learning over AI impressiveness
- Local inference preferred
- RTX 4050 optimized

---

## Forbidden

Do not add:
- authentication
- payments
- cloud-only architecture
- Kubernetes
- microservices
- enterprise abstractions
- social features
- teams/collaboration
- dashboards unrelated to learning
- agent swarms
- unnecessary dependencies

---

## Allowed Autonomous Changes

Codex may refactor if:
- retrieval improves
- hallucinations reduce
- latency decreases
- VRAM usage decreases
- code becomes simpler
- maintainability improves
- student UX becomes clearer

Codex must explain:
- what changed
- why it improves the project
- tradeoffs introduced

---

## Engineering Rules

- Keep FastAPI backend modular
- Keep routers thin
- Keep services explicit
- Keep adapters replaceable
- Use typed Python
- Prefer async where useful
- Avoid hidden magic
- Avoid global state
- Write tests for retrieval-critical logic

---

## Retrieval Rules

Every answer must prioritize:
1. Correct source retrieval
2. Citation accuracy
3. Grounded synthesis
4. Abstention when evidence is weak
5. Student-readable explanations

Required:
- BM25 retrieval
- Vector retrieval
- RRF fusion
- Reranking
- Context compression
- Citation mapping
- Confidence scoring

---

## Response Rules

If evidence is strong:
- answer clearly
- cite evidence
- show grounding strength

If evidence is weak:
- say evidence is insufficient
- suggest which document may be missing
- do not invent answers

If the user asks exam questions:
- answer from uploaded documents
- give concise exam-ready structure
- include key points
- include source references

---

## UI Rules

NIRMIQ UI must feel:
- academic
- trustworthy
- focused
- modern
- student-friendly

Avoid:
- generic AI neon
- cyberpunk glow
- fake futuristic effects
- cluttered dashboards

Use the design language from:
`docs/UI_GUIDELINES.md`
