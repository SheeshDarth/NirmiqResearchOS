const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error("Health check failed");
  }
  return response.json() as Promise<{ status: string }>;
}

export type IngestResponse = {
  document_id: string;
  status: string;
  indexed: boolean;
};

export type IngestStatusResponse = {
  document_id: string;
  status: string;
  source_path: string;
  title?: string;
  active_chunk_count: number;
  latest_job?: {
    stage: string;
    status: string;
    error?: string | null;
    started_at: string;
    finished_at?: string | null;
  } | null;
};

export type IngestJobsResponse = {
  document_id: string;
  jobs: Array<{
    stage: string;
    status: string;
    error?: string | null;
    started_at: string;
    finished_at?: string | null;
  }>;
};

export type QueryResponse = {
  session_id: string;
  answer: string;
  grounded: boolean;
  citations: Array<{
    document_id: string;
    chunk_id: string;
    page_start?: number | null;
    page_end?: number | null;
    score?: number | null;
    excerpt?: string | null;
  }>;
  retrieval_meta?: Record<string, unknown> | null;
};

export type SessionSummaryResponse = {
  session_id: string;
  summary: string;
  message_count: number;
};

export type SessionTimelineResponse = {
  session_id: string;
  summary: string;
  message_count: number;
  latest_snapshot_created_at?: string | null;
  messages: Array<{
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    created_at: string;
    citations: Array<{
      document_id: string;
      chunk_id: string;
      page_start?: number | null;
      page_end?: number | null;
      score?: number | null;
      excerpt?: string | null;
    }>;
    retrieval_meta?: Record<string, unknown> | null;
  }>;
};

export type DocumentItem = {
  id: string;
  title?: string | null;
  status: string;
  source_path: string;
  active_chunk_count: number;
  updated_at: string;
};

export type DocumentListResponse = {
  items: DocumentItem[];
};

export type DocumentDetailResponse = DocumentItem & {
  chunks: Array<{
    id: string;
    document_id: string;
    index_version: number;
    chunk_index: number;
    page_start?: number | null;
    page_end?: number | null;
    text: string;
    token_count: number;
    chunk_hash: string;
    is_active: boolean;
    created_at: string;
  }>;
};

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export async function ingestDocument(payload: {
  source_path: string;
  title?: string;
  mime_type?: string;
  force_reindex?: boolean;
}): Promise<IngestResponse> {
  const response = await fetch(`${API_BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<IngestResponse>(response);
}

export async function getIngestStatus(documentId: string): Promise<IngestStatusResponse> {
  const response = await fetch(`${API_BASE}/ingest/${encodeURIComponent(documentId)}`);
  return parseJson<IngestStatusResponse>(response);
}

export async function getIngestJobs(documentId: string): Promise<IngestJobsResponse> {
  const response = await fetch(`${API_BASE}/ingest/${encodeURIComponent(documentId)}/jobs`);
  return parseJson<IngestJobsResponse>(response);
}

export async function runQuery(payload: {
  session_id: string;
  query: string;
  document_id?: string;
  mode?: string;
  retrieval_profile?: "fast" | "balanced" | "precision";
  retrieval_mode: "hybrid" | "bm25" | "vector";
  debug?: boolean;
}): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<QueryResponse>(response);
}

export async function getMemorySummary(sessionId: string): Promise<SessionSummaryResponse> {
  const response = await fetch(`${API_BASE}/memory/${encodeURIComponent(sessionId)}`);
  return parseJson<SessionSummaryResponse>(response);
}

export async function getSessionTimeline(sessionId: string): Promise<SessionTimelineResponse> {
  const response = await fetch(`${API_BASE}/memory/${encodeURIComponent(sessionId)}/timeline`);
  return parseJson<SessionTimelineResponse>(response);
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const response = await fetch(`${API_BASE}/documents`);
  return parseJson<DocumentListResponse>(response);
}

export async function getDocument(documentId: string): Promise<DocumentDetailResponse> {
  const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(documentId)}`);
  return parseJson<DocumentDetailResponse>(response);
}
