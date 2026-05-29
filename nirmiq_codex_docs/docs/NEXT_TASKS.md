# Next Tasks — NIRMIQ ResearchOS

## Immediate

1. Commit current state.
2. Run tests when environment available.
3. Freeze Phase 1 architecture.
4. Tune retrieval defaults.
5. Add retrieval profiles.
6. Improve context packing.
7. Start frontend chat MVP.

---

## First Codex Task

Validate existing Phase 1 implementation.

Do not redesign architecture.

Check:
- tests
- imports
- migrations
- service boundaries
- retrieval pipeline
- citation persistence
- memory snapshots

---

## Second Codex Task

Implement retrieval profiles:
- fast
- balanced
- precision

Only change:
- top-K values
- rerank count
- context token budget
- abstention thresholds

---

## Third Codex Task

Implement frontend MVP:
- chat layout
- document upload
- evidence trail
- advanced panel
- grounding meter
