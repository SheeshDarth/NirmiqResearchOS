import type { BusyState, StudyMode, WorkspaceSection } from "../app/page-model";

type ChatEmptyStateProps = {
  busy: BusyState;
  onLoadGoldenDemo: () => void;
  onSuggestion: (section: WorkspaceSection, mode: StudyMode, query: string) => void;
};

export function ChatEmptyState({ busy, onLoadGoldenDemo, onSuggestion }: ChatEmptyStateProps) {
  return (
    <section className="empty-state">
      <p className="eyebrow">Upload. Understand. Verify. Learn.</p>
      <h2>What do you want to understand today?</h2>
      <p className="copy">
        Upload a PDF, select one document, then ask naturally. The technical trail stays hidden until you open Sources.
      </p>
      <div className="first-run-steps" aria-label="How to use NIRMIQ">
        <span><strong>1</strong> Upload material</span>
        <span><strong>2</strong> Ask naturally</span>
        <span><strong>3</strong> Verify sources</span>
      </div>
      <div className="golden-path-panel">
        <div>
          <p className="eyebrow">Reviewer path</p>
          <strong>Try the local golden demo</strong>
          <span>Seed corpus, locked prompts, citations, export, and source removal.</span>
        </div>
        <button className="button primary" type="button" onClick={onLoadGoldenDemo} disabled={busy !== ""}>
          {busy === "demo" ? "Loading..." : "Load demo"}
        </button>
      </div>
      <div className="suggestions">
        <button
          className="button ghost"
          onClick={() => onSuggestion("research", "research", "Explain this topic simply from my study material.")}
          type="button"
        >
          Explain this topic simply
        </button>
        <button
          className="button ghost"
          onClick={() => onSuggestion("exam", "exam_answer", "Make this into a 10-mark exam answer.")}
          type="button"
        >
          Make 10-mark exam answer
        </button>
        <button
          className="button ghost"
          onClick={() => onSuggestion("research", "summary", "Summarize selected document.")}
          type="button"
        >
          Summarize selected document
        </button>
        <button
          className="button ghost"
          onClick={() => onSuggestion("exam", "compare_concepts", "Compare concepts from my notes.")}
          type="button"
        >
          Compare concepts from my notes
        </button>
      </div>
    </section>
  );
}
