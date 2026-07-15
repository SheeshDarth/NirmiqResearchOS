const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export function diagramAssetUrl(assetId: string): string {
  return `${API_BASE}/exam/diagrams/assets/${encodeURIComponent(assetId)}`;
}

export async function healthCheck(): Promise<{ status: string }> {
  const response = await apiFetch(`${API_BASE}/health`);
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

export type SessionDeleteResponse = {
  session_id: string;
  deleted: boolean;
  deleted_messages: number;
  deleted_snapshots: number;
};

export type AnswerFeedbackRating = "good" | "needs_work";

export type AnswerFeedbackItem = {
  id: string;
  session_id: string;
  rating: AnswerFeedbackRating;
  query: string;
  answer: string;
  document_id?: string | null;
  source_title?: string | null;
  reason?: string | null;
  created_at: string;
};

export type AnswerFeedbackListResponse = {
  session_id: string;
  items: AnswerFeedbackItem[];
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

export type DocumentDeleteResponse = {
  document_id: string;
  deleted: boolean;
};

export type DocumentPurgeResponse = {
  deleted_count: number;
  deleted_document_ids: string[];
  vector_store_cleared: boolean;
  source_files_deleted: boolean;
  source_file_delete_count: number;
  derived_files_deleted: number;
  note: string;
};

export type SessionPurgeResponse = {
  deleted_sessions: number;
  deleted_messages: number;
  deleted_snapshots: number;
  deleted_feedback: number;
  deleted_exam_profiles: number;
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

export type ExamProfileItem = {
  id: string;
  session_id: string;
  document_id: string;
  title: string;
  marks: number;
  answer_style: string;
  content_type: string;
  instructions?: string | null;
  created_at: string;
  updated_at: string;
};

export type QuestionBankItem = {
  id: string;
  document_id: string;
  question: string;
  marks?: number | null;
  source_label?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  created_at: string;
};

export type QuestionBankImportResponse = {
  document_id: string;
  imported_count: number;
  items: QuestionBankItem[];
};

export type DiagramAssetItem = {
  id: string;
  document_id: string;
  page_number: number;
  image_index: number;
  image_path: string;
  width?: number | null;
  height?: number | null;
  caption?: string | null;
  created_at: string;
};

export type DiagramExtractionResponse = {
  document_id: string;
  extracted_count: number;
  assets: DiagramAssetItem[];
};

async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = 120_000,
): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, {
      ...init,
      signal: init.signal ?? controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        "NIRMIQ local runtime took too long to respond. Check that FastAPI, Next.js, and Ollama are running, then retry.",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

async function errorMessageFromResponse(response: Response): Promise<string> {
  const body = await response.text();
  if (!body.trim()) {
    return `HTTP ${response.status}: ${response.statusText || "Request failed"}`;
  }
  try {
    const parsed = JSON.parse(body) as { detail?: unknown; message?: unknown };
    const detail = parsed.detail ?? parsed.message;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  } catch {
    // Fall through to raw text below.
  }
  return `HTTP ${response.status}: ${body}`;
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.json() as Promise<T>;
}

export async function ingestDocument(payload: {
  source_path: string;
  title?: string;
  mime_type?: string;
  force_reindex?: boolean;
}): Promise<IngestResponse> {
  const response = await apiFetch(`${API_BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<IngestResponse>(response);
}

export async function uploadDocument(payload: {
  file: File;
  title?: string;
  force_reindex?: boolean;
}): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("file", payload.file);
  if (payload.title?.trim()) {
    formData.append("title", payload.title.trim());
  }
  formData.append("force_reindex", String(payload.force_reindex ?? true));

  const response = await apiFetch(`${API_BASE}/ingest/upload`, {
    method: "POST",
    body: formData,
  });
  return parseJson<IngestResponse>(response);
}

export async function getIngestStatus(documentId: string): Promise<IngestStatusResponse> {
  const response = await apiFetch(`${API_BASE}/ingest/${encodeURIComponent(documentId)}`);
  return parseJson<IngestStatusResponse>(response);
}

export async function getIngestJobs(documentId: string): Promise<IngestJobsResponse> {
  const response = await apiFetch(`${API_BASE}/ingest/${encodeURIComponent(documentId)}/jobs`);
  return parseJson<IngestJobsResponse>(response);
}

export async function runQuery(payload: {
  session_id: string;
  query: string;
  document_id?: string;
  mode?: string;
  retrieval_profile?: "fast" | "balanced" | "precision";
  retrieval_mode: "hybrid" | "bm25" | "vector";
  exam_profile?: {
    marks: number;
    answer_style: string;
    content_type: string;
    instructions?: string;
  };
  debug?: boolean;
}): Promise<QueryResponse> {
  const response = await apiFetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<QueryResponse>(response);
}

export async function getMemorySummary(sessionId: string): Promise<SessionSummaryResponse> {
  const response = await apiFetch(`${API_BASE}/memory/${encodeURIComponent(sessionId)}`);
  return parseJson<SessionSummaryResponse>(response);
}

export async function getSessionTimeline(sessionId: string): Promise<SessionTimelineResponse> {
  const response = await apiFetch(`${API_BASE}/memory/${encodeURIComponent(sessionId)}/timeline`);
  return parseJson<SessionTimelineResponse>(response);
}

export async function exportSessionMarkdown(sessionId: string): Promise<string> {
  const response = await apiFetch(`${API_BASE}/memory/${encodeURIComponent(sessionId)}/export`);
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.text();
}

export async function deleteSession(sessionId: string): Promise<SessionDeleteResponse> {
  const response = await apiFetch(`${API_BASE}/memory/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  return parseJson<SessionDeleteResponse>(response);
}

export async function saveAnswerFeedback(
  sessionId: string,
  payload: {
    rating: AnswerFeedbackRating;
    query: string;
    answer: string;
    document_id?: string;
    source_title?: string;
    reason?: string;
  },
): Promise<AnswerFeedbackItem> {
  const response = await apiFetch(`${API_BASE}/memory/${encodeURIComponent(sessionId)}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<AnswerFeedbackItem>(response);
}

export async function listAnswerFeedback(
  sessionId: string,
  limit = 50,
): Promise<AnswerFeedbackListResponse> {
  const response = await apiFetch(
    `${API_BASE}/memory/${encodeURIComponent(sessionId)}/feedback?limit=${encodeURIComponent(String(limit))}`,
  );
  return parseJson<AnswerFeedbackListResponse>(response);
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const response = await apiFetch(`${API_BASE}/documents`);
  return parseJson<DocumentListResponse>(response);
}

export async function getDocument(documentId: string): Promise<DocumentDetailResponse> {
  const response = await apiFetch(`${API_BASE}/documents/${encodeURIComponent(documentId)}`);
  return parseJson<DocumentDetailResponse>(response);
}

export async function deleteDocument(documentId: string): Promise<DocumentDeleteResponse> {
  const response = await apiFetch(`${API_BASE}/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
  });
  return parseJson<DocumentDeleteResponse>(response);
}

export async function purgeDocuments(): Promise<DocumentPurgeResponse> {
  const response = await apiFetch(`${API_BASE}/documents`, {
    method: "DELETE",
  });
  return parseJson<DocumentPurgeResponse>(response);
}

export async function purgeSessions(): Promise<SessionPurgeResponse> {
  const response = await apiFetch(`${API_BASE}/memory`, {
    method: "DELETE",
  });
  return parseJson<SessionPurgeResponse>(response);
}

export async function upsertExamProfile(payload: {
  session_id: string;
  document_id: string;
  title: string;
  marks: number;
  answer_style: string;
  content_type: string;
  instructions?: string;
}): Promise<ExamProfileItem> {
  const response = await apiFetch(`${API_BASE}/exam/profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<ExamProfileItem>(response);
}

export async function importQuestionBank(payload: {
  document_id: string;
  raw_text: string;
}): Promise<QuestionBankImportResponse> {
  const response = await apiFetch(`${API_BASE}/exam/question-bank/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<QuestionBankImportResponse>(response);
}

export async function listQuestionBank(documentId: string): Promise<QuestionBankItem[]> {
  const response = await apiFetch(`${API_BASE}/exam/question-bank/${encodeURIComponent(documentId)}`);
  return parseJson<QuestionBankItem[]>(response);
}

export async function extractDiagrams(payload: {
  document_id: string;
  force?: boolean;
}): Promise<DiagramExtractionResponse> {
  const response = await apiFetch(`${API_BASE}/exam/diagrams/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<DiagramExtractionResponse>(response);
}

export async function listDiagrams(documentId: string): Promise<DiagramAssetItem[]> {
  const response = await apiFetch(`${API_BASE}/exam/diagrams/${encodeURIComponent(documentId)}`);
  return parseJson<DiagramAssetItem[]>(response);
}
