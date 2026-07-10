import type { QueryResponse } from "../lib/api-client";
import { cx, previewText, type BusyState, type Chunk } from "../app/page-model";

type SourceEvidencePanelProps = {
  busy: BusyState;
  citedChunkIds: Set<string>;
  documentId: string;
  hasSelectedDocument: boolean;
  latestCitations: QueryResponse["citations"];
  onRefreshStatus: () => void;
  onSelectChunk: (chunkId: string) => void;
  onSelectCitation: (documentId: string, chunkId: string) => void;
  selectedChunk: Chunk | null;
  selectedChunkId: string;
  selectedTitle: string;
  visibleChunks: Chunk[];
};

export function SourceEvidencePanel({
  busy,
  citedChunkIds,
  documentId,
  hasSelectedDocument,
  latestCitations,
  onRefreshStatus,
  onSelectChunk,
  onSelectCitation,
  selectedChunk,
  selectedChunkId,
  selectedTitle,
  visibleChunks,
}: SourceEvidencePanelProps) {
  return (
    <section className="tool-panel rail-section">
      <div className="panel">
        <div className="section-head">
          <h2>{selectedTitle}</h2>
          <button className="button ghost" type="button" onClick={onRefreshStatus} disabled={!documentId || busy !== ""}>
            Refresh
          </button>
        </div>
        <p className="tiny">
          {hasSelectedDocument ? "Stored locally. Full path hidden for privacy." : "Select study material."}
        </p>
        <p className="copy source-status-copy">
          {hasSelectedDocument
            ? "Only answer-used passages are shown here. Technical ranking data stays hidden."
            : "Upload or select material to inspect source support."}
        </p>
      </div>

      {latestCitations.length ? (
        <div className="panel">
          <div className="section-head">
            <h2>Answer citations</h2>
            <span className="chip copper">{latestCitations.length}</span>
          </div>
          <div className="timeline-list" style={{ marginTop: 10 }}>
            {latestCitations.slice(0, 6).map((citation, index) => (
              <button
                className={cx("material-card source-citation-card", citation.chunk_id === selectedChunkId && "active")}
                key={`${citation.chunk_id}-${index}`}
                onClick={() => onSelectCitation(citation.document_id, citation.chunk_id)}
                type="button"
              >
                <span className="material-title">Source {index + 1}</span>
                <span className="tiny">
                  {citation.page_start ? `Page ${citation.page_start}` : "Page unknown"}
                </span>
                <span className="source-reason">Used in the answer</span>
                <span className="tiny">{previewText(citation.excerpt, 220)}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {selectedChunk ? (
        <div className="chunk-card active">
          <div className="chunk-head">
            <strong>Selected source passage</strong>
            <span className="chip">{selectedChunk.page_start ? `Page ${selectedChunk.page_start}` : "Page unknown"}</span>
          </div>
          <p className="chunk-text">{previewText(selectedChunk.text, 900)}</p>
        </div>
      ) : null}

      <details className="panel source-passages-details">
        <summary>
          More source passages
          <span>{visibleChunks.length} available</span>
        </summary>
        <div className="chunk-list" style={{ marginTop: 10 }}>
          {visibleChunks.length ? (
            visibleChunks.map((chunk) => (
              <button
                className={cx(
                  "chunk-card",
                  chunk.id === selectedChunkId && "active",
                  citedChunkIds.has(chunk.id) && "cited",
                )}
                key={chunk.id}
                onClick={() => onSelectChunk(chunk.id)}
                type="button"
              >
                <div className="chunk-head">
                  <strong>Passage</strong>
                  <span className="tiny">p.{chunk.page_start ?? "?"}-{chunk.page_end ?? "?"}</span>
                </div>
                <p className="chunk-text">{previewText(chunk.text, 330)}</p>
              </button>
            ))
          ) : (
            <div className="chunk-card">
              <strong>No evidence preview yet</strong>
              <p className="copy">Ask a question or select material to inspect chunks.</p>
            </div>
          )}
        </div>
      </details>
    </section>
  );
}
