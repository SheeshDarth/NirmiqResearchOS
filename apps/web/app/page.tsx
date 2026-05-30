"use client";

import { ChangeEvent, FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  deleteDocument,
  diagramAssetUrl,
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
type BusyState = "" | "health" | "ingest" | "query" | "status" | "documents" | "delete";
type DeepView = "evidence" | "context" | "compare" | "eval";
type Chunk = DocumentDetailResponse["chunks"][number];

type ChatRun = {
  session_id: string;
  query: string;
  mode: StudyMode;
  profile: RetrievalProfile;
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

const DEFAULT_SOURCE_PATH = "C:\\Nirmiq-researchOS\\data\\raw\\attention_is_all_you_need.pdf";
const PRODUCT_NAME = "NIRMIQ";
const PRODUCT_TAGLINE = "Academic Intelligence";
const PRODUCT_DESCRIPTION = "Private research chat for documents, citations, papers, and exams.";

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
  onDisplayNameChange,
  onContinue,
}: {
  displayName: string;
  onDisplayNameChange: (value: string) => void;
  onContinue: () => void;
}) {
  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand-lockup hero">
          <div className="brand-mark" aria-hidden="true">
            <img alt="" src="/brand/nirmiq-mark.png" />
          </div>
          <div>
            <strong>{PRODUCT_NAME}</strong>
            <span>{PRODUCT_TAGLINE}</span>
          </div>
        </div>
        <h1>Chat with your documents. Build with evidence.</h1>
        <p className="copy">
          {PRODUCT_DESCRIPTION} The MVP runs local-first, so your source material stays on your machine.
        </p>
        <label className="label">
          Local profile name
          <input
            className="input"
            onChange={(event) => onDisplayNameChange(event.target.value)}
            placeholder="Siddharth"
            value={displayName}
          />
        </label>
        <button className="button primary" disabled={!displayName.trim()} onClick={onContinue} type="button">
          Enter workspace
        </button>
        <div className="login-proof">
          <span>Local-first</span>
          <span>Citation-aware</span>
          <span>Paper Lab</span>
        </div>
        <div className="why-nirmiq">
          <strong>Why NIRMIQ?</strong>
          <p>
            It keeps the interaction simple like chat, but every serious answer can stay tied to your own
            PDFs, notes, diagrams, and citations.
          </p>
        </div>
        <p className="tiny">
          This is a local profile gate, not cloud authentication. Add real auth only before hosted/multi-user use.
        </p>
      </section>
    </main>
  );
}

function modeLabel(value: StudyMode): string {
  return STUDY_MODES.find((mode) => mode.value === value)?.label ?? "Study";
}

export default function Home() {
  const queryFormRef = useRef<HTMLFormElement | null>(null);
  const queryInputRef = useRef<HTMLTextAreaElement | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const [mounted, setMounted] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [displayName, setDisplayName] = useState("Siddharth");
  const [showLibrary, setShowLibrary] = useState(false);
  const [showInspector, setShowInspector] = useState(false);
  const [health, setHealth] = useState("unknown");
  const [busy, setBusy] = useState<BusyState>("");
  const [error, setError] = useState("");
  const [sourcePath, setSourcePath] = useState(DEFAULT_SOURCE_PATH);
  const [title, setTitle] = useState("Attention Is All You Need");
  const [documentId, setDocumentId] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentDetail, setSelectedDocumentDetail] = useState<DocumentDetailResponse | null>(null);
  const [selectedChunkId, setSelectedChunkId] = useState("");
  const [ingestStatus, setIngestStatus] = useState<IngestStatusResponse | null>(null);
  const [ingestJobs, setIngestJobs] = useState<IngestJobsResponse | null>(null);
  const [sessionId, setSessionId] = useState("siddharth-study-thread");
  const [workspaceSection, setWorkspaceSection] = useState<WorkspaceSection>("research");
  const [studyMode, setStudyMode] = useState<StudyMode>("research");
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
  const availableModes = STUDY_MODES.filter((mode) => mode.section === workspaceSection);
  const currentMode = availableModes.find((mode) => mode.value === studyMode) ?? availableModes[0] ?? STUDY_MODES[0];
  const currentSection = WORKSPACE_SECTIONS.find((section) => section.value === workspaceSection) ?? WORKSPACE_SECTIONS[0];
  const activeMaterialName = selectedDocumentDetail?.title || selectedDocument?.title || "No study material selected";

  useEffect(() => {
    const storedName = window.localStorage.getItem("nirmiq.localProfileName");
    const storedUnlocked = window.localStorage.getItem("nirmiq.localUnlocked") === "true";
    if (storedName) setDisplayName(storedName);
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
        title: title.trim() || fallbackTitle,
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
    if (!canQuery) return;
    await executeQuery(query.trim());
  }

  async function executeQuery(submittedQuery: string, modeOverride: StudyMode = currentMode.value) {
    if (!submittedQuery || !sessionId.trim()) return;
    setBusy("query");
    setError("");
    try {
      const scopedDocumentId =
        workspaceSection === "general" && modeOverride !== "summary" ? undefined : documentId || undefined;
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
            response,
            timestamp: new Date().toISOString(),
          },
        ].slice(-12),
      );
      setQuery("");
      await loadSessionState(response.session_id);
      setDeepView("evidence");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
  }

  async function onSummarizeSelectedSource() {
    if (!documentId || busy !== "") {
      setError("Upload or select a source before summarizing.");
      return;
    }
    setWorkspaceSection("research");
    setStudyMode("summary");
    setRetrievalProfile("balanced");
    await executeQuery("Summarize this PDF with the main ideas, methods, findings, and limitations.", "summary");
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
    setShowInspector(section === "exam");
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
    window.localStorage.setItem("nirmiq.localUnlocked", "true");
  }

  function onQueryKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
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
        onContinue={unlockLocalWorkspace}
        onDisplayNameChange={setDisplayName}
      />
    );
  }

  return (
    <main className={cx("nirmiq-v2", showLibrary && "library-open", showInspector && "inspector-open")}>
      <aside className="material-rail">
        <section className="identity-card">
          <div className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">
              <img alt="" src="/brand/nirmiq-mark.png" />
            </div>
            <div>
              <strong>{PRODUCT_NAME}</strong>
              <span>{PRODUCT_TAGLINE}</span>
            </div>
          </div>
          <p className="copy">
            {displayName}&apos;s local workspace for research-grade answers, citations, engineering papers,
            and exam prep.
          </p>
          <div className="chip-row">
            <button className="chip" type="button" onClick={onHealthCheck} disabled={busy !== ""}>
              <span className={cx("status-dot", health === "ok" && "ok")} />
              API {health}
            </button>
            <span className="chip sage">Local-first</span>
            <span className="chip teal">RTX 4050-aware</span>
          </div>
          <div className="legal-links">
            <a href="/privacy_policy.md" target="_blank" rel="noreferrer">Privacy</a>
            <a href="/terms_conditions.md" target="_blank" rel="noreferrer">Terms</a>
            <a href="/security.md" target="_blank" rel="noreferrer">Security</a>
          </div>
        </section>

        <section className="rail-section">
          <div className="section-head">
            <h2>Source Intake</h2>
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
          </form>
        </section>

        <section className="rail-section">
          <div className="section-head">
            <h2>Source Vault</h2>
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
              {busy === "delete" ? "Removing..." : "Remove selected source"}
            </button>
          ) : null}
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
        </section>
      </aside>

      <section className="study-thread">
        <header className="thread-top">
          <div className="thread-bar">
            <div className="brand-lockup app">
              <div className="brand-mark" aria-hidden="true">
                <img alt="" src="/brand/nirmiq-mark.png" />
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
                {showLibrary ? "Hide Library" : "Library"}
              </button>
              <button className="button ghost" type="button" onClick={() => setShowInspector((current) => !current)}>
                {showInspector ? "Hide Sources" : "Sources"}
              </button>
            </div>
          </div>
          <div className="thread-title">
            <p className="eyebrow">{currentSection.label} Workspace</p>
            <h1>
              {workspaceSection === "general"
                ? "Ask anything"
                : workspaceSection === "paper"
                  ? "Engineering Paper Lab"
                  : workspaceSection === "exam"
                    ? "Exam Lab"
                    : activeMaterialName}
            </h1>
            <p className="copy" style={{ maxWidth: 680 }}>{currentSection.hint}</p>
            <div className="chip-row">
              <span className="chip copper">{modeLabel(studyMode)}</span>
              <span className="chip sage">{activeMaterialName}</span>
            </div>
          </div>
          <div className="mode-grid">
            {availableModes.map((mode) => (
              <button
                className={cx("mode-button", studyMode === mode.value && "active")}
                key={mode.value}
                onClick={() => setStudyMode(mode.value)}
                type="button"
              >
                <strong>{mode.label}</strong>
                <div className="tiny">{mode.hint}</div>
              </button>
            ))}
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
                      <span className={cx("chip", run.response.grounded ? "sage" : "copper")}>
                        {run.response.grounded ? "grounded" : "review"} / {run.response.citations.length} citations
                      </span>
                    </div>
                    {run.mode === "study_guide" ? (
                      <StudyGuideAnswer answer={run.response.answer} />
                    ) : (
                      <div className="answer">{run.response.answer}</div>
                    )}
                    {run.response.citations.length ? (
                      <div className="citation-row">
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
              <h2>
                {workspaceSection === "general"
                  ? "Ask naturally. If local evidence is missing, NIRMIQ will say so."
                  : workspaceSection === "paper"
                    ? "Build engineering research papers with traceable multi-source citations."
                  : workspaceSection === "exam"
                    ? "Prepare answers and study guides from your exact notes."
                    : "Upload a source. Summarize first. Then question every claim."}
              </h2>
              <div className="suggestions">
                {availableModes.slice(0, 4).map((mode) => (
                  <button
                    className="button ghost"
                    key={mode.value}
                    onClick={() => {
                      setStudyMode(mode.value);
                      applySuggestion(mode.prompt);
                    }}
                    type="button"
                  >
                    {mode.label}
                  </button>
                ))}
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
                  <span className="source-label">Selected source</span>
                  <strong>{selectedDocument ? activeMaterialName : "No source selected"}</strong>
                </div>
              </div>
              <div className="source-actions">
                <span className="mini-stat">
                  {selectedDocumentDetail?.active_chunk_count ?? selectedDocument?.active_chunk_count ?? 0} chunks
                </span>
                <span className={cx("mini-stat", queryResult?.grounded ? "ok" : "")}>
                  {groundingLabel}
                </span>
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
                  disabled={busy !== ""}
                  onClick={() => uploadInputRef.current?.click()}
                  type="button"
                >
                  Upload
                </button>
              </div>
            </div>
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
                placeholder={
                  busy === "ingest"
                    ? "Uploading and indexing your file..."
                    : `Ask in ${currentMode.label} mode...`
                }
              />
              <button className="send-button" disabled={!canQuery || busy !== ""} type="submit">
                {busy === "query" ? "Reading" : "Ask"}
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
                  ? `${latestCitations.length} evidence links ready. Click Sources to inspect citations.`
                  : "Answers stay grounded in the selected source when evidence is available."}
              </p>
              <div className="chip-row" style={{ marginTop: 0 }}>
                <button className="clear-link" type="button" onClick={clearThread}>
                  Clear Thread
                </button>
              </div>
            </div>
          </div>
        </form>
      </section>

      <aside className="deep-rail">
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

