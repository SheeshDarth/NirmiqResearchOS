import type { ChangeEvent, FormEvent, KeyboardEvent, RefObject } from "react";

import {
  RETRIEVAL_PROFILES,
  WORKSPACE_SECTIONS,
  cx,
  modeLabel,
  type BusyState,
  type RetrievalMode,
  type RetrievalProfile,
  type StudyMode,
  type WorkspaceSection,
} from "../app/page-model";

type ModeOption = {
  value: StudyMode;
  label: string;
};

type ChatComposerProps = {
  activeActionLabel: string;
  activeMaterialName: string;
  activePlaceholder: string;
  activeWorkspaceLabel: string;
  availableModes: ModeOption[];
  busy: BusyState;
  canExportCurrentRun: boolean;
  canQuery: boolean;
  composerCollapsed: boolean;
  documentId: string;
  hasSelectedDocument: boolean;
  latestCitationCount: number;
  onClearThread: () => void;
  onComposerCollapsedChange: (collapsed: boolean) => void;
  onExportCurrentRun: () => void;
  onGenerateExamPdf: () => void;
  onOpenSources: () => void;
  onQuery: (event: FormEvent<HTMLFormElement>) => void;
  onQueryChange: (value: string) => void;
  onQueryKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onRetrievalModeChange: (mode: RetrievalMode) => void;
  onRetrievalProfileChange: (profile: RetrievalProfile) => void;
  onSessionIdChange: (sessionId: string) => void;
  onShowLibrary: () => void;
  onStudyModeChange: (mode: StudyMode) => void;
  onSummarizeSelectedSource: () => void;
  onUploadFile: (event: ChangeEvent<HTMLInputElement>) => void;
  onWorkspaceSectionChange: (section: WorkspaceSection) => void;
  query: string;
  queryFormRef: RefObject<HTMLFormElement | null>;
  queryInputRef: RefObject<HTMLTextAreaElement | null>;
  retrievalMode: RetrievalMode;
  retrievalProfile: RetrievalProfile;
  sessionId: string;
  studyMode: StudyMode;
  uploadInputRef: RefObject<HTMLInputElement | null>;
  workspaceSection: WorkspaceSection;
};

export function ChatComposer({
  activeActionLabel,
  activeMaterialName,
  activePlaceholder,
  activeWorkspaceLabel,
  availableModes,
  busy,
  canExportCurrentRun,
  canQuery,
  composerCollapsed,
  documentId,
  hasSelectedDocument,
  latestCitationCount,
  onClearThread,
  onComposerCollapsedChange,
  onExportCurrentRun,
  onGenerateExamPdf,
  onOpenSources,
  onQuery,
  onQueryChange,
  onQueryKeyDown,
  onRetrievalModeChange,
  onRetrievalProfileChange,
  onSessionIdChange,
  onShowLibrary,
  onStudyModeChange,
  onSummarizeSelectedSource,
  onUploadFile,
  onWorkspaceSectionChange,
  query,
  queryFormRef,
  queryInputRef,
  retrievalMode,
  retrievalProfile,
  sessionId,
  studyMode,
  uploadInputRef,
  workspaceSection,
}: ChatComposerProps) {
  const requestUpload = () => uploadInputRef.current?.click();
  const sourceStatusLabel =
    busy === "ingest" ? "Uploading" : busy === "query" ? "Reading" : busy === "demo" ? "Loading" : "Using";
  const sourceStatusText =
    busy === "ingest"
      ? "Indexing your upload..."
      : busy === "query"
        ? "Checking selected sources..."
        : busy === "demo"
          ? "Preparing demo material..."
          : hasSelectedDocument
            ? activeMaterialName
            : "No material attached";
  const sourceDotState = busy === "ingest" || busy === "query" || busy === "demo" ? "working" : hasSelectedDocument ? "ok" : "";

  return (
    <form className={cx("composer-wrap", composerCollapsed && "collapsed")} ref={queryFormRef} onSubmit={onQuery}>
      <div className="composer-card">
        <input
          accept=".pdf,.txt,.md,.markdown,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,image/*,application/pdf,text/*"
          className="file-input"
          onChange={onUploadFile}
          ref={uploadInputRef}
          type="file"
        />
        <div className="source-cockpit">
          <div className="source-status" aria-live="polite">
            <span className={cx("source-dot", sourceDotState)} />
            <div>
              <span className="source-label">{sourceStatusLabel}</span>
              <strong>{sourceStatusText}</strong>
            </div>
          </div>
          <div className="source-actions">
            <button className="quick-action ghost" disabled={busy !== ""} onClick={requestUpload} type="button">
              Upload
            </button>
            <button className="quick-action ghost" onClick={onShowLibrary} type="button">
              Library
            </button>
          </div>
        </div>
        {composerCollapsed ? (
          <div className="composer-minimized">
            Composer minimized.
            <button className="clear-link" onClick={() => onComposerCollapsedChange(false)} type="button">
              Ask next
            </button>
          </div>
        ) : (
          <>
            <div className="composer-input-shell">
              <button
                aria-label="Upload file or photo"
                className="attach-button"
                disabled={busy !== ""}
                onClick={requestUpload}
                type="button"
                title="Upload PDF, document, or photo"
              >
                +
              </button>
              <textarea
                className="textarea"
                ref={queryInputRef}
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                onKeyDown={onQueryKeyDown}
                placeholder={busy === "ingest" ? "Uploading and indexing your file..." : activePlaceholder}
              />
              <button className="send-button" disabled={!canQuery || busy !== ""} type="submit">
                {busy === "query" ? "Reading" : activeActionLabel}
              </button>
            </div>
            <details className="composer-tools">
              <summary>
                Tools
                <span>{activeWorkspaceLabel} / {modeLabel(studyMode)}</span>
              </summary>
              <div className="tool-strip" aria-label="NIRMIQ tools">
                {WORKSPACE_SECTIONS.map((section) => (
                  <button
                    className={cx("tool-chip", workspaceSection === section.value && "active")}
                    data-testid={`workspace-${section.value}`}
                    key={section.value}
                    onClick={() => onWorkspaceSectionChange(section.value)}
                    type="button"
                    title={section.hint}
                  >
                    {section.label}
                  </button>
                ))}
              </div>
              <div className="source-actions expanded">
                {workspaceSection === "exam" ? (
                  <button className="quick-action" disabled={busy !== ""} onClick={onGenerateExamPdf} type="button">
                    Custom PDF
                  </button>
                ) : null}
                <button
                  className="quick-action"
                  disabled={!documentId || busy !== ""}
                  onClick={onSummarizeSelectedSource}
                  type="button"
                >
                  Summarize
                </button>
                <button
                  className="quick-action ghost"
                  disabled={!canExportCurrentRun || busy !== ""}
                  onClick={onExportCurrentRun}
                  type="button"
                >
                  Export
                </button>
                <button className="quick-action ghost" onClick={onOpenSources} type="button">
                  Sources
                </button>
                <button className="quick-action ghost" onClick={() => onComposerCollapsedChange(true)} type="button">
                  Minimize
                </button>
                <button className="quick-action ghost" type="button" onClick={onClearThread}>
                  New thread
                </button>
              </div>
              <details className="composer-settings compact-details">
                <summary>
                  Advanced
                  <span>optional</span>
                </summary>
                <div className="composer-meta">
                  <label className="label">
                    Thread
                    <input className="input" value={sessionId} onChange={(event) => onSessionIdChange(event.target.value)} />
                  </label>
                  <label className="label">
                    Route
                    <select
                      className="select"
                      value={studyMode}
                      onChange={(event) => onStudyModeChange(event.target.value as StudyMode)}
                    >
                      {availableModes.map((mode) => (
                        <option key={mode.value} value={mode.value}>
                          {mode.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="label">
                    Retrieval
                    <select
                      className="select"
                      value={retrievalMode}
                      onChange={(event) => onRetrievalModeChange(event.target.value as RetrievalMode)}
                    >
                      <option value="hybrid">Hybrid</option>
                      <option value="bm25">BM25</option>
                      <option value="vector">Vector</option>
                    </select>
                  </label>
                  <label className="label">
                    Profile
                    <select
                      className="select"
                      value={retrievalProfile}
                      onChange={(event) => onRetrievalProfileChange(event.target.value as RetrievalProfile)}
                    >
                      {RETRIEVAL_PROFILES.map((profile) => (
                        <option key={profile.value} value={profile.value}>
                          {profile.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </details>
              <p className="composer-hint">
                {latestCitationCount
                  ? `${latestCitationCount} evidence links ready. Open Sources to inspect citations.`
                  : "Answers stay grounded in the selected study material when evidence is available."}
              </p>
            </details>
          </>
        )}
      </div>
    </form>
  );
}
