import type { ChangeEvent, FormEvent, KeyboardEvent, RefObject } from "react";

import {
  RETRIEVAL_PROFILES,
  WORKSPACE_SECTIONS,
  cx,
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

function AttachIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 19V5M6.5 10.5 12 5l5.5 5.5" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m8 10 4 4 4-4" />
    </svg>
  );
}

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
  const statusText =
    busy === "ingest"
      ? "Uploading and indexing..."
      : busy === "query"
        ? "Reading local sources..."
        : busy === "demo"
          ? "Preparing local demo..."
          : "Local and private";

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

        {composerCollapsed ? (
          <button className="composer-minimized" onClick={() => onComposerCollapsedChange(false)} type="button">
            Ask another question
          </button>
        ) : (
          <>
            {hasSelectedDocument ? (
              <button className="attached-source" onClick={onShowLibrary} title={activeMaterialName} type="button">
                <span className="attached-source-dot" />
                <span>{activeMaterialName}</span>
              </button>
            ) : null}

            <div className="composer-input-shell">
              <button
                aria-label="Attach a PDF, document, or image"
                className="attach-button"
                disabled={busy !== ""}
                onClick={requestUpload}
                title="Attach file"
                type="button"
              >
                <AttachIcon />
              </button>
              <textarea
                aria-label="Message NIRMIQ"
                className="textarea"
                ref={queryInputRef}
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                onKeyDown={onQueryKeyDown}
                placeholder={busy === "ingest" ? "Uploading and indexing your file..." : activePlaceholder}
                rows={1}
              />
              <button
                aria-label={busy === "query" ? "NIRMIQ is answering" : activeActionLabel}
                className="send-button"
                disabled={!canQuery || busy !== ""}
                title={activeActionLabel}
                type="submit"
              >
                {busy === "query" ? <span className="send-spinner" /> : <SendIcon />}
              </button>
            </div>

            <div className="composer-footer">
              <details className="composer-mode">
                <summary aria-label={`Current workspace: ${activeWorkspaceLabel}`}>
                  <span>{activeWorkspaceLabel}</span>
                  <ChevronIcon />
                </summary>
                <div className="composer-mode-menu" role="menu">
                  {WORKSPACE_SECTIONS.map((section) => (
                    <button
                      aria-current={workspaceSection === section.value ? "true" : undefined}
                      className={cx("composer-mode-option", workspaceSection === section.value && "active")}
                      key={section.value}
                      onClick={(event) => {
                        onWorkspaceSectionChange(section.value);
                        event.currentTarget.closest("details")?.removeAttribute("open");
                      }}
                      role="menuitem"
                      type="button"
                    >
                      <span>{section.label}</span>
                      <small>{section.hint}</small>
                    </button>
                  ))}
                </div>
              </details>

              <span className="composer-runtime-state" aria-live="polite">{statusText}</span>

              <details className="composer-more">
                <summary>More</summary>
                <div className="composer-more-menu">
                  {workspaceSection === "exam" ? (
                    <button disabled={busy !== ""} onClick={onGenerateExamPdf} type="button">
                      Generate custom PDF
                    </button>
                  ) : null}
                  <button disabled={!documentId || busy !== ""} onClick={onSummarizeSelectedSource} type="button">
                    Summarize source
                  </button>
                  <button disabled={!canExportCurrentRun || busy !== ""} onClick={onExportCurrentRun} type="button">
                    Export answer
                  </button>
                  <button onClick={onOpenSources} type="button">
                    {latestCitationCount ? `Open sources (${latestCitationCount})` : "Open sources"}
                  </button>
                  <button onClick={onShowLibrary} type="button">Open library</button>
                  <button onClick={() => onComposerCollapsedChange(true)} type="button">Minimize composer</button>
                  <button onClick={onClearThread} type="button">New conversation</button>

                  <details className="composer-settings">
                    <summary>Advanced routing</summary>
                    <div className="composer-meta">
                      <label className="label">
                        Thread
                        <input className="input" value={sessionId} onChange={(event) => onSessionIdChange(event.target.value)} />
                      </label>
                      <label className="label">
                        Answer type
                        <select className="select" value={studyMode} onChange={(event) => onStudyModeChange(event.target.value as StudyMode)}>
                          {availableModes.map((mode) => (
                            <option key={mode.value} value={mode.value}>{mode.label}</option>
                          ))}
                        </select>
                      </label>
                      <label className="label">
                        Retrieval
                        <select className="select" value={retrievalMode} onChange={(event) => onRetrievalModeChange(event.target.value as RetrievalMode)}>
                          <option value="hybrid">Hybrid</option>
                          <option value="bm25">BM25</option>
                          <option value="vector">Vector</option>
                        </select>
                      </label>
                      <label className="label">
                        Profile
                        <select className="select" value={retrievalProfile} onChange={(event) => onRetrievalProfileChange(event.target.value as RetrievalProfile)}>
                          {RETRIEVAL_PROFILES.map((profile) => (
                            <option key={profile.value} value={profile.value}>{profile.label}</option>
                          ))}
                        </select>
                      </label>
                    </div>
                  </details>
                </div>
              </details>
            </div>
            <p className="composer-disclaimer">NIRMIQ can make mistakes. Verify important claims in Sources.</p>
            <span className="sr-only">Current mode: {activeWorkspaceLabel}</span>
          </>
        )}
      </div>
    </form>
  );
}
