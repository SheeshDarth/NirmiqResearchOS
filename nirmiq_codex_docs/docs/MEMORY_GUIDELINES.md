# Memory Guidelines — NIRMIQ Academic Intelligence System

## Goal

Preserve study continuity without causing hallucinations.

Memory supports conversation.

Documents remain the source of truth.

---

## Memory Types

### Short-Term Memory

Stores:
- recent user turns
- recent assistant answers
- active study thread
- selected documents

Storage:
- SQLite messages

---

### Session Summary

Stores:
- condensed study context
- current topic
- unresolved questions
- important concepts discussed

Storage:
- SQLite memory_snapshots

---

## Memory Rules

Memory may:
- help interpret follow-up questions
- resolve pronouns like "this topic"
- remember current study goal
- continue exam preparation flow

Memory may not:
- invent document facts
- replace retrieval
- override citations
- answer without evidence

---

## Query Memory Flow

```text
User Query
  ↓
Load Recent Messages
  ↓
Load Session Summary
  ↓
Clarify Query Context
  ↓
Retrieve From Documents
  ↓
Generate Grounded Answer
  ↓
Save Turn
  ↓
Update Summary When Needed
```

---

## Example

User:
"Explain this in simpler words."

Memory helps identify:
- previous answer
- previous topic
- active document

Retrieval still validates:
- source chunks
- citation anchors

---

## Summary Update Policy

Update memory when:
- message count exceeds window
- topic changes
- exam mode starts
- user switches documents

Do not summarize every turn.

---

## Privacy

Memory is local.

No cloud sync in MVP.
