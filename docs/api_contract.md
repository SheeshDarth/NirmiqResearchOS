# NIRMIQ API Contract (Phase 1)

## Endpoints

### `GET /health`
- Response:
  - `{"status":"ok"}`

### `GET /health/readiness`
- Response:
  - `status: "ready"|"needs_documents"`
  - `database: "ok"`
  - `documents: number`
  - `indexed_documents: number`
  - `active_chunks: number`
  - `vector_store_available: boolean`
  - `ollama_available: boolean`
  - `local_first: true`
  - `local_backend: true`
  - `cloud_api_required: false`
  - `external_provider_enabled: false`
  - `primary_inference: "local_offline"`
  - `runtime_profile: "balanced"|"low_memory"|"cpu_offline"`
  - `low_memory_mode: boolean`
  - `ollama_runtime: object`
  - `notes: string`
- Behavior:
  - Indicates whether the local backend is alive and whether there is enough indexed local corpus state for a grounded demo.
  - Confirms that cloud/ChatGPT/OpenAI API access is not required for core operation.
  - Reports bounded local model settings such as keep-alive, context window, prediction cap, optional GPU/thread controls, and embedding batch size.

### `POST /ingest`
- Request:
  - `source_path: string`
  - `title?: string`
  - `mime_type?: string`
- Response:
  - `document_id: string`
  - `status: string`
  - `indexed: boolean`
- Behavior:
  - idempotent by `source_path + content_hash`
  - reindexes when source content changes
  - applies OCR fallback for low-text pages when OCR stack is installed

### `POST /query`
- Request:
  - `session_id: string`
  - `query: string`
  - `mode: string` (default `research`)
  - `retrieval_mode: "hybrid"|"bm25"|"vector"` (default `hybrid`)
  - `debug: boolean` (default `false`)
- Response:
  - `session_id: string`
  - `answer: string`
  - `citations: Citation[]`
  - `grounded: boolean`
  - `retrieval_meta?: object`
- `Citation`:
  - `document_id: string`
  - `chunk_id: string`
  - `page_start?: number`
  - `page_end?: number`
  - `score?: number`
  - `excerpt?: string`
- `retrieval_meta` currently includes:
  - `bm25_hits`
  - `vector_hits`
  - `vector_enabled`
  - `embed_backend` (`ollama|hash|disabled`)
  - `rerank_backend` (`ollama|lexical`)
  - `generation_backend` (`ollama|fallback|none`)
  - `grounding_score`
  - `grounding_state` (`strong|moderate|weak`)
  - `grounding_summary`
  - `citation_count`
  - `context_chunks_used`
  - `max_chunks_per_document`
  - `diverse_documents`
  - `strategy` (`nirmiq_ehr_hybrid|nirmiq_ehr_bm25|nirmiq_ehr_vector`)
  - `retrieval_method` (`nirmiq_evidence_first_hierarchical_hybrid_rag`)
  - `requested_retrieval_mode`
  - `effective_retrieval_mode`
  - `cache_hit`
  - `detected_intent`
  - `intent_confidence`
  - `intent_route`
  - `citation_coverage`
  - `citation_sentence_count`
  - `citation_anchor_count`
  - `paper_lab` for paper-draft intent, including outline, citation clusters, and related-work matrix.

### Retrieval Tuning
- `RETRIEVAL_MAX_CONTEXT_TOKENS` bounds synthesis context size.
- `RETRIEVAL_MIN_GROUNDING_SCORE` determines abstention threshold.
- `RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT` limits repeated chunks from the same source during final rerank.
- `LOW_MEMORY_MODE=true` keeps the local runtime optimized for consumer GPUs.
- `NIRMIQ_RUNTIME_PROFILE=auto|balanced|low_memory|cpu_offline` applies coherent local defaults; explicit tuning variables still override the selected profile.
- `OLLAMA_KEEP_ALIVE`, `OLLAMA_NUM_CTX`, `OLLAMA_NUM_PREDICT`, `OLLAMA_NUM_GPU`, `OLLAMA_NUM_THREAD`, and `OLLAMA_EMBED_BATCH_SIZE` tune Ollama memory pressure without changing public APIs.

### `GET /ingest/{document_id}`
- Response:
  - `document_id: string`
  - `status: string`
  - `source_path: string`
  - `title?: string`
  - `active_chunk_count: number`
  - `latest_job?: { stage, status, error?, started_at, finished_at? }`

### `GET /ingest/{document_id}/jobs`
- Response:
  - `document_id: string`
  - `jobs: [{ stage, status, error?, started_at, finished_at? }]`

### `GET /memory/{session_id}`
- Response:
  - `session_id: string`
  - `summary: string`
  - `message_count: number`
- Behavior:
  - Summary is sourced from latest memory snapshot when available.
  - Snapshots are auto-refreshed after query turns based on configured message interval.

### `GET /memory/{session_id}/timeline`
- Response:
  - `session_id: string`
  - `summary: string`
  - `message_count: number`
  - `latest_snapshot_created_at?: string`
  - `messages: SessionTimelineMessage[]`
- `SessionTimelineMessage`:
  - `id: string`
  - `role: "user" | "assistant" | "system"`
  - `content: string`
  - `created_at: string`
  - `citations: Citation[]`
  - `retrieval_meta?: object`
- Behavior:
  - Returns the recent session turn history in chronological order.
  - Includes stored citations and retrieval metadata for assistant turns.
  - Reuses the same SQLite `messages` table as query persistence.

### `POST /memory/{session_id}/feedback`
- Request:
  - `rating: "good" | "needs_work"`
  - `query: string`
  - `answer: string`
  - `document_id?: string`
  - `source_title?: string`
  - `reason?: string`
- Response:
  - `id: string`
  - `session_id: string`
  - `rating: "good" | "needs_work"`
  - `query: string`
  - `answer: string`
  - `document_id?: string | null`
  - `source_title?: string | null`
  - `reason?: string | null`
  - `created_at: string`
- Behavior:
  - Saves local answer-quality feedback for retrieval and synthesis tuning.
  - Does not send feedback to analytics, cloud APIs, or model training.
  - Creates the session row if it does not already exist.

### `GET /memory/{session_id}/feedback`
- Query:
  - `limit?: number` default `50`, maximum `200`
- Response:
  - `session_id: string`
  - `items: AnswerFeedbackItem[]`
- Behavior:
  - Lists recent local answer feedback for review or eval-label creation.
  - Clearing a session removes its feedback records.

### `GET /documents`
- Response:
  - `items: DocumentItem[]`
  - `DocumentItem`:
    - `id: string`
    - `title?: string`
    - `status: string`
    - `source_path: string`
    - `active_chunk_count: number`
    - `updated_at: string`

### `GET /documents/{document_id}`
- Response:
  - `id: string`
  - `title?: string`
  - `status: string`
  - `source_path: string`
  - `active_chunk_count: number`
  - `updated_at: string`
  - `chunks: DocumentChunkItem[]`
- `DocumentChunkItem`:
  - `id: string`
  - `document_id: string`
  - `index_version: number`
  - `chunk_index: number`
  - `page_start?: number`
  - `page_end?: number`
  - `text: string`
  - `token_count: number`
  - `chunk_hash: string`
  - `is_active: boolean`
  - `created_at: string`
- Behavior:
  - Returns all chunks for the document, ordered by chunk index.
  - Lets the UI drill down from citations into corpus source detail.

## Notes
- Phase 1 endpoints are stable contracts with scaffolded internals.
- Advanced retrieval/indexing behavior will be implemented behind these contracts in Phase 2.
