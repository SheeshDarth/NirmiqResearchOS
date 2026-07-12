import type { StudyMode, WorkspaceSection } from "../app/page-model";

type ChatEmptyStateProps = {
  hasSelectedDocument: boolean;
  onSuggestion: (section: WorkspaceSection, mode: StudyMode, query: string) => void;
};

const suggestions: Array<{
  label: string;
  mode: StudyMode;
  query: string;
  section: WorkspaceSection;
}> = [
  {
    label: "Explain a concept",
    mode: "research",
    query: "Explain the main concept clearly and cite the relevant passages.",
    section: "research",
  },
  {
    label: "Summarize the source",
    mode: "summary",
    query: "Summarize this document with its main ideas, methods, findings, and limitations.",
    section: "research",
  },
  {
    label: "Compare ideas",
    mode: "compare_concepts",
    query: "Compare the key ideas in this material and explain the differences clearly.",
    section: "exam",
  },
  {
    label: "Draft with citations",
    mode: "research_paper",
    query: "Draft a concise related-work section using evidence from the selected material.",
    section: "paper",
  },
];

export function ChatEmptyState({ hasSelectedDocument, onSuggestion }: ChatEmptyStateProps) {
  return (
    <section className="empty-state">
      <div className="empty-mark" aria-hidden="true">
        <img alt="" src="/brand/nirmiq-ais-mark.svg" />
      </div>
      <div className="empty-copy">
        <h1>{hasSelectedDocument ? "What should we find in this source?" : "Ask your material anything"}</h1>
        <p>
          {hasSelectedDocument
            ? "Ask naturally. NIRMIQ will answer from the selected material and show sources only when you open them."
            : "Attach a PDF, document, or image from the composer. Your material and answers stay on this device."}
        </p>
      </div>
      <div className="suggestions" aria-label="Suggested prompts">
        {suggestions.map((suggestion) => (
          <button
            className="suggestion-button"
            key={suggestion.label}
            onClick={() => onSuggestion(suggestion.section, suggestion.mode, suggestion.query)}
            type="button"
          >
            {suggestion.label}
          </button>
        ))}
      </div>
    </section>
  );
}
