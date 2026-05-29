# NIRMIQ Next Version Improvements

Last updated: 2026-05-29

## Product improvements

1. Make sidebars collapsible with keyboard shortcuts so the default view is nearly identical to ChatGPT.
2. Add a proper local document picker instead of requiring users to paste filesystem paths.
3. Add document deletion and secure purge from SQLite, BM25, Chroma, extracted diagrams, and memory.
4. Add a first-run onboarding flow that explains local-first privacy, citations, and offline limitations.
5. Add a dedicated Engineering Paper Lab workflow:
   - title/abstract builder
   - related-work matrix
   - citation clustering
   - methodology scaffold
   - limitations and future-work generator
   - export to Markdown, DOCX, and LaTeX/BibTeX
6. Add source quality indicators for papers, notes, textbooks, and question banks.
7. Add collection-level querying across multiple uploaded PDFs.

## Retrieval improvements

1. Add GraphRAG-lite concept tables in SQLite before considering a graph database.
2. Add concept extraction for chunks and diagrams.
3. Add citation diversity constraints so paper drafts cite multiple parts of the corpus.
4. Add query decomposition for deep research and paper drafting.
5. Add citation verification that rejects answer claims without citation anchors.
6. Add retrieval evaluation datasets for engineering PDFs, textbooks, and notes.
7. Add hybrid reranking with local cross-encoder only when VRAM allows.

## UI improvements

1. Use a ChatGPT-like conversation shell by default with optional source drawer.
2. Add command palette for modes: Research, Paper Lab, Exam Lab, Explain, Compare, Study Guide.
3. Show citations inline as compact source chips that open the source drawer.
4. Show source diagrams inside study-guide cards when diagram context is used.
5. Add paper-outline cards and citation table views.
6. Improve mobile layout so chat remains the primary surface.

## Security and privacy improvements

1. Add real authentication only for hosted or multi-user deployment.
2. Add encrypted local SQLite and encrypted extracted-asset storage.
3. Add allowed ingestion roots to prevent accidental indexing outside approved folders.
4. Add explicit consent before sending any document content to online APIs.
5. Add local data export/delete controls.
6. Add audit log for ingestion, deletion, generation, and external-provider usage.
7. Add a clear hosted-mode privacy policy if cloud sync or remote APIs are enabled.

## Performance improvements

1. Cache parsed PDF pages by content hash.
2. Incrementally reindex changed documents only.
3. Add embedding batch-size controls for RTX 4050 memory limits.
4. Add model-routing presets: fast, balanced, deep, exam, paper.
5. Add streaming responses once local generation is stable.
