import { PRODUCT_NAME, PRODUCT_TAGLINE } from "../app/page-model";

type ThreadHeaderProps = {
  activeMaterialName: string;
  activeWorkspaceLabel: string;
  hasSelectedDocument: boolean;
  onToggleInspector: () => void;
  onToggleLibrary: () => void;
  showInspector: boolean;
  showLibrary: boolean;
};

export function ThreadHeader({
  activeMaterialName,
  activeWorkspaceLabel,
  hasSelectedDocument,
  onToggleInspector,
  onToggleLibrary,
  showInspector,
  showLibrary,
}: ThreadHeaderProps) {
  return (
    <header className="thread-top">
      <div className="thread-bar">
        <div className="brand-lockup app">
          <div className="brand-mark" aria-hidden="true">
            <img alt="" src="/brand/nirmiq-ais-mark.svg" />
          </div>
          <div>
            <strong>{PRODUCT_NAME}</strong>
            <span>{PRODUCT_TAGLINE}</span>
          </div>
        </div>
        <div className="thread-title compact">
          <h1>Ask NIRMIQ</h1>
          <p className="tiny">Local answers from your material, with sources when evidence exists.</p>
        </div>
        <div className="top-actions">
          <button className="button ghost" type="button" onClick={onToggleLibrary}>
            {showLibrary ? "Hide Library" : "Library"}
          </button>
          <button className="button ghost" type="button" onClick={onToggleInspector}>
            {showInspector ? "Hide Sources" : "Sources"}
          </button>
        </div>
      </div>
      <div className="route-strip">
        <span className="source-pill">{hasSelectedDocument ? activeMaterialName : "No document selected"}</span>
        <span className="route-chip">{activeWorkspaceLabel}</span>
        <span className="route-hint">sources stay tucked away until needed</span>
      </div>
    </header>
  );
}
