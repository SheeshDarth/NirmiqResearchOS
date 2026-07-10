import type { RefObject } from "react";

import type { AnswerFeedbackRating, QueryResponse } from "../lib/api-client";
import {
  type BusyState,
  type ChatRun,
  cx,
  formatDate,
  getTrustCopy,
  getVerificationBadge,
  previewText,
} from "../app/page-model";
import { AnswerBody } from "./answer-body";
import { StudyGuideAnswer } from "./study-guide-answer";

type ChatThreadProps = {
  busy: BusyState;
  chatEndRef: RefObject<HTMLDivElement | null>;
  onOpenSources: (response: QueryResponse) => void;
  onRateAnswer: (run: ChatRun, runKey: string, rating: AnswerFeedbackRating) => void;
  onSelectCitation: (documentId: string, chunkId: string) => void;
  queryHistory: ChatRun[];
  savedFeedback: Record<string, AnswerFeedbackRating>;
  selectedChunkId: string;
};

function formatCitationPage(pageStart?: number | null, pageEnd?: number | null) {
  if (!pageStart) return "Page not tagged";
  if (pageEnd && pageEnd !== pageStart) return `Pages ${pageStart}-${pageEnd}`;
  return `Page ${pageStart}`;
}

export function ChatThread({
  busy,
  chatEndRef,
  onOpenSources,
  onRateAnswer,
  onSelectCitation,
  queryHistory,
  savedFeedback,
  selectedChunkId,
}: ChatThreadProps) {
  return (
    <div className="turn-list">
      {queryHistory.map((run) => {
        const runKey = run.timestamp;
        const feedbackRating = savedFeedback[runKey];
        const verificationBadge = getVerificationBadge(run.response);

        return (
          <article className="turn" key={runKey}>
            <div className="bubble user">
              <div className="message-meta">
                <span className="tiny">You</span>
              </div>
              <div className="answer">{run.query}</div>
            </div>
            <div className="bubble assistant">
              <div className="message-meta">
                <span className="tiny">NIRMIQ / {formatDate(run.timestamp)}</span>
                {verificationBadge ? (
                  <span className={cx("trust-badge", verificationBadge.className)}>
                    {verificationBadge.label}
                  </span>
                ) : null}
              </div>
              {run.mode === "study_guide" ? (
                <StudyGuideAnswer answer={run.response.answer} />
              ) : (
                <AnswerBody answer={run.response.answer} />
              )}
              <div className="trust-line">
                <span className={cx("trust-copy", run.response.grounded ? "sage" : "copper")}>
                  {getTrustCopy(run.response)}
                </span>
                <button
                  className="clear-link"
                  onClick={() => onOpenSources(run.response)}
                  type="button"
                >
                  Open Sources
                </button>
              </div>
              <div className="feedback-row" aria-label="Answer feedback">
                <span>{feedbackRating ? "Saved for local quality review" : "Was this useful?"}</span>
                <button
                  className={cx("feedback-button", feedbackRating === "good" && "active")}
                  disabled={busy !== "" || Boolean(feedbackRating)}
                  onClick={() => onRateAnswer(run, runKey, "good")}
                  type="button"
                >
                  Good
                </button>
                <button
                  className={cx("feedback-button", feedbackRating === "needs_work" && "active")}
                  disabled={busy !== "" || Boolean(feedbackRating)}
                  onClick={() => onRateAnswer(run, runKey, "needs_work")}
                  type="button"
                >
                  Needs work
                </button>
              </div>
              {run.response.citations.length ? (
                <details className="source-drawer">
                  <summary>
                    Sources used
                    <span>{run.response.citations.length}</span>
                  </summary>
                  <p className="source-drawer-hint">Tap a source to open the exact passage in Sources.</p>
                  <div className="source-preview-list">
                    {run.response.citations.slice(0, 4).map((citation, citationIndex) => (
                      <button
                        aria-label={`Open source ${citationIndex + 1}, ${formatCitationPage(citation.page_start, citation.page_end)}`}
                        className={cx("source-preview-card", citation.chunk_id === selectedChunkId && "active")}
                        key={`${run.timestamp}-${citation.chunk_id}-${citationIndex}`}
                        onClick={() => onSelectCitation(citation.document_id, citation.chunk_id)}
                        type="button"
                      >
                        <span className="source-preview-meta">
                          Source {citationIndex + 1}
                          <span>{formatCitationPage(citation.page_start, citation.page_end)}</span>
                        </span>
                        <span className="source-preview-text">
                          {citation.excerpt
                            ? previewText(citation.excerpt, 220)
                            : "Open Sources to inspect this supporting passage."}
                        </span>
                      </button>
                    ))}
                  </div>
                </details>
              ) : null}
            </div>
          </article>
        );
      })}
      <div ref={chatEndRef} />
    </div>
  );
}
