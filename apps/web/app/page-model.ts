import type { DocumentDetailResponse, QueryResponse } from "../lib/api-client";

export type RetrievalMode = "hybrid" | "bm25" | "vector";
export type RetrievalProfile = "fast" | "balanced" | "precision";
export type WorkspaceSection = "research" | "general" | "paper" | "exam";
export type StudyMode =
  | "research"
  | "summary"
  | "deep_research"
  | "general_chat"
  | "research_paper"
  | "exam_answer"
  | "revision_notes"
  | "important_questions"
  | "compare_concepts"
  | "study_guide";
export type BusyState =
  | ""
  | "health"
  | "ingest"
  | "query"
  | "status"
  | "documents"
  | "delete"
  | "demo"
  | "privacy"
  | "feedback";
export type DeepView = "evidence" | "context" | "compare";
export type Chunk = DocumentDetailResponse["chunks"][number];

export type ChatRun = {
  session_id: string;
  query: string;
  mode: StudyMode;
  profile: RetrievalProfile;
  document_id?: string;
  source_title?: string;
  source_path?: string;
  response: QueryResponse;
  timestamp: string;
};

export type DiffLine = {
  kind: "same" | "added" | "removed";
  text: string;
};

export type GuideCard = {
  title: string;
  body: string[];
};

export type PaperLabMatrixRow = {
  claim_area?: string;
  evidence?: number;
  page?: number | null;
  source_type?: string;
  quality?: number;
  use_in_paper?: string;
  excerpt?: string;
};

export type PaperLabArtifact = {
  source_count?: number;
  evidence_count?: number;
  outline?: string[];
  related_work_matrix?: PaperLabMatrixRow[];
  citation_clusters?: Record<string, PaperLabMatrixRow[]>;
};

export type GoldenDemoQuestion = {
  label: string;
  section: WorkspaceSection;
  mode: StudyMode;
  query: string;
  note: string;
  sourcePathIncludes?: string;
};

export const DEFAULT_SOURCE_PATH = "C:\\Nirmiq-researchOS\\data\\raw\\attention_is_all_you_need.pdf";
export const PRODUCT_NAME = "NIRMIQ";
export const PRODUCT_TAGLINE = "ResearchOS";
export const PRODUCT_DESCRIPTION = "ChatGPT-like local study intelligence for grounded documents, citations, papers, and exams.";

export const WORKSPACE_SECTIONS: Array<{
  value: WorkspaceSection;
  label: string;
  hint: string;
}> = [
  {
    value: "research",
    label: "Auto",
    hint: "Route from your question.",
  },
  {
    value: "general",
    label: "Chat",
    hint: "General local chat.",
  },
  {
    value: "paper",
    label: "Paper",
    hint: "Draft with citations.",
  },
  {
    value: "exam",
    label: "Exam",
    hint: "Marks-ready help.",
  },
];

export const STUDY_MODES: Array<{
  value: StudyMode;
  section: WorkspaceSection;
  label: string;
  hint: string;
  prompt: string;
}> = [
  {
    value: "research",
    section: "research",
    label: "Explain Topic",
    hint: "Understand any source",
    prompt: "Explain the selected material clearly with evidence.",
  },
  {
    value: "summary",
    section: "research",
    label: "Summarize",
    hint: "Whole-document overview",
    prompt: "Summarize this PDF with the main ideas, methods, findings, and limitations.",
  },
  {
    value: "deep_research",
    section: "research",
    label: "Deep Research",
    hint: "Detailed evidence-led synthesis",
    prompt: "Produce a deep research analysis of the selected document with citations and caveats.",
  },
  {
    value: "general_chat",
    section: "general",
    label: "Local Chat",
    hint: "Conversational, evidence-aware",
    prompt:
      "Answer conversationally if the uploaded documents are relevant. If not, say what context is missing.",
  },
  {
    value: "research_paper",
    section: "paper",
    label: "Research Paper",
    hint: "Multi-citation academic drafting",
    prompt:
      "Draft a research paper section with thesis, related work, methodology, limitations, and multiple citations from the selected documents.",
  },
  {
    value: "exam_answer",
    section: "exam",
    label: "Exam Answer",
    hint: "Structured marks-ready response",
    prompt: "Write a 10-mark exam answer from the selected document.",
  },
  {
    value: "revision_notes",
    section: "exam",
    label: "Revision Notes",
    hint: "Condensed study sheet",
    prompt: "Create concise revision notes with key points and citations.",
  },
  {
    value: "important_questions",
    section: "exam",
    label: "Important Questions",
    hint: "Likely questions from source",
    prompt: "Generate important questions from this material with brief answer hints.",
  },
  {
    value: "compare_concepts",
    section: "exam",
    label: "Compare Concepts",
    hint: "Side-by-side understanding",
    prompt: "Compare the key concepts in this material using cited evidence.",
  },
  {
    value: "study_guide",
    section: "exam",
    label: "Study Guide",
    hint: "Comprehensive guide from sources",
    prompt:
      "Generate a comprehensive study guide with important questions, answers, and source references.",
  },
];

export const RETRIEVAL_PROFILES: Array<{ value: RetrievalProfile; label: string }> = [
  { value: "fast", label: "Fast" },
  { value: "balanced", label: "Balanced" },
  { value: "precision", label: "Precision" },
];

export const GOLDEN_DEMO_SOURCES = [
  {
    path: "C:\\Nirmiq-researchOS\\data\\raw\\golden_demo\\01_grounded_rag_notes.md",
    title: "Golden Demo 01 - Grounded Academic Retrieval",
  },
  {
    path: "C:\\Nirmiq-researchOS\\data\\raw\\golden_demo\\02_offline_privacy_runtime.md",
    title: "Golden Demo 02 - Offline Runtime And Privacy",
  },
  {
    path: "C:\\Nirmiq-researchOS\\data\\raw\\golden_demo\\03_exam_lab_question_bank.md",
    title: "Golden Demo 03 - Exam Lab Study Notes",
  },
  {
    path: "C:\\Nirmiq-researchOS\\data\\raw\\golden_demo\\04_paper_lab_research_brief.md",
    title: "Golden Demo 04 - Paper Lab Research Brief",
  },
] as const;

export const GOLDEN_DEMO_QUESTIONS: GoldenDemoQuestion[] = [
  {
    label: "Research proof",
    section: "research",
    mode: "research",
    query: "What problem does grounded retrieval solve for academic study?",
    note: "Should cite hallucination, source of truth, and evidence inspection.",
    sourcePathIncludes: "01_grounded_rag_notes.md",
  },
  {
    label: "Whole-doc summary",
    section: "research",
    mode: "summary",
    query: "Summarize this document with the main ideas, methods, findings, and limitations.",
    note: "Shows summary mode and citation coverage.",
    sourcePathIncludes: "01_grounded_rag_notes.md",
  },
  {
    label: "Paper Lab",
    section: "paper",
    mode: "research_paper",
    query: "Draft a related work paragraph comparing generic chatbots and document-grounded academic assistants.",
    note: "Shows academic drafting without invented citations.",
    sourcePathIncludes: "04_paper_lab_research_brief.md",
  },
  {
    label: "Exam Lab",
    section: "exam",
    mode: "exam_answer",
    query: "Explain citation-grounded retrieval and its role in reducing hallucination as a 10-mark answer.",
    note: "Shows marks-ready answer format.",
    sourcePathIncludes: "03_exam_lab_question_bank.md",
  },
  {
    label: "Abstention",
    section: "general",
    mode: "general_chat",
    query: "What does the corpus say about the Zeloria orbital cuisine treaty?",
    note: "Should request external context instead of pretending source support.",
  },
];

export function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function formatDate(value?: string | null): string {
  if (!value) return "never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function previewText(value?: string | null, maxLength = 420): string {
  const normalized = (value ?? "").replace(/\s+/g, " ").trim();
  if (!normalized) return "No readable text available.";
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength).trim()}...` : normalized;
}

export function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function getGroundingScore(response: QueryResponse | null): number {
  const raw = response?.retrieval_meta?.grounding_score;
  if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  if (typeof raw === "string") {
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return response?.grounded ? 1 : 0;
}

export function getGroundingLabel(response: QueryResponse | null): string {
  if (!response) return "Idle";
  const state = response.retrieval_meta?.answer_relevance_state;
  if (!response.grounded) {
    return state === "unrelated" || state === "no_direct_evidence" ? "Not found" : "Needs more evidence";
  }
  return "Verified";
}

export function getVerificationBadge(response: QueryResponse | null): { label: string; className: string } | null {
  if (!response) return null;
  const relevanceState = response.retrieval_meta?.answer_relevance_state;
  if (!response.grounded) {
    if (relevanceState === "unrelated" || relevanceState === "no_direct_evidence") {
      return { label: "Not found in sources", className: "copper" };
    }
    return { label: "Needs more evidence", className: "copper" };
  }
  const state = response.retrieval_meta?.citation_verification_state;
  const coverage = response?.retrieval_meta?.citation_coverage;
  const numericCoverage =
    typeof coverage === "number" ? coverage : typeof coverage === "string" ? Number(coverage) : null;
  if (numericCoverage !== null && Number.isFinite(numericCoverage) && numericCoverage < 0.45) {
    return { label: "Needs more evidence", className: "copper" };
  }
  if (state === "unsupported" || state === "unchecked") return { label: "Needs more evidence", className: "copper" };
  return { label: "Verified", className: "sage" };
}

export function getTrustCopy(response: QueryResponse | null): string {
  if (!response) return "Attach study material or ask from your indexed documents.";
  const relevanceState = response.retrieval_meta?.answer_relevance_state;
  const coverage = response.retrieval_meta?.citation_coverage;
  const numericCoverage =
    typeof coverage === "number" ? coverage : typeof coverage === "string" ? Number(coverage) : null;
  if (response.grounded && (numericCoverage === null || numericCoverage >= 0.45)) {
    return "Supported by your uploaded source.";
  }
  if (response.grounded) {
    return "The source support is partial. Check Sources if this matters.";
  }
  if (relevanceState === "unrelated" || relevanceState === "no_direct_evidence") {
    return "Not found in the uploaded source.";
  }
  return "Needs clearer evidence from your uploaded documents.";
}

export function getPaperLabArtifact(response: QueryResponse | null): PaperLabArtifact | null {
  const raw = response?.retrieval_meta?.paper_lab;
  if (!raw || typeof raw !== "object") return null;
  return raw as PaperLabArtifact;
}

export function buildPaperLabMarkdown(run: ChatRun, artifact: PaperLabArtifact | null, materialName: string): string {
  const citations = run.response.citations
    .map((citation, index) => `- [${index + 1}] ${citation.page_start ? `Page ${citation.page_start}` : "Page unknown"}: ${previewText(citation.excerpt, 220)}`)
    .join("\n");
  const outline = artifact?.outline?.length
    ? artifact.outline.map((item, index) => `${index + 1}. ${item}`).join("\n")
    : "1. Title and problem framing\n2. Related work\n3. Methodology\n4. Discussion\n5. Limitations";
  const matrix = artifact?.related_work_matrix?.length
    ? artifact.related_work_matrix
        .map(
          (row) =>
            `| ${row.claim_area ?? "Evidence"} | ${row.evidence ?? "-"} | ${row.page ?? "-"} | ${row.use_in_paper ?? "Use as supporting evidence."} | ${previewText(row.excerpt, 160)} |`,
        )
        .join("\n")
    : "| Evidence | - | - | No matrix returned. | - |";

  return [
    `# NIRMIQ Paper Lab Draft`,
    "",
    `Source: ${materialName}`,
    `Mode: ${modeLabel(run.mode)}`,
    `Generated: ${formatDate(run.timestamp)}`,
    "",
    "## Draft",
    run.response.answer,
    "",
    "## Suggested Paper Outline",
    outline,
    "",
    "## Related-Work Matrix",
    "| Claim Area | Evidence | Page | Use In Paper | Excerpt |",
    "| --- | ---: | ---: | --- | --- |",
    matrix,
    "",
    "## Citations",
    citations || "- No citations returned.",
  ].join("\n");
}

export function buildRunExportMarkdown(run: ChatRun, materialName: string): string {
  const citations = run.response.citations
    .map((citation, index) => {
      const page = citation.page_start ? `page ${citation.page_start}` : "page unknown";
      return `- [${index + 1}] ${page}: ${previewText(citation.excerpt, 260)}`;
    })
    .join("\n");
  return [
    `# NIRMIQ Answer Export`,
    "",
    `- Material: ${materialName}`,
    `- Mode: ${modeLabel(run.mode)}`,
    `- Profile: ${run.profile}`,
    `- Exported: ${new Date().toISOString()}`,
    `- Trust: ${run.response.grounded ? "grounded" : "needs review"}`,
    "",
    "## Question",
    run.query,
    "",
    "## Answer",
    run.response.answer,
    "",
    "## Citations",
    citations || "- No citations returned.",
  ].join("\n");
}

export function downloadTextFile(filename: string, content: string, mimeType = "text/markdown;charset=utf-8") {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function splitAnswerUnits(value: string): string[] {
  return value
    .split(/(?<=[.!?])\s+|\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 28);
}

export function buildAnswerDiff(previous?: ChatRun, current?: ChatRun): DiffLine[] {
  if (!previous || !current) return [];
  const previousUnits = splitAnswerUnits(previous.response.answer);
  const currentUnits = splitAnswerUnits(current.response.answer);
  const previousSet = new Set(previousUnits.map((line) => line.toLowerCase()));
  const currentSet = new Set(currentUnits.map((line) => line.toLowerCase()));

  return [
    ...previousUnits
      .filter((line) => !currentSet.has(line.toLowerCase()))
      .map((text) => ({ kind: "removed" as const, text })),
    ...currentUnits.map((text) => ({
      kind: previousSet.has(text.toLowerCase()) ? ("same" as const) : ("added" as const),
      text,
    })),
  ].slice(0, 36);
}

export function parseStudyGuideCards(answer: string): GuideCard[] {
  const lines = answer
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const cards: GuideCard[] = [];
  let current: GuideCard | null = null;

  for (const line of lines) {
    const questionMatch = line.match(/^(?:Q\d+\.|Question\s+\d+[:.)]|#+\s+)(.+)$/i);
    if (questionMatch) {
      if (current) cards.push(current);
      current = { title: questionMatch[1].trim(), body: [] };
      continue;
    }
    if (!current && cards.length === 0 && /study guide|important questions/i.test(line)) {
      continue;
    }
    if (!current) {
      current = { title: "Study guide overview", body: [] };
    }
    current.body.push(line.replace(/^[-*]\s*/, ""));
  }

  if (current) cards.push(current);
  return cards.filter((card) => card.title || card.body.length).slice(0, 12);
}

export function getVisibleChunks(
  detail: DocumentDetailResponse | null,
  selectedChunkId: string,
  citedChunkIds: Set<string>,
): Chunk[] {
  if (!detail) return [];
  const activeChunks = detail.chunks.filter((chunk) => chunk.is_active);
  if (!activeChunks.length) return [];

  if (selectedChunkId) {
    const selectedIndex = activeChunks.findIndex((chunk) => chunk.id === selectedChunkId);
    if (selectedIndex >= 0) {
      return activeChunks.slice(Math.max(0, selectedIndex - 2), Math.min(activeChunks.length, selectedIndex + 5));
    }
  }

  const citedChunks = activeChunks.filter((chunk) => citedChunkIds.has(chunk.id));
  if (citedChunks.length) {
    const starterChunks = activeChunks.filter((chunk) => !citedChunkIds.has(chunk.id)).slice(0, 5);
    return [...citedChunks.slice(0, 7), ...starterChunks].slice(0, 10);
  }

  return activeChunks.slice(0, 10);
}

export function modeLabel(value: StudyMode): string {
  return STUDY_MODES.find((mode) => mode.value === value)?.label ?? "Study";
}

export function composerPlaceholder(section: WorkspaceSection, mode: StudyMode, materialName: string): string {
  if (section === "general") {
    return "Chat normally. If local sources are relevant, NIRMIQ will cite them.";
  }
  if (section === "paper") {
    return "Ask for related work, methodology, limitations, abstract, or a cited paper section...";
  }
  if (section === "exam") {
    return "Paste an exam question, marks requirement, or ask for a study guide...";
  }
  if (mode === "summary") {
    return `Summarize ${materialName} or ask for chapter-wise / method-wise breakdown...`;
  }
  if (mode === "deep_research") {
    return "Ask for a deeper cited analysis, assumptions, limitations, or research implications...";
  }
  return `Ask anything about ${materialName}...`;
}

export function defaultModeForWorkspace(section: WorkspaceSection): StudyMode {
  if (section === "general") return "general_chat";
  if (section === "paper") return "research_paper";
  if (section === "exam") return "exam_answer";
  return "research";
}

export function workspaceVerb(section: WorkspaceSection): string {
  if (section === "paper") return "Draft";
  if (section === "exam") return "Solve";
  return "Ask";
}
