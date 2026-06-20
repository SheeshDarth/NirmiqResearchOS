"use client";

import { ChangeEvent, FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  deleteDocument,
  deleteSession,
  diagramAssetUrl,
  exportSessionMarkdown,
  getDocument,
  getIngestJobs,
  getIngestStatus,
  getMemorySummary,
  getSessionTimeline,
  healthCheck,
  extractDiagrams,
  importQuestionBank,
  ingestDocument,
  listDiagrams,
  listQuestionBank,
  listDocuments,
  purgeDocuments,
  runQuery,
  upsertExamProfile,
  uploadDocument,
  type DiagramAssetItem,
  type DocumentDetailResponse,
  type DocumentItem,
  type ExamProfileItem,
  type IngestJobsResponse,
  type IngestStatusResponse,
  type QuestionBankItem,
  type QueryResponse,
  type SessionSummaryResponse,
  type SessionTimelineResponse,
} from "../lib/api-client";

type RetrievalMode = "hybrid" | "bm25" | "vector";
type RetrievalProfile = "fast" | "balanced" | "precision";
type WorkspaceSection = "research" | "general" | "paper" | "exam";
type StudyMode =
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
type BusyState =
  | ""
  | "health"
  | "ingest"
  | "query"
  | "status"
  | "documents"
  | "delete"
  | "demo"
  | "privacy";
type DeepView = "evidence" | "context" | "compare" | "eval";
type Chunk = DocumentDetailResponse["chunks"][number];

type ChatRun = {
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

type EvalReportPayload = {
  dataset?: string;
  evaluation_mode?: string;
  modes?: string[];
  results?: Record<
    string,
    {
      mode?: string;
      samples?: number;
      target_level?: string;
      mrr?: number;
      hit_rate_at_3?: number;
      hit_rate_at_5?: number;
      [key: string]: unknown;
    }
  >;
};

type DiffLine = {
  kind: "same" | "added" | "removed";
  text: string;
};

type GuideCard = {
  title: string;
  body: string[];
};

type PaperLabMatrixRow = {
  claim_area?: string;
  evidence?: number;
  page?: number | null;
  source_type?: string;
  quality?: number;
  use_in_paper?: string;
  excerpt?: string;
};

type PaperLabArtifact = {
  source_count?: number;
  evidence_count?: number;
  outline?: string[];
  related_work_matrix?: PaperLabMatrixRow[];
  citation_clusters?: Record<string, PaperLabMatrixRow[]>;
};

type GoldenDemoQuestion = {
  label: string;
  section: WorkspaceSection;
  mode: StudyMode;
  query: string;
  note: string;
  sourcePathIncludes?: string;
};

const DEFAULT_SOURCE_PATH = "C:\\Nirmiq-researchOS\\data\\raw\\attention_is_all_you_need.pdf";
const PRODUCT_NAME = "NIRMIQ";
const PRODUCT_TAGLINE = "ResearchOS";
const PRODUCT_DESCRIPTION = "ChatGPT-like local study intelligence for grounded documents, citations, papers, and exams.";

const WORKSPACE_SECTIONS: Array<{
  value: WorkspaceSection;
  label: string;
  hint: string;
}> = [
  {
    value: "research",
    label: "Research",
    hint: "Deep reads with citations.",
  },
  {
    value: "general",
    label: "Chat",
    hint: "Talk normally, local-first.",
  },
  {
    value: "paper",
    label: "Paper Lab",
    hint: "Engineering research drafts.",
  },
  {
    value: "exam",
    label: "Exam Lab",
    hint: "Marks, guides, diagrams.",
  },
];

const STUDY_MODES: Array<{
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

const RETRIEVAL_PROFILES: Array<{ value: RetrievalProfile; label: string }> = [
  { value: "fast", label: "Fast" },
  { value: "balanced", label: "Balanced" },
  { value: "precision", label: "Precision" },
];

const GOLDEN_DEMO_SOURCES = [
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

const GOLDEN_DEMO_QUESTIONS: GoldenDemoQuestion[] = [
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

function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

function formatDate(value?: string | null): string {
  if (!value) return "never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function previewText(value?: string | null, maxLength = 420): string {
  const normalized = (value ?? "").replace(/\s+/g, " ").trim();
  if (!normalized) return "No readable text available.";
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength).trim()}...` : normalized;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getGroundingScore(response: QueryResponse | null): number {
  const raw = response?.retrieval_meta?.grounding_score;
  if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  if (typeof raw === "string") {
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return response?.grounded ? 1 : 0;
}

function getGroundingLabel(response: QueryResponse | null): string {
  if (!response) return "Idle";
  const score = getGroundingScore(response);
  if (!response.grounded) return "Insufficient";
  if (score >= 0.75) return "Strong";
  if (score >= 0.45) return "Moderate";
  return "Weak";
}

function getVerificationBadge(response: QueryResponse | null): { label: string; className: string } | null {
  const state = response?.retrieval_meta?.citation_verification_state;
  const rewritten = response?.retrieval_meta?.answer_rewritten_for_faithfulness === true;
  const coverage = response?.retrieval_meta?.citation_coverage;
  const numericCoverage =
    typeof coverage === "number" ? coverage : typeof coverage === "string" ? Number(coverage) : null;
  if (rewritten) return { label: "Rewritten", className: "copper" };
  if (numericCoverage !== null && Number.isFinite(numericCoverage) && numericCoverage < 0.45) {
    return { label: "Low citation coverage", className: "copper" };
  }
  if (state === "supported") return { label: "Verified", className: "sage" };
  if (state === "unsupported" || state === "unchecked") return { label: "Needs review", className: "copper" };
  return null;
}

function getTrustCopy(response: QueryResponse | null): string {
  if (!response) return "Attach study material or ask from your indexed documents.";
  const coverage = response.retrieval_meta?.citation_coverage;
  const numericCoverage =
    typeof coverage === "number" ? coverage : typeof coverage === "string" ? Number(coverage) : null;
  if (response.grounded && (numericCoverage === null || numericCoverage >= 0.45)) {
    return "Answer grounded in your study material.";
  }
  if (response.grounded) {
    return "Answer uses local evidence, but citation coverage needs review.";
  }
  return "I could not find enough evidence in your uploaded documents.";
}

function getPaperLabArtifact(response: QueryResponse | null): PaperLabArtifact | null {
  const raw = response?.retrieval_meta?.paper_lab;
  if (!raw || typeof raw !== "object") return null;
  return raw as PaperLabArtifact;
}

function buildPaperLabMarkdown(run: ChatRun, artifact: PaperLabArtifact | null, materialName: string): string {
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

function buildRunExportMarkdown(run: ChatRun, materialName: string): string {
  const citations = run.response.citations
    .map((citation, index) => {
      const page = citation.page_start ? `page ${citation.page_start}` : "page unknown";
      const score = typeof citation.score === "number" ? `, score ${citation.score.toFixed(2)}` : "";
      return `- [${index + 1}] ${page}${score}: ${previewText(citation.excerpt, 260)}`;
    })
    .join("\n");
  const meta = run.response.retrieval_meta ?? {};
  return [
    `# NIRMIQ Answer Export`,
    "",
    `- Material: ${materialName}`,
    `- Mode: ${modeLabel(run.mode)}`,
    `- Profile: ${run.profile}`,
    `- Exported: ${new Date().toISOString()}`,
    `- Trust: ${run.response.grounded ? "grounded" : "needs review"}`,
    `- Citation coverage: ${String(meta.citation_coverage ?? "not reported")}`,
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

function downloadTextFile(filename: string, content: string, mimeType = "text/markdown;charset=utf-8") {
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

function splitAnswerUnits(value: string): string[] {
  return value
    .split(/(?<=[.!?])\s+|\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 28);
}

function buildAnswerDiff(previous?: ChatRun, current?: ChatRun): DiffLine[] {
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

function parseStudyGuideCards(answer: string): GuideCard[] {
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

function getVisibleChunks(
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

function StudyGuideAnswer({ answer }: { answer: string }) {
  const cards = parseStudyGuideCards(answer);
  if (!cards.length) {
    return <div className="answer">{answer}</div>;
  }

  return (
    <div className="study-guide-cards">
      {cards.map((card, index) => (
        <details className="guide-card" key={`${card.title}-${index}`} open={index === 0}>
          <summary>
            <span>Question {index + 1}</span>
            <strong>{card.title}</strong>
          </summary>
          <div className="guide-card-body">
            {card.body.length ? (
              card.body.map((line, lineIndex) => <p key={`${card.title}-${lineIndex}`}>{line}</p>)
            ) : (
              <p>No generated answer body was returned for this question.</p>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}

function LocalLogin({
  displayName,
  email,
  phone,
  onDisplayNameChange,
  onEmailChange,
  onPhoneChange,
  onContinue,
}: {
  displayName: string;
  email: string;
  phone: string;
  onDisplayNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onContinue: () => void;
}) {
  const canContinue = displayName.trim().length > 0 && (email.trim().length > 0 || phone.trim().length > 0);

  return (
    <main className="login-shell">
      <section className="login-card landing-card minimal-login">
        <div className="brand-lockup hero">
          <div className="brand-mark" aria-hidden="true">
            <img alt="" src="/brand/nirmiq-ais-mark.svg" />
          </div>
          <div>
            <strong>{PRODUCT_NAME}</strong>
            <span>{PRODUCT_TAGLINE}</span>
          </div>
        </div>
        <div className="landing-copy">
          <p className="eyebrow">Local study intelligence</p>
          <h1>Chat with your study material.</h1>
          <p className="copy">
            Upload PDFs, notes, papers, question banks, or images. Ask naturally and get answers
            grounded in your own sources with citations.
          </p>
          <div className="login-proof" aria-label="NIRMIQ trust proof">
            <span>offline core</span>
            <span>citation trail</span>
            <span>abstains when unsupported</span>
            <span>paper + exam labs</span>
          </div>
          <div className="why-nirmiq">
            <strong>Not just a PDF chatbot.</strong>
            <p>
              NIRMIQ is built for academic work: verify sources, draft cited sections, prepare
              exams, and prove when the uploaded material is not enough.
            </p>
          </div>
        </div>
        <div className="login-panel">
          <h2>Start a local study thread</h2>
          <p className="tiny">
            Local profile only. No cloud account, no API key, no hosted auth.
          </p>
          <div className="login-fields">
            <label className="label">
              Name
              <input
                className="input"
                onChange={(event) => onDisplayNameChange(event.target.value)}
                placeholder="Siddharth"
                value={displayName}
              />
            </label>
            <label className="label">
              Email
              <input
                className="input"
                onChange={(event) => onEmailChange(event.target.value)}
                placeholder="you@example.com"
                type="email"
                value={email}
              />
            </label>
            <label className="label">
              Phone
              <input
                className="input"
                onChange={(event) => onPhoneChange(event.target.value)}
                placeholder="+91..."
                type="tel"
                value={phone}
              />
            </label>
          </div>
          <button className="button primary" disabled={!canContinue} onClick={onContinue} type="button">
            Open NIRMIQ
          </button>
        </div>
      </section>
    </main>
  );
}

function modeLabel(value: StudyMode): string {
  return STUDY_MODES.find((mode) => mode.value === value)?.label ?? "Study";
}

function composerPlaceholder(section: WorkspaceSection, mode: StudyMode, materialName: string): string {
  if (section === "general") {
    return "Chat normally. If local sources are relevant, NIRMIQ will cite them.";
  }
  if (section === "paper") {
    return "Ask for thesis, abstract, related work, methodology, limitations, or citation-backed sections...";
  }
  if (section === "exam") {
    return "Paste an exam question, marks requirement, or ask for a custom study guide PDF...";
  }
  if (mode === "summary") {
    return `Summarize ${materialName} or ask for chapter-wise / method-wise breakdown...`;
  }
  if (mode === "deep_research") {
    return "Ask for a deeper cited analysis, assumptions, limitations, or research implications...";
  }
  return `Ask about ${materialName}...`;
}

function workspaceVerb(section: WorkspaceSection): string {
  if (section === "paper") return "Draft";
  if (section === "exam") return "Solve";
  if (section === "general") return "Send";
  return "Ask";
}

export default function Home() {
  const queryFormRef = useRef<HTMLFormElement | null>(null);
  const queryInputRef = useRef<HTMLTextAreaElement | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const [mounted, setMounted] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [displayName, setDisplayName] = useState("Siddharth");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [composerCollapsed, setComposerCollapsed] = useState(false);
  const [showLibrary, setShowLibrary] = useState(true);
  const [showInspector, setShowInspector] = useState(false);
  const [health, setHealth] = useState("unknown");
  const [busy, setBusy] = useState<BusyState>("");
  const [error, setError] = useState("");
  const [sourcePath, setSourcePath] = useState(DEFAULT_SOURCE_PATH);
  const [title, setTitle] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentDetail, setSelectedDocumentDetail] = useState<DocumentDetailResponse | null>(null);
  const [selectedChunkId, setSelectedChunkId] = useState("");
  const [ingestStatus, setIngestStatus] = useState<IngestStatusResponse | null>(null);
  const [ingestJobs, setIngestJobs] = useState<IngestJobsResponse | null>(null);
  const [sessionId, setSessionId] = useState("siddharth-study-thread");
  const [workspaceSection, setWorkspaceSection] = useState<WorkspaceSection>("general");
  const [studyMode, setStudyMode] = useState<StudyMode>("general_chat");
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>("hybrid");
  const [retrievalProfile, setRetrievalProfile] = useState<RetrievalProfile>("balanced");
  const [query, setQuery] = useState("");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [queryHistory, setQueryHistory] = useState<ChatRun[]>([]);
  const [memory, setMemory] = useState<SessionSummaryResponse | null>(null);
  const [timeline, setTimeline] = useState<SessionTimelineResponse | null>(null);
  const [deepView, setDeepView] = useState<DeepView>("evidence");
  const [examAction, setExamAction] = useState("");
  const [examProfile, setExamProfile] = useState<ExamProfileItem | null>(null);
  const [examMarks, setExamMarks] = useState(10);
  const [examAnswerStyle, setExamAnswerStyle] = useState("exam-ready");
  const [examContentType, setExamContentType] = useState("conceptual");
  const [examInstructions, setExamInstructions] = useState("Use concise headings, key points, and source-backed explanations.");
  const [questionBankInput, setQuestionBankInput] = useState("");
  const [questionBankItems, setQuestionBankItems] = useState<QuestionBankItem[]>([]);
  const [diagramAssets, setDiagramAssets] = useState<DiagramAssetItem[]>([]);
  const [evalReportInput, setEvalReportInput] = useState("");
  const [evalReport, setEvalReport] = useState<EvalReportPayload | null>(null);
  const [evalReportError, setEvalReportError] = useState("");

  const canIngest = sourcePath.trim().length > 0;
  const canQuery = query.trim().length > 0 && sessionId.trim().length > 0;

  const selectedDocument = useMemo(
    () => documents.find((item) => item.id === documentId) ?? null,
    [documentId, documents],
  );
  const latestCitations = queryResult?.citations ?? [];
  const groundingScore = getGroundingScore(queryResult);
  const groundingLabel = getGroundingLabel(queryResult);
  const citedChunkIds = useMemo(
    () =>
      new Set(
        latestCitations
          .filter((citation) => citation.document_id === documentId)
          .map((citation) => citation.chunk_id),
      ),
    [documentId, latestCitations],
  );
  const visibleChunks = useMemo(
    () => getVisibleChunks(selectedDocumentDetail, selectedChunkId, citedChunkIds),
    [citedChunkIds, selectedChunkId, selectedDocumentDetail],
  );
  const selectedChunk = useMemo(
    () => selectedDocumentDetail?.chunks.find((chunk) => chunk.id === selectedChunkId) ?? null,
    [selectedChunkId, selectedDocumentDetail],
  );
  const previousRun = queryHistory.length >= 2 ? queryHistory[queryHistory.length - 2] : undefined;
  const currentRun = queryHistory.length >= 1 ? queryHistory[queryHistory.length - 1] : undefined;
  const answerDiff = useMemo(() => buildAnswerDiff(previousRun, currentRun), [currentRun, previousRun]);
  const paperLabArtifact = useMemo(() => getPaperLabArtifact(queryResult), [queryResult]);
  const availableModes = STUDY_MODES.filter((mode) => mode.section === workspaceSection);
  const currentMode = availableModes.find((mode) => mode.value === studyMode) ?? availableModes[0] ?? STUDY_MODES[0];
  const currentSection = WORKSPACE_SECTIONS.find((section) => section.value === workspaceSection) ?? WORKSPACE_SECTIONS[0];
  const activeMaterialName = selectedDocumentDetail?.title || selectedDocument?.title || "No study material selected";
  const activePlaceholder = composerPlaceholder(workspaceSection, currentMode.value, activeMaterialName);
  const activeActionLabel = workspaceVerb(workspaceSection);
  const isGoldenDemoSource = Boolean(
    selectedDocument?.source_path?.includes("\\golden_demo\\") ||
      selectedDocument?.source_path?.includes("/golden_demo/") ||
      selectedDocumentDetail?.source_path?.includes("\\golden_demo\\") ||
      selectedDocumentDetail?.source_path?.includes("/golden_demo/"),
  );
  const retrievalMeta = queryResult?.retrieval_meta ?? {};
  const citationCoverage =
    typeof retrievalMeta.citation_coverage === "number"
      ? `${Math.round(retrievalMeta.citation_coverage * 100)}%`
      : "not reported";
  const detectedIntent =
    typeof retrievalMeta.detected_intent === "string" ? retrievalMeta.detected_intent : "not routed yet";

  useEffect(() => {
    const storedName = window.localStorage.getItem("nirmiq.localProfileName");
    const storedEmail = window.localStorage.getItem("nirmiq.localEmail");
    const storedPhone = window.localStorage.getItem("nirmiq.localPhone");
    const storedUnlocked = window.localStorage.getItem("nirmiq.localUnlocked") === "true";
    if (storedName) setDisplayName(storedName);
    if (storedEmail) setEmail(storedEmail);
    if (storedPhone) setPhone(storedPhone);
    if (storedUnlocked) setIsUnlocked(true);
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    void loadHealth();
    void loadDocuments();
  }, [mounted]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [queryHistory, busy]);

  useEffect(() => {
    if (!mounted || !documentId) return;
    void loadExamLabState(documentId);
  }, [documentId, mounted]);

  async function loadHealth() {
    try {
      const response = await healthCheck();
      setHealth(response.status);
    } catch (err) {
      setHealth("offline");
      setError(String(err));
    }
  }

  async function loadDocuments() {
    setBusy((current) => current || "documents");
    try {
      const response = await listDocuments();
      setDocuments(response.items);
      const preferredId =
        documentId && response.items.some((item) => item.id === documentId)
          ? documentId
          : response.items[0]?.id ?? "";
      if (preferredId && preferredId !== documentId) {
        setDocumentId(preferredId);
        await Promise.all([loadDocumentState(preferredId), loadDocumentDetail(preferredId)]);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy((current) => (current === "documents" ? "" : current));
    }
  }

  async function loadDocumentState(targetId: string) {
    if (!targetId.trim()) return;
    const [status, jobs] = await Promise.all([
      getIngestStatus(targetId.trim()),
      getIngestJobs(targetId.trim()),
    ]);
    setIngestStatus(status);
    setIngestJobs(jobs);
  }

  async function loadDocumentDetail(targetId: string) {
    if (!targetId.trim()) return;
    const detail = await getDocument(targetId.trim());
    setSelectedDocumentDetail(detail);
  }

  async function loadExamLabState(targetId: string) {
    if (!targetId.trim()) return;
    try {
      const [questions, diagrams] = await Promise.all([
        listQuestionBank(targetId.trim()),
        listDiagrams(targetId.trim()),
      ]);
      setQuestionBankItems(questions);
      setDiagramAssets(diagrams);
    } catch (err) {
      setError(String(err));
    }
  }

  async function loadSessionState(targetSessionId: string) {
    if (!targetSessionId.trim()) return;
    const [summary, timelineResponse] = await Promise.all([
      getMemorySummary(targetSessionId.trim()),
      getSessionTimeline(targetSessionId.trim()),
    ]);
    setMemory(summary);
    setTimeline(timelineResponse);
  }

  async function onHealthCheck() {
    setBusy("health");
    setError("");
    await loadHealth();
    setBusy("");
  }

  async function onIngest(event: FormEvent) {
    event.preventDefault();
    if (!canIngest) return;
    setBusy("ingest");
    setError("");
    try {
      const response = await ingestDocument({
        source_path: sourcePath.trim(),
        title: title.trim() || undefined,
        force_reindex: true,
      });
      setDocumentId(response.document_id);
      setSelectedChunkId("");
      await Promise.all([loadDocumentState(response.document_id), loadDocumentDetail(response.document_id)]);
      await loadDocuments();
      setDeepView("evidence");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function onRefreshStatus() {
    if (!documentId.trim()) return;
    setBusy("status");
    setError("");
    try {
      await Promise.all([loadDocumentState(documentId.trim()), loadDocumentDetail(documentId.trim())]);
      await loadDocuments();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function onUploadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy("ingest");
    setError("");
    try {
      const fallbackTitle = file.name.replace(/\.[^.]+$/, "");
      const response = await uploadDocument({
        file,
        title: fallbackTitle,
        force_reindex: true,
      });
      setDocumentId(response.document_id);
      setTitle(fallbackTitle);
      setSourcePath(`Uploaded: ${file.name}`);
      setSelectedChunkId("");
      await Promise.all([loadDocumentState(response.document_id), loadDocumentDetail(response.document_id)]);
      await loadDocuments();
      setShowLibrary(false);
      setDeepView("evidence");
      queryInputRef.current?.focus();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
      if (event.target) event.target.value = "";
    }
  }

  async function onLoadGoldenDemo() {
    if (busy !== "") return;
    setBusy("demo");
    setError("");
    try {
      const loadedIds: string[] = [];
      for (const source of GOLDEN_DEMO_SOURCES) {
        const response = await ingestDocument({
          source_path: source.path,
          title: source.title,
          force_reindex: false,
        });
        loadedIds.push(response.document_id);
      }

      const documentList = await listDocuments();
      setDocuments(documentList.items);
      const firstDemoDocument =
        documentList.items.find((item) => item.source_path.includes("01_grounded_rag_notes.md")) ??
        documentList.items.find((item) => loadedIds.includes(item.id)) ??
        documentList.items[0];

      if (firstDemoDocument) {
        setDocumentId(firstDemoDocument.id);
        setSelectedChunkId("");
        await Promise.all([loadDocumentState(firstDemoDocument.id), loadDocumentDetail(firstDemoDocument.id)]);
      }

      const firstQuestion = GOLDEN_DEMO_QUESTIONS[0];
      setWorkspaceSection(firstQuestion.section);
      setStudyMode(firstQuestion.mode);
      setRetrievalProfile("balanced");
      setRetrievalMode("hybrid");
      setQuery(firstQuestion.query);
      setShowLibrary(false);
      setShowInspector(true);
      setDeepView("evidence");
      setError("Golden demo loaded. Press Ask to run the first proof question.");
      window.requestAnimationFrame(() => queryInputRef.current?.focus());
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function onDeleteSelectedDocument() {
    if (!documentId || busy !== "") return;
    const label = selectedDocumentDetail?.title || selectedDocument?.title || "selected document";
    const confirmed = window.confirm(`Remove "${label}" from NIRMIQ? This clears local indexes, chunks, exam data, and diagram metadata for this document.`);
    if (!confirmed) return;
    setBusy("delete");
    setError("");
    try {
      await deleteDocument(documentId);
      setDocumentId("");
      setSelectedDocumentDetail(null);
      setSelectedChunkId("");
      setIngestStatus(null);
      setIngestJobs(null);
      setQuestionBankItems([]);
      setDiagramAssets([]);
      setExamProfile(null);
      setQueryResult(null);
      await loadDocuments();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function onQuery(event: FormEvent) {
    event.preventDefault();
    if (!canQuery || busy !== "") return;
    await executeQuery(query.trim());
  }

  async function executeQuery(submittedQuery: string, modeOverride: StudyMode = currentMode.value) {
    if (!submittedQuery || !sessionId.trim() || busy !== "") return;
    setBusy("query");
    setError("");
    try {
      const scopedDocumentId = documentId || undefined;
      const sourceSnapshot = scopedDocumentId
        ? {
            document_id: scopedDocumentId,
            source_title: activeMaterialName,
            source_path: selectedDocumentDetail?.source_path || selectedDocument?.source_path,
          }
        : {};
      const response = await runQuery({
        session_id: sessionId.trim(),
        query: submittedQuery,
        document_id: scopedDocumentId,
        mode: modeOverride,
        retrieval_mode: retrievalMode,
        retrieval_profile: retrievalProfile,
        exam_profile:
          workspaceSection === "exam" &&
          ["exam_answer", "revision_notes", "important_questions", "compare_concepts", "study_guide"].includes(
            modeOverride,
          )
            ? {
                marks: examMarks,
                answer_style: examAnswerStyle,
                content_type: examContentType,
                instructions: examInstructions.trim() || undefined,
              }
            : undefined,
        debug: true,
      });
      setQueryResult(response);
      setQueryHistory((current) =>
        [
          ...current,
          {
            session_id: response.session_id,
            query: submittedQuery,
            mode: modeOverride,
            profile: retrievalProfile,
            ...sourceSnapshot,
            response,
            timestamp: new Date().toISOString(),
          },
        ].slice(-12),
      );
      setQuery("");
      try {
        await loadSessionState(response.session_id);
      } catch (err) {
        setError(`Answer generated, but local memory refresh failed: ${String(err)}`);
      }
      setDeepView("evidence");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function onSummarizeSelectedSource() {
    if (!documentId || busy !== "") {
      setError("Upload or select study material before summarizing.");
      return;
    }
    setWorkspaceSection("research");
    setStudyMode("summary");
    setRetrievalProfile("balanced");
    await executeQuery("Summarize this PDF with the main ideas, methods, findings, and limitations.", "summary");
  }

  async function onGenerateExamPdf() {
    if (busy !== "") return;
    if (currentRun?.response.answer && workspaceSection === "exam") {
      openPdfPrintView(currentRun);
      return;
    }
    if (!documentId) {
      setError("Upload or select exam material before generating a custom PDF.");
      return;
    }
    setWorkspaceSection("exam");
    setStudyMode("study_guide");
    setRetrievalProfile("precision");
    await executeQuery(
      "Generate a custom exam PDF study guide from the selected study material. Include important questions, concise answers, marks-ready structure, and citations.",
      "study_guide",
    );
    setError("Custom PDF content generated. Click Custom PDF again and choose 'Save as PDF' in the print dialog.");
  }

  function openPdfPrintView(run: ChatRun) {
    const printable = window.open("", "_blank", "noopener,noreferrer,width=900,height=1000");
    if (!printable) {
      setError("Popup blocked. Allow popups to export the custom PDF.");
      return;
    }
    const citationList = run.response.citations
      .map((citation, index) => `<li>Evidence ${index + 1}${citation.page_start ? `, page ${citation.page_start}` : ""}</li>`)
      .join("");
    const runSourceLabel = run.source_title || activeMaterialName;
    printable.document.write(`
      <html>
        <head>
          <title>NIRMIQ Custom Exam PDF</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 40px; color: #111; line-height: 1.6; }
            h1 { margin-bottom: 4px; }
            .meta { color: #555; font-size: 12px; margin-bottom: 24px; }
            pre { white-space: pre-wrap; font-family: inherit; }
            li { margin: 4px 0; }
          </style>
        </head>
        <body>
          <h1>NIRMIQ Custom Exam PDF</h1>
          <div class="meta">${escapeHtml(runSourceLabel)} / ${escapeHtml(modeLabel(run.mode))} / ${escapeHtml(formatDate(run.timestamp))}</div>
          <pre>${escapeHtml(run.response.answer)}</pre>
          <h2>Citations</h2>
          <ol>${citationList || "<li>No citations returned.</li>"}</ol>
          <script>window.onload = () => window.print();</script>
        </body>
      </html>
    `);
    printable.document.close();
  }

  async function onCopyPaperMarkdown() {
    if (!currentRun || workspaceSection !== "paper") return;
    const markdown = buildPaperLabMarkdown(currentRun, paperLabArtifact, currentRun.source_title || activeMaterialName);
    try {
      await navigator.clipboard.writeText(markdown);
      setError("Paper Lab Markdown copied with outline, matrix, answer, and citations.");
    } catch {
      setError("Clipboard copy failed. Select the answer text manually and copy it.");
    }
  }

  function onExportCurrentRun() {
    if (!currentRun) {
      setError("Ask a question first, then export the answer and citations.");
      return;
    }
    const filename = `nirmiq-answer-${new Date().toISOString().slice(0, 10)}.md`;
    downloadTextFile(filename, buildRunExportMarkdown(currentRun, currentRun.source_title || activeMaterialName));
    setError("Answer exported locally as Markdown with citations.");
  }

  async function onExportThread() {
    if (!sessionId.trim()) return;
    setBusy("privacy");
    setError("");
    try {
      const markdown = await exportSessionMarkdown(sessionId.trim());
      const filename = `nirmiq-thread-${sessionId.trim().replace(/[^a-z0-9_-]+/gi, "-").slice(0, 48)}.md`;
      downloadTextFile(filename, markdown);
      setError("Thread exported locally as Markdown.");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function onClearSession() {
    if (!sessionId.trim() || busy !== "") return;
    const confirmed = window.confirm(
      "Clear this NIRMIQ thread from local memory? Indexed documents remain available.",
    );
    if (!confirmed) return;
    setBusy("privacy");
    setError("");
    try {
      const response = await deleteSession(sessionId.trim());
      setQueryHistory([]);
      setQueryResult(null);
      setMemory(null);
      setTimeline(null);
      setError(`Cleared ${response.deleted_messages} local thread messages.`);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function onPurgeDocuments() {
    if (busy !== "") return;
    const confirmed = window.confirm(
      "Clear all indexed material from NIRMIQ? This removes local chunks, summaries, jobs, exam artifacts, and vector entries. Source files on disk are not deleted.",
    );
    if (!confirmed) return;
    setBusy("privacy");
    setError("");
    try {
      const response = await purgeDocuments();
      setDocuments([]);
      setDocumentId("");
      setSelectedDocumentDetail(null);
      setSelectedChunkId("");
      setIngestStatus(null);
      setIngestJobs(null);
      setQuestionBankItems([]);
      setDiagramAssets([]);
      setExamProfile(null);
      setQueryResult(null);
      setDeepView("evidence");
      setError(`Cleared ${response.deleted_count} indexed material item(s). Source files were not deleted.`);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  function selectDocument(item: DocumentItem) {
    setDocumentId(item.id);
    setSelectedChunkId("");
    setSelectedDocumentDetail(null);
    void Promise.all([loadDocumentState(item.id), loadDocumentDetail(item.id)]);
    setDeepView("evidence");
  }

  function selectWorkspaceSection(section: WorkspaceSection) {
    setWorkspaceSection(section);
    const nextMode = STUDY_MODES.find((mode) => mode.section === section)?.value ?? "research";
    setStudyMode(nextMode);
    if (section === "general") {
      setRetrievalProfile("fast");
    } else if (section === "paper") {
      setRetrievalProfile("precision");
    } else if (section === "exam") {
      setRetrievalProfile("precision");
    } else {
      setRetrievalProfile("balanced");
    }
  }

  function applyGoldenDemoQuestion(sample: GoldenDemoQuestion) {
    const matchingDocument = sample.sourcePathIncludes
      ? documents.find((item) => item.source_path.includes(sample.sourcePathIncludes ?? ""))
      : null;
    if (sample.sourcePathIncludes && !matchingDocument) {
      setError("Load the golden demo first so this prompt can attach the expected source.");
    }
    if (matchingDocument) {
      setDocumentId(matchingDocument.id);
      setSelectedChunkId("");
      setSelectedDocumentDetail(null);
      void Promise.all([loadDocumentState(matchingDocument.id), loadDocumentDetail(matchingDocument.id)]);
    }
    selectWorkspaceSection(sample.section);
    setStudyMode(sample.mode);
    setRetrievalMode("hybrid");
    setRetrievalProfile(sample.section === "general" ? "fast" : sample.section === "research" ? "balanced" : "precision");
    setQuery(sample.query);
    setShowInspector(true);
    setDeepView("evidence");
    window.requestAnimationFrame(() => queryInputRef.current?.focus());
  }

  async function onSaveExamProfile() {
    if (!documentId || !sessionId.trim()) return;
    setExamAction("profile");
    setError("");
    try {
      const profile = await upsertExamProfile({
        session_id: sessionId.trim(),
        document_id: documentId,
        title: `${activeMaterialName} Exam Profile`,
        marks: examMarks,
        answer_style: examAnswerStyle,
        content_type: examContentType,
        instructions: examInstructions.trim() || undefined,
      });
      setExamProfile(profile);
    } catch (err) {
      setError(String(err));
    } finally {
      setExamAction("");
    }
  }

  async function onImportQuestionBank() {
    if (!documentId || !questionBankInput.trim()) return;
    setExamAction("questions");
    setError("");
    try {
      const response = await importQuestionBank({
        document_id: documentId,
        raw_text: questionBankInput,
      });
      setQuestionBankItems(response.items);
    } catch (err) {
      setError(String(err));
    } finally {
      setExamAction("");
    }
  }

  async function onExtractDiagrams(force = false) {
    if (!documentId) return;
    setExamAction("diagrams");
    setError("");
    try {
      const response = await extractDiagrams({ document_id: documentId, force });
      setDiagramAssets(response.assets);
    } catch (err) {
      setError(String(err));
    } finally {
      setExamAction("");
    }
  }

  function selectCitation(documentIdValue: string, chunkId: string) {
    setDocumentId(documentIdValue);
    setSelectedChunkId(chunkId);
    setSelectedDocumentDetail(null);
    void Promise.all([loadDocumentState(documentIdValue), loadDocumentDetail(documentIdValue)]);
    setShowInspector(true);
    setDeepView("evidence");
  }

  function clearThread() {
    setSessionId(`nirmiq-thread-${Date.now().toString(36)}`);
    setQueryHistory([]);
    setQueryResult(null);
    setTimeline(null);
    setMemory(null);
    setSelectedChunkId("");
    setError("");
  }

  function applySuggestion(value: string) {
    setQuery(value);
    window.requestAnimationFrame(() => queryInputRef.current?.focus());
  }

  function unlockLocalWorkspace() {
    const name = displayName.trim() || "Local Researcher";
    setDisplayName(name);
    setIsUnlocked(true);
    window.localStorage.setItem("nirmiq.localProfileName", name);
    window.localStorage.setItem("nirmiq.localEmail", email.trim());
    window.localStorage.setItem("nirmiq.localPhone", phone.trim());
    window.localStorage.setItem("nirmiq.localUnlocked", "true");
  }

  function onQueryKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (busy !== "" || !canQuery) return;
      queryFormRef.current?.requestSubmit();
    }
  }

  function loadEvalReportFromText(rawText: string) {
    const trimmed = rawText.trim();
    if (!trimmed) {
      setEvalReport(null);
      setEvalReportError("");
      return;
    }
    try {
      const parsed = JSON.parse(trimmed) as EvalReportPayload;
      setEvalReport(parsed);
      setEvalReportError("");
    } catch (err) {
      setEvalReport(null);
      setEvalReportError(String(err));
    }
  }

  function onEvalReportFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    void file
      .text()
      .then((text) => {
        setEvalReportInput(text);
        loadEvalReportFromText(text);
      })
      .catch((err) => {
        setEvalReport(null);
        setEvalReportError(String(err));
      });
  }

  if (!mounted) {
    return (
      <main className="nirmiq-v2" suppressHydrationWarning>
        <section className="client-boot">
          <p className="eyebrow">{PRODUCT_TAGLINE}</p>
          <h1>{PRODUCT_NAME}</h1>
          <p>Preparing your local study workspace...</p>
        </section>
      </main>
    );
  }

  if (!isUnlocked) {
    return (
      <LocalLogin
        displayName={displayName}
        email={email}
        phone={phone}
        onContinue={unlockLocalWorkspace}
        onDisplayNameChange={setDisplayName}
        onEmailChange={setEmail}
        onPhoneChange={setPhone}
      />
    );
  }

  return (
    <main className={cx("nirmiq-v2", showLibrary && "library-open", showInspector && "inspector-open")}>
      <aside className="material-rail">
        <section className="identity-card">
          <div className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">
              <img alt="" src="/brand/nirmiq-ais-mark.svg" />
            </div>
            <div>
              <strong>{PRODUCT_NAME}</strong>
              <span>{PRODUCT_TAGLINE}</span>
            </div>
          </div>
          <p className="copy">
            {displayName}&apos;s local ChatGPT-style workspace for study material, citations, papers,
            and exam prep.
          </p>
          <div className="chip-row">
            <button className="chip" type="button" onClick={onHealthCheck} disabled={busy !== ""}>
              <span className={cx("status-dot", health === "ok" && "ok")} />
              Local runtime {health}
            </button>
            <span className="chip sage">Local-first</span>
            <span className="chip teal">{documents.length} materials</span>
          </div>
          <button className="button primary sidebar-new-thread" type="button" onClick={clearThread}>
            New Study Thread
          </button>
          <button className="button ghost sidebar-new-thread" type="button" onClick={onLoadGoldenDemo} disabled={busy !== ""}>
            {busy === "demo" ? "Loading demo..." : "Load Golden Demo"}
          </button>
        </section>

        <section className="rail-section golden-demo-card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Publish Proof</p>
              <h2>Golden Demo</h2>
            </div>
            <span className="chip sage">offline</span>
          </div>
          <p className="copy">
            Loads four local demo sources and locks the review path: research, summary, paper, exam, and abstention.
          </p>
          <div className="timeline-list">
            {GOLDEN_DEMO_QUESTIONS.map((sample) => (
              <button
                className="material-card demo-prompt-card"
                key={sample.label}
                onClick={() => applyGoldenDemoQuestion(sample)}
                type="button"
              >
                <span className="material-title">{sample.label}</span>
                <span className="tiny">{sample.note}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="rail-section">
          <div className="section-head">
            <h2>Recent Study Threads</h2>
            <span className="chip copper">{queryHistory.length}</span>
          </div>
          <div className="timeline-list">
            {queryHistory.length ? (
              queryHistory.slice(-4).reverse().map((run) => (
                <button
                  className="material-card"
                  key={`${run.timestamp}-thread`}
                  onClick={() => {
                    setSessionId(run.session_id);
                    applySuggestion(run.query);
                  }}
                  type="button"
                >
                  <span className="material-title">{previewText(run.query, 64)}</span>
                  <span className="tiny">{modeLabel(run.mode)} / {formatDate(run.timestamp)}</span>
                </button>
              ))
            ) : (
              <div className="material-card">
                <strong>No thread history yet</strong>
                <p className="copy">Ask your first question to start a local study thread.</p>
              </div>
            )}
          </div>
        </section>

        <section className="rail-section">
          <div className="section-head">
            <h2>Study Material</h2>
            <span className="chip copper">{documents.length} indexed</span>
          </div>
          <form className="material-form panel" onSubmit={onIngest}>
            <button
              className="button primary"
              disabled={busy !== ""}
              onClick={() => uploadInputRef.current?.click()}
              type="button"
            >
              {busy === "ingest" ? "Uploading..." : "Upload file"}
            </button>
            <p className="tiny">
              Supports PDF, text, Markdown, and image files. Photo OCR depends on local OCR availability.
            </p>
            <details className="composer-settings compact-details">
              <summary>
                Add by local path
                <span>Advanced</span>
              </summary>
              <label className="label">
                Local path
                <input
                  className="input"
                  value={sourcePath}
                  onChange={(event) => setSourcePath(event.target.value)}
                  placeholder={DEFAULT_SOURCE_PATH}
                />
              </label>
              <label className="label">
                Material title
                <input
                  className="input"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Unit 3 OS Notes"
                />
              </label>
              <button className="button ghost" disabled={!canIngest || busy !== ""} type="submit">
                {busy === "ingest" ? "Indexing source..." : "Index local path"}
              </button>
            </details>
          </form>
        </section>

        <section className="rail-section">
          <div className="section-head">
            <h2>Knowledge Base</h2>
            <button className="button ghost" type="button" onClick={() => void loadDocuments()} disabled={busy !== ""}>
              Refresh
            </button>
          </div>
          {selectedDocument ? (
            <button
              className="button danger"
              disabled={busy !== "" || !documentId}
              onClick={onDeleteSelectedDocument}
              type="button"
            >
              {busy === "delete" ? "Removing..." : "Remove material"}
            </button>
          ) : null}
          <div className="privacy-card">
            <div>
              <p className="eyebrow">Local Data</p>
              <strong>Private by default</strong>
              <span>Export or reset local workspace state without cloud sync.</span>
            </div>
            <div className="privacy-actions">
              <button className="button ghost" disabled={busy !== ""} onClick={onExportThread} type="button">
                Export thread
              </button>
              <button className="button ghost" disabled={busy !== ""} onClick={onClearSession} type="button">
                Clear thread
              </button>
              <button
                className="button danger"
                disabled={busy !== "" || documents.length === 0}
                onClick={onPurgeDocuments}
                type="button"
              >
                Clear indexed material
              </button>
            </div>
          </div>
          <div className="material-list">
            {documents.length ? (
              documents.map((item) => (
                <button
                  className={cx("material-card", item.id === documentId && "active")}
                  key={item.id}
                  onClick={() => selectDocument(item)}
                  type="button"
                >
                  <span className="material-title">{item.title || "Untitled material"}</span>
                  <span className="tiny">{item.status} / {item.active_chunk_count} evidence chunks</span>
                  <span className="tiny path">{item.source_path}</span>
                </button>
              ))
            ) : (
              <div className="material-card">
                <strong>No material indexed yet</strong>
                <p className="copy">Add a PDF or text file from your laptop to begin.</p>
              </div>
            )}
          </div>
          <div className="legal-links sidebar-links">
            <a href="/privacy_policy.md" target="_blank" rel="noreferrer">Privacy</a>
            <a href="/terms_conditions.md" target="_blank" rel="noreferrer">Terms</a>
            <a href="/security.md" target="_blank" rel="noreferrer">Security</a>
          </div>
        </section>
      </aside>

      <section className="study-thread">
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
            <div className="workspace-switcher">
              {WORKSPACE_SECTIONS.map((section) => (
                <button
                  className={cx("section-button", workspaceSection === section.value && "active")}
                  data-testid={`workspace-${section.value}`}
                  key={section.value}
                  onClick={() => selectWorkspaceSection(section.value)}
                  type="button"
                >
                  <strong>{section.label}</strong>
                  <span>{section.hint}</span>
                </button>
              ))}
            </div>
            <div className="top-actions">
              <button className="button ghost" type="button" onClick={() => setShowLibrary((current) => !current)}>
                {showLibrary ? "Hide Knowledge Base" : "Knowledge Base"}
              </button>
              <button className="button ghost" type="button" onClick={() => setShowInspector((current) => !current)}>
                {showInspector ? "Hide Deep Research" : "Deep Research"}
              </button>
            </div>
          </div>
          <div className="route-strip">
            <span className="chip copper">{modeLabel(studyMode)}</span>
            <span className="chip sage">{selectedDocument ? activeMaterialName : "No active source"}</span>
            <span className="tiny">
              {workspaceSection === "general"
                ? "Chat first. NIRMIQ cites local material when evidence is available."
                : currentSection.hint}
            </span>
          </div>
        </header>

        <div className="thread-scroll">
          {queryHistory.length ? (
            <div className="turn-list">
              {queryHistory.map((run, index) => (
                <article className="turn" key={`${run.timestamp}-${index}`}>
                  <div className="bubble user">
                    <div className="message-meta">
                      <span className="tiny">You / {modeLabel(run.mode)}</span>
                      <span className="chip">{run.profile}</span>
                    </div>
                    <div className="answer">{run.query}</div>
                  </div>
                  <div className="bubble assistant">
                    <div className="message-meta">
                      <span className="tiny">NIRMIQ / {formatDate(run.timestamp)}</span>
                      <div className="meta-chip-row">
                        <span className={cx("chip", run.response.grounded ? "sage" : "copper")}>
                          {run.response.grounded ? "grounded" : "review"} / {run.response.citations.length} citations
                        </span>
                        {getVerificationBadge(run.response) ? (
                          <span className={cx("chip", getVerificationBadge(run.response)?.className)}>
                            {getVerificationBadge(run.response)?.label}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    {run.mode === "study_guide" ? (
                      <StudyGuideAnswer answer={run.response.answer} />
                    ) : (
                      <div className="answer">{run.response.answer}</div>
                    )}
                    <div className="trust-line">
                      <span className={cx("chip", run.response.grounded ? "sage" : "copper")}>
                        {getTrustCopy(run.response)}
                      </span>
                      <button
                        className="clear-link"
                        onClick={() => {
                          setQueryResult(run.response);
                          setShowInspector(true);
                          setDeepView("evidence");
                        }}
                        type="button"
                      >
                        View Deep Research
                      </button>
                    </div>
                    {run.response.citations.length ? (
                      <div className="citation-row evidence-trail">
                        <span className="evidence-label">Evidence Trail</span>
                        {run.response.citations.slice(0, 6).map((citation, citationIndex) => (
                          <button
                            className={cx("citation-chip", citation.chunk_id === selectedChunkId && "active")}
                            key={`${run.timestamp}-${citation.chunk_id}-${citationIndex}`}
                            onClick={() => selectCitation(citation.document_id, citation.chunk_id)}
                            type="button"
                          >
                            Evidence {citationIndex + 1}
                            {citation.page_start ? ` / p.${citation.page_start}` : ""}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </article>
              ))}
              <div ref={chatEndRef} />
            </div>
          ) : (
            <section className="empty-state">
              <p className="eyebrow">Upload. Understand. Verify. Learn.</p>
              <h2>What do you want to understand today?</h2>
              <p className="copy">Upload study material or ask from your indexed documents.</p>
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
                  onClick={() => {
                    selectWorkspaceSection("research");
                    setStudyMode("research");
                    applySuggestion("Explain this topic simply from my study material.");
                  }}
                  type="button"
                >
                  Explain this topic simply
                </button>
                <button
                  className="button ghost"
                  onClick={() => {
                    selectWorkspaceSection("exam");
                    setStudyMode("exam_answer");
                    applySuggestion("Make this into a 10-mark exam answer.");
                  }}
                  type="button"
                >
                  Make 10-mark exam answer
                </button>
                <button
                  className="button ghost"
                  onClick={() => {
                    selectWorkspaceSection("research");
                    setStudyMode("summary");
                    applySuggestion("Summarize selected document.");
                  }}
                  type="button"
                >
                  Summarize selected document
                </button>
                <button
                  className="button ghost"
                  onClick={() => {
                    selectWorkspaceSection("exam");
                    setStudyMode("compare_concepts");
                    applySuggestion("Compare concepts from my notes.");
                  }}
                  type="button"
                >
                  Compare concepts from my notes
                </button>
              </div>
            </section>
          )}
        </div>

        <form className="composer-wrap" ref={queryFormRef} onSubmit={onQuery}>
          <div className="composer-card">
            <input
              accept=".pdf,.txt,.md,.markdown,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,image/*,application/pdf,text/*"
              className="file-input"
              onChange={onUploadFile}
              ref={uploadInputRef}
              type="file"
            />
            <div className="source-cockpit">
              <div className="source-status">
                <span className={cx("source-dot", selectedDocument && "ok")} />
                <div>
                  <span className="source-label">Active Sources</span>
                  <strong>{selectedDocument ? activeMaterialName : "No material attached"}</strong>
                </div>
              </div>
              <div className="source-actions">
                <span className="mini-stat">
                  {selectedDocumentDetail?.active_chunk_count ?? selectedDocument?.active_chunk_count ?? 0} chunks
                </span>
                <span className={cx("mini-stat", queryResult?.grounded ? "ok" : "")}>
                  {groundingLabel}
                </span>
                {workspaceSection === "exam" ? (
                  <button
                    className="quick-action"
                    disabled={busy !== ""}
                    onClick={onGenerateExamPdf}
                    type="button"
                  >
                    Custom PDF
                  </button>
                ) : null}
                <button
                  className="quick-action"
                  disabled={!documentId || busy !== ""}
                  onClick={onSummarizeSelectedSource}
                  type="button"
                >
                  Summarize PDF
                </button>
                <button
                  className="quick-action ghost"
                  disabled={!currentRun || busy !== ""}
                  onClick={onExportCurrentRun}
                  type="button"
                >
                  Export
                </button>
                <button
                  className="quick-action ghost"
                  disabled={busy !== ""}
                  onClick={() => uploadInputRef.current?.click()}
                  type="button"
                >
                  Upload
                </button>
                <button
                  className="quick-action ghost"
                  onClick={() => setComposerCollapsed((current) => !current)}
                  type="button"
                >
                  {composerCollapsed ? "Open Search" : "Minimize"}
                </button>
              </div>
            </div>
            {composerCollapsed ? (
              <div className="composer-minimized">
                Search box minimized. Responses have more room. Use Open Search when you need to ask the next question.
              </div>
            ) : (
              <>
                <div className="composer-input-shell">
                  <button
                    aria-label="Upload file or photo"
                    className="attach-button"
                    disabled={busy !== ""}
                    onClick={() => uploadInputRef.current?.click()}
                    type="button"
                    title="Upload PDF, document, or photo"
                  >
                    +
                  </button>
                  <textarea
                    className="textarea"
                    ref={queryInputRef}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    onKeyDown={onQueryKeyDown}
                    placeholder={busy === "ingest" ? "Uploading and indexing your file..." : activePlaceholder}
                  />
                  <button className="send-button" disabled={!canQuery || busy !== ""} type="submit">
                    {busy === "query" ? "Reading" : activeActionLabel}
                  </button>
                </div>
                <details className="composer-settings">
                  <summary>
                    Tuning
                    <span>{retrievalMode.toUpperCase()} / {retrievalProfile} / {sessionId}</span>
                  </summary>
                  <div className="composer-meta">
                    <label className="label">
                      Thread
                      <input className="input" value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
                    </label>
                    <label className="label">
                      Route
                      <select
                        className="select"
                        value={studyMode}
                        onChange={(event) => setStudyMode(event.target.value as StudyMode)}
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
                        onChange={(event) => setRetrievalMode(event.target.value as RetrievalMode)}
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
                        onChange={(event) => setRetrievalProfile(event.target.value as RetrievalProfile)}
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
                <div className="composer-actions">
                  <p className="composer-hint">
                    {latestCitations.length
                      ? `${latestCitations.length} evidence links ready. Open Deep Research to inspect citations.`
                      : "Answers stay grounded in the selected study material when evidence is available."}
                  </p>
                  <div className="chip-row" style={{ marginTop: 0 }}>
                    <button className="clear-link" type="button" onClick={clearThread}>
                      Clear Thread
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </form>
      </section>

      <aside className="deep-rail">
        <div className="deep-panel-head">
          <div>
            <p className="eyebrow">Deep Research</p>
            <h2>Evidence and reasoning details</h2>
          </div>
          <button className="button ghost" type="button" onClick={() => setShowInspector(false)}>
            Close
          </button>
        </div>
        <section className="grounding-meter">
          <div className="section-head">
            <div>
              <p className="eyebrow">Grounding Strength</p>
              <h2>{groundingLabel}</h2>
            </div>
            <span className="chip copper">{Math.round(Math.min(1, groundingScore) * 100)}%</span>
          </div>
          <div className="meter-track">
            <div className="meter-fill" style={{ width: `${Math.max(4, Math.min(100, groundingScore * 100))}%` }} />
          </div>
          <p className="copy">
            Evidence first. Memory can help the thread, but uploaded material remains the source of truth.
          </p>
          <div className="proof-grid">
            <div>
              <span>Intent</span>
              <strong>{detectedIntent}</strong>
            </div>
            <div>
              <span>Citation coverage</span>
              <strong>{citationCoverage}</strong>
            </div>
            <div>
              <span>Cache</span>
              <strong>{retrievalMeta.cache_hit === true ? "hit" : retrievalMeta.cache_hit === false ? "miss" : "n/a"}</strong>
            </div>
            <div>
              <span>Source</span>
              <strong>{isGoldenDemoSource ? "golden demo" : selectedDocument ? "local material" : "none"}</strong>
            </div>
          </div>
        </section>

        <div className="tab-row">
          {(["evidence", "context", "compare", "eval"] as DeepView[]).map((view) => (
            <button
              className={cx("tab", deepView === view && "active")}
              key={view}
              onClick={() => setDeepView(view)}
              type="button"
            >
              {view === "evidence" ? "Evidence Trail" : view === "context" ? "Study Context" : view}
            </button>
          ))}
        </div>

        {workspaceSection === "paper" ? (
          <section className="tool-panel rail-section" data-testid="paper-lab-panel">
            <div className="panel">
              <div className="section-head">
                <div>
                  <p className="eyebrow">V4 Paper Lab</p>
                  <h2>Citation Workspace</h2>
                </div>
                <span className="chip sage">
                  {paperLabArtifact?.evidence_count ?? latestCitations.length} evidence
                </span>
              </div>
              <p className="copy">
                Draft with source-backed structure. NIRMIQ organizes retrieved chunks into an outline,
                citation clusters, and a related-work matrix.
              </p>
              <button
                className="button primary"
                disabled={!currentRun?.response.answer}
                onClick={onCopyPaperMarkdown}
                style={{ marginTop: 12 }}
                type="button"
              >
                Copy Markdown Draft
              </button>
            </div>

            <div className="panel">
              <div className="section-head">
                <h2>Paper Outline</h2>
                <span className="chip">{paperLabArtifact?.source_count ?? 0} sources</span>
              </div>
              <div className="timeline-list" style={{ marginTop: 12 }}>
                {(paperLabArtifact?.outline ?? [
                  "Title and problem framing",
                  "Background and related work",
                  "Methodology or system design",
                  "Evidence-backed discussion",
                  "Limitations and future work",
                ]).map((item, index) => (
                  <div className="timeline-card" key={`${item}-${index}`}>
                    <div className="message-meta">
                      <strong>{index + 1}. {item}</strong>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="section-head">
                <h2>Related-Work Matrix</h2>
                <span className="chip">{paperLabArtifact?.related_work_matrix?.length ?? 0} rows</span>
              </div>
              <div className="timeline-list" style={{ marginTop: 12 }}>
                {paperLabArtifact?.related_work_matrix?.slice(0, 5).map((row, index) => (
                  <div className="timeline-card" key={`${row.evidence}-${index}`}>
                    <div className="message-meta">
                      <strong>{row.claim_area ?? "Evidence"}</strong>
                      <span className="tiny">
                        Evidence {row.evidence ?? index + 1}
                        {row.page ? ` / p.${row.page}` : ""}
                      </span>
                    </div>
                    <p className="chunk-text">{row.use_in_paper ?? "Use as supporting evidence."}</p>
                    <span className="tiny">{previewText(row.excerpt, 180)}</span>
                  </div>
                )) ?? (
                  <p className="copy">
                    Ask Paper Lab for a research paper section to generate the matrix.
                  </p>
                )}
              </div>
            </div>
          </section>
        ) : null}

        {workspaceSection === "exam" ? (
          <section className="tool-panel rail-section" data-testid="exam-lab-panel">
            <div className="panel">
              <div className="section-head">
                <h2>Exam Lab Setup</h2>
                <span className="chip copper">{examProfile ? "saved" : "draft"}</span>
              </div>
              <div className="exam-grid" style={{ marginTop: 12 }}>
                <label className="label">
                  Marks
                  <input
                    className="input"
                    min={1}
                    max={100}
                    type="number"
                    value={examMarks}
                    onChange={(event) => setExamMarks(Number(event.target.value))}
                  />
                </label>
                <label className="label">
                  Answer style
                  <select
                    className="select"
                    value={examAnswerStyle}
                    onChange={(event) => setExamAnswerStyle(event.target.value)}
                  >
                    <option value="exam-ready">Exam-ready</option>
                    <option value="stepwise">Stepwise</option>
                    <option value="concise">Concise</option>
                    <option value="long-form">Long-form</option>
                  </select>
                </label>
                <label className="label">
                  Content type
                  <select
                    className="select"
                    value={examContentType}
                    onChange={(event) => setExamContentType(event.target.value)}
                  >
                    <option value="conceptual">Conceptual</option>
                    <option value="numerical">Numerical</option>
                    <option value="diagram-heavy">Diagram-heavy</option>
                    <option value="mixed">Mixed</option>
                  </select>
                </label>
              </div>
              <label className="label" style={{ marginTop: 12 }}>
                Custom answer instructions
                <textarea
                  className="textarea"
                  value={examInstructions}
                  onChange={(event) => setExamInstructions(event.target.value)}
                />
              </label>
              <button
                className="button primary"
                disabled={!documentId || examAction !== ""}
                onClick={onSaveExamProfile}
                style={{ marginTop: 12 }}
                type="button"
              >
                {examAction === "profile" ? "Saving..." : "Save Exam Profile"}
              </button>
            </div>

            <div className="panel">
              <div className="section-head">
                <h2>Question Bank</h2>
                <span className="chip">{questionBankItems.length} questions</span>
              </div>
              <label className="label" style={{ marginTop: 12 }}>
                Paste questions
                <textarea
                  className="textarea"
                  placeholder="1. Explain retrieval augmented generation. (10 marks)"
                  value={questionBankInput}
                  onChange={(event) => setQuestionBankInput(event.target.value)}
                />
              </label>
              <button
                className="button"
                disabled={!documentId || !questionBankInput.trim() || examAction !== ""}
                onClick={onImportQuestionBank}
                style={{ marginTop: 12 }}
                type="button"
              >
                {examAction === "questions" ? "Importing..." : "Import Questions"}
              </button>
              <div className="timeline-list" style={{ marginTop: 12 }}>
                {questionBankItems.slice(0, 5).map((item, index) => (
                  <div className="timeline-card" key={item.id}>
                    <div className="message-meta">
                      <strong>Q{index + 1}</strong>
                      <span className="tiny">{item.marks ? `${item.marks} marks` : "marks unset"}</span>
                    </div>
                    <p className="chunk-text">{item.question}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="section-head">
                <h2>Source Diagrams</h2>
                <span className="chip">{diagramAssets.length} assets</span>
              </div>
              <p className="copy">
                Extracts embedded PDF images into local processed assets and links them back to pages.
              </p>
              <div className="chip-row">
                <button
                  className="button"
                  disabled={!documentId || examAction !== ""}
                  onClick={() => void onExtractDiagrams(false)}
                  type="button"
                >
                  {examAction === "diagrams" ? "Extracting..." : "Extract Diagrams"}
                </button>
                <button
                  className="button ghost"
                  disabled={!documentId || examAction !== ""}
                  onClick={() => void onExtractDiagrams(true)}
                  type="button"
                >
                  Refresh Assets
                </button>
              </div>
              <div className="timeline-list" style={{ marginTop: 12 }}>
                {diagramAssets.slice(0, 5).map((asset) => (
                  <div className="timeline-card" key={asset.id}>
                    <div className="message-meta">
                      <strong>Page {asset.page_number}</strong>
                      <span className="tiny">
                        {asset.width && asset.height ? `${asset.width}x${asset.height}` : "size unknown"}
                      </span>
                    </div>
                    <a
                      className="diagram-preview"
                      href={diagramAssetUrl(asset.id)}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <img alt={asset.caption || `Diagram from page ${asset.page_number}`} src={diagramAssetUrl(asset.id)} />
                    </a>
                    <p className="tiny path">{asset.image_path}</p>
                    {asset.caption ? <p className="chunk-text">{asset.caption}</p> : null}
                  </div>
                ))}
              </div>
            </div>
          </section>
        ) : null}

        {deepView === "evidence" ? (
          <section className="tool-panel rail-section">
            <div className="panel">
              <div className="section-head">
                <h2>{selectedDocumentDetail?.title || selectedDocument?.title || "No material selected"}</h2>
                <button className="button ghost" type="button" onClick={onRefreshStatus} disabled={!documentId || busy !== ""}>
                  Refresh
                </button>
              </div>
              <p className="tiny path">
                {selectedDocumentDetail?.source_path || selectedDocument?.source_path || "Select study material."}
              </p>
              <div className="metric-grid" style={{ marginTop: 12 }}>
                <div className="metric-card">
                  <strong>{selectedDocumentDetail?.active_chunk_count ?? selectedDocument?.active_chunk_count ?? 0}</strong>
                  <span className="tiny">chunks</span>
                </div>
                <div className="metric-card">
                  <strong>{ingestStatus?.status ?? "idle"}</strong>
                  <span className="tiny">index</span>
                </div>
                <div className="metric-card">
                  <strong>{ingestJobs?.jobs.length ?? 0}</strong>
                  <span className="tiny">jobs</span>
                </div>
              </div>
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
                      className={cx("material-card", citation.chunk_id === selectedChunkId && "active")}
                      key={`${citation.chunk_id}-${index}`}
                      onClick={() => selectCitation(citation.document_id, citation.chunk_id)}
                      type="button"
                    >
                      <span className="material-title">Evidence {index + 1}</span>
                      <span className="tiny">
                        {citation.page_start ? `Page ${citation.page_start}` : "Page unknown"}
                        {typeof citation.score === "number" ? ` / score ${citation.score.toFixed(2)}` : ""}
                      </span>
                      <span className="tiny">{previewText(citation.excerpt, 220)}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {selectedChunk ? (
              <div className="chunk-card active">
                <div className="chunk-head">
                  <strong>Focused chunk {selectedChunk.chunk_index + 1}</strong>
                  <span className="chip">{selectedChunk.token_count} tokens</span>
                </div>
                <p className="chunk-text">{previewText(selectedChunk.text, 900)}</p>
              </div>
            ) : null}

            <div className="panel">
              <div className="section-head">
                <h2>Retrieved chunks</h2>
                <span className="tiny">{visibleChunks.length} visible</span>
              </div>
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
                      onClick={() => setSelectedChunkId(chunk.id)}
                      type="button"
                    >
                      <div className="chunk-head">
                        <strong>Chunk {chunk.chunk_index + 1}</strong>
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
            </div>
          </section>
        ) : null}

        {deepView === "context" ? (
          <section className="tool-panel rail-section">
            <div className="panel">
              <div className="section-head">
                <h2>Study Context</h2>
                <button className="button ghost" type="button" onClick={() => void loadSessionState(sessionId)} disabled={!sessionId || busy !== ""}>
                  Refresh
                </button>
              </div>
              <p className="copy">{memory?.summary || "Study memory appears after your first grounded exchange."}</p>
              <div className="chip-row">
                <span className="chip">{memory?.message_count ?? 0} messages</span>
                <span className="chip">Memory never overrides evidence</span>
              </div>
            </div>
            <div className="timeline-list">
              {(timeline?.messages ?? []).slice(-8).map((message) => (
                <div className="timeline-card" key={message.id}>
                  <div className="message-meta">
                    <strong>{message.role}</strong>
                    <span className="tiny">{formatDate(message.created_at)}</span>
                  </div>
                  <p className="chunk-text">{previewText(message.content, 280)}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {deepView === "compare" ? (
          <section className="tool-panel rail-section">
            <div className="panel">
              <div className="section-head">
                <h2>Answer Delta</h2>
                <span className="chip">{answerDiff.length} lines</span>
              </div>
              <p className="copy">Compare the last two grounded responses when tuning mode or retrieval profile.</p>
            </div>
            <div className="diff-list">
              {answerDiff.length ? (
                answerDiff.map((line, index) => (
                  <div className={cx("diff-card", line.kind)} key={`${line.kind}-${index}`}>
                    <strong>{line.kind}</strong>
                    <p className="chunk-text">{line.text}</p>
                  </div>
                ))
              ) : (
                <div className="diff-card">
                  <strong>Run two questions</strong>
                  <p className="copy">The change log will appear here.</p>
                </div>
              )}
            </div>
          </section>
        ) : null}

        {deepView === "eval" ? (
          <section className="tool-panel rail-section">
            <div className="panel">
              <div className="section-head">
                <h2>Retrieval Evaluation</h2>
                <label className="button ghost">
                  Load JSON
                  <input accept=".json,application/json" hidden type="file" onChange={onEvalReportFileChange} />
                </label>
              </div>
              <p className="copy">Paste output from the retrieval evaluation script to inspect MRR and hit rates.</p>
            </div>
            <textarea
              className="eval-input"
              value={evalReportInput}
              onChange={(event) => {
                setEvalReportInput(event.target.value);
                loadEvalReportFromText(event.target.value);
              }}
              placeholder="Paste retrieval evaluation JSON..."
            />
            {evalReportError ? <div className="toast" style={{ position: "static", transform: "none", width: "100%" }}>{evalReportError}</div> : null}
            {evalReport ? (
              <div className="eval-list">
                <div className="eval-card">
                  <strong>{evalReport.dataset || "Evaluation report"}</strong>
                  <p className="tiny">{evalReport.evaluation_mode || "mode unknown"}</p>
                </div>
                {Object.entries(evalReport.results ?? {}).map(([mode, result]) => (
                  <div className="eval-card" key={mode}>
                    <div className="message-meta">
                      <strong>{result.mode || mode}</strong>
                      <span className="chip">{result.samples ?? 0} samples</span>
                    </div>
                    <p className="chunk-text">
                      MRR {typeof result.mrr === "number" ? result.mrr.toFixed(3) : "n/a"} / Hit@3{" "}
                      {typeof result.hit_rate_at_3 === "number" ? result.hit_rate_at_3.toFixed(3) : "n/a"} / Hit@5{" "}
                      {typeof result.hit_rate_at_5 === "number" ? result.hit_rate_at_5.toFixed(3) : "n/a"}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}
          </section>
        ) : null}
      </aside>

      {error ? (
        <div className="toast" role="alert">
          {error}
        </div>
      ) : null}
    </main>
  );
}

