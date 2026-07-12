import type { RefObject } from "react";

import type { AnswerFeedbackRating, QueryResponse } from "../lib/api-client";
import {
  type BusyState,
  type ChatRun,
  cx,
  getTrustCopy,
  getVerificationBadge,
} from "../app/page-model";
import { AnswerBody } from "./answer-body";
import { StudyGuideAnswer } from "./study-guide-answer";

type ChatThreadProps = {
  busy: BusyState;
  chatEndRef: RefObject<HTMLDivElement | null>;
  onOpenSources: (response: QueryResponse) => void;
  onRateAnswer: (run: ChatRun, runKey: string, rating: AnswerFeedbackRating) => void;
  queryHistory: ChatRun[];
  savedFeedback: Record<string, AnswerFeedbackRating>;
};

function CopyIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <rect height="13" rx="2" width="13" x="8" y="8" />
      <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" />
    </svg>
  );
}

export function ChatThread({
  busy,
  chatEndRef,
  onOpenSources,
  onRateAnswer,
  queryHistory,
  savedFeedback,
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
              <div className="answer">{run.query}</div>
            </div>

            <div className="assistant-message">
              <div className="assistant-avatar" aria-hidden="true">
                <img alt="" src="/brand/nirmiq-ais-mark.svg" />
              </div>
              <div className="assistant-content">
                {run.mode === "study_guide" ? (
                  <StudyGuideAnswer answer={run.response.answer} />
                ) : (
                  <AnswerBody answer={run.response.answer} />
                )}

                <div className="answer-actions">
                  {verificationBadge ? (
                    <span className={cx("trust-badge", verificationBadge.className)} title={getTrustCopy(run.response)}>
                      {verificationBadge.label}
                    </span>
                  ) : null}
                  {run.response.citations.length ? (
                    <button className="answer-action" onClick={() => onOpenSources(run.response)} type="button">
                      Sources <span>{run.response.citations.length}</span>
                    </button>
                  ) : null}
                  <button
                    aria-label="Copy answer"
                    className="answer-icon-action"
                    onClick={() => void navigator.clipboard.writeText(run.response.answer)}
                    title="Copy answer"
                    type="button"
                  >
                    <CopyIcon />
                  </button>
                  <details className="answer-more">
                    <summary>Feedback</summary>
                    <div className="feedback-popover">
                      <span>{feedbackRating ? "Saved locally" : "Was this useful?"}</span>
                      <button
                        className={cx("feedback-button", feedbackRating === "good" && "active")}
                        disabled={busy !== "" || Boolean(feedbackRating)}
                        onClick={() => onRateAnswer(run, runKey, "good")}
                        type="button"
                      >
                        Helpful
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
                  </details>
                </div>
              </div>
            </div>
          </article>
        );
      })}

      {busy === "query" ? (
        <article className="turn pending-turn" aria-live="polite" aria-label="NIRMIQ is reading your sources">
          <div className="assistant-message pending">
            <div className="assistant-avatar" aria-hidden="true">
              <img alt="" src="/brand/nirmiq-ais-mark.svg" />
            </div>
            <p className="pending-copy">Reading the selected material and checking the evidence...</p>
          </div>
        </article>
      ) : null}
      <div ref={chatEndRef} />
    </div>
  );
}
