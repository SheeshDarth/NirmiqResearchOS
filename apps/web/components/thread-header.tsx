import { PRODUCT_NAME } from "../app/page-model";

type ThreadHeaderProps = {
  activeMaterialName: string;
  activeWorkspaceLabel: string;
  hasSelectedDocument: boolean;
  onToggleInspector: () => void;
  onToggleLibrary: () => void;
  showInspector: boolean;
  showLibrary: boolean;
};

function MenuIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

export function ThreadHeader({
  activeMaterialName,
  activeWorkspaceLabel,
  hasSelectedDocument,
  onToggleInspector,
  onToggleLibrary,
  showInspector,
  showLibrary,
}: ThreadHeaderProps) {
  const inspectorLabel =
    activeWorkspaceLabel === "Paper Lab"
      ? "Paper tools"
      : activeWorkspaceLabel === "Exam Lab"
        ? "Exam tools"
        : showInspector
          ? "Close sources"
          : "Sources";

  return (
    <header className="thread-top">
      <div className="thread-bar">
        <button
          aria-expanded={showLibrary}
          aria-label={showLibrary ? "Close navigation" : "Open navigation"}
          className="header-icon-button"
          onClick={onToggleLibrary}
          type="button"
        >
          <MenuIcon />
        </button>

        <div className="header-context">
          <div className="header-brand-line">
            <img alt="" aria-hidden="true" src="/brand/nirmiq-ais-mark.svg" />
            <strong>{PRODUCT_NAME}</strong>
            <span>{activeWorkspaceLabel}</span>
          </div>
          <p title={hasSelectedDocument ? activeMaterialName : undefined}>
            {hasSelectedDocument ? activeMaterialName : "No source attached"}
          </p>
        </div>

        <button
          aria-expanded={showInspector}
          className="header-source-button"
          onClick={onToggleInspector}
          type="button"
        >
          {inspectorLabel}
        </button>
      </div>
    </header>
  );
}
