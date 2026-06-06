# NIRMIQ Academic Intelligence System V3 Foundation

## Product Direction

V3 expands NIRMIQ from an exam-focused workspace into a local-first document intelligence system with three clear sections.

1. **Research Workspace**
   - Regular and deep research over any uploaded document type.
   - Ask questions, inspect citations, compare answers, and review evidence trails.
   - Grounded by local RAG first.

2. **General Chat**
   - A normal chatbot surface for broad conversation.
   - Offline mode can only answer from relevant uploaded documents.
   - If evidence is missing, it should abstain and suggest adding documents or enabling an online model/API later.
   - Online/API-key mode is a future opt-in path, never default.

3. **Exam Lab**
   - Separate academic preparation area.
   - Upload notes, textbooks, PDFs, and question banks.
   - Configure marks, answer style, content type, and format.
   - Generate answers strictly from source documents.
   - Future V3 increments should extract diagrams/images from PDFs and cite them alongside text.
   - Study guide generation should produce important questions with expandable grounded answers and source-backed diagrams.

## Retrieval Strategy

Do not add TigerGraph or another heavyweight graph database yet.

Reason:
- The project is local-first.
- The target machine is an RTX 4050 laptop.
- The MVP should remain solo-developer maintainable.
- Graph databases add operational weight before the retrieval baseline is fully measured.

Preferred V3 retrieval path:

```text
Query
  -> Query intent and section mode
  -> BM25 lexical retrieval
  -> Chroma vector retrieval
  -> Reciprocal Rank Fusion
  -> Lightweight rerank
  -> GraphRAG-lite expansion from SQLite metadata
  -> Context packing and deduplication
  -> Citation validation
  -> Grounded synthesis
```

## GraphRAG-Lite Plan

Use SQLite first.

Add later:
- `concepts`
- `document_concepts`
- `chunk_concepts`
- `concept_edges`
- `diagram_assets`

This gives most of the practical benefit of graph retrieval without running a graph server.

Potential extraction:
- Key concepts from chunks.
- Adjacent chunk relationships.
- Page-level diagram references.
- Question-bank-to-source mappings.

## Diagram Extraction Plan

Use PyMuPDF:
- Extract page images.
- Store assets under `data/processed/diagrams`.
- Add metadata in SQLite.
- Link diagrams to document ID, page, chunk range, caption/nearby text.

Do not generate diagrams from imagination. Use extracted source diagrams first.

## Immediate Implementation Order

1. Add V3 UI sections: Research Workspace, General Chat, Exam Lab.
2. Add section-aware query payloads and prompt modes.
3. Add General Chat abstention behavior for offline/no-evidence cases.
4. Add Exam Lab answer settings model.
5. Add diagram extraction pipeline.
6. Add study guide generation from retrieved source material.
7. Add GraphRAG-lite concept tables and retrieval expansion.

## Tradeoff

This keeps V3 powerful without turning the project into infrastructure soup. TigerGraph or another dedicated graph database can be reconsidered only after local GraphRAG-lite metrics show a specific bottleneck.
