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
  saveAnswerFeedback,
  upsertExamProfile,
  uploadDocument,
  type AnswerFeedbackRating,
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
import { LocalLogin } from "../components/local-login";
import { StudyGuideAnswer } from "../components/study-guide-answer";
import { AnswerBody } from "../components/answer-body";
import { ChatEmptyState } from "../components/chat-empty-state";
import { SourceEvidencePanel } from "../components/source-evidence-panel";
import { ThreadHeader } from "../components/thread-header";
import {
  DEFAULT_SOURCE_PATH,
  GOLDEN_DEMO_QUESTIONS,
  GOLDEN_DEMO_SOURCES,
  PRODUCT_NAME,
  PRODUCT_TAGLINE,
  RETRIEVAL_PROFILES,
  STUDY_MODES,
  WORKSPACE_SECTIONS,
  buildAnswerDiff,
  buildPaperLabMarkdown,
  buildRunExportMarkdown,
  composerPlaceholder,
  cx,
  defaultModeForWorkspace,
  downloadTextFile,
  escapeHtml,
  formatDate,
  getGroundingLabel,
  getPaperLabArtifact,
  getTrustCopy,
  getVerificationBadge,
  getVisibleChunks,
  modeLabel,
  previewText,
  workspaceVerb,
  type BusyState,
  type ChatRun,
  type DeepView,
  type DiffLine,
  type GoldenDemoQuestion,
  type PaperLabArtifact,
  type RetrievalMode,
  type RetrievalProfile,
  type StudyMode,
  type WorkspaceSection,
} from "./page-model";


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
  const [showLibrary, setShowLibrary] = useState(false);
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
  const [workspaceSection, setWorkspaceSection] = useState<WorkspaceSection>("research");
  const [studyMode, setStudyMode] = useState<StudyMode>("research");
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>("hybrid");
  const [retrievalProfile, setRetrievalProfile] = useState<RetrievalProfile>("balanced");
  const [query, setQuery] = useState("");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [queryHistory, setQueryHistory] = useState<ChatRun[]>([]);
  const [savedFeedback, setSavedFeedback] = useState<Record<string, AnswerFeedbackRating>>({});
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

  const canIngest = sourcePath.trim().length > 0;
  const canQuery = query.trim().length > 0 && sessionId.trim().length > 0;

  const selectedDocument = useMemo(
    () => documents.find((item) => item.id === documentId) ?? null,
    [documentId, documents],
  );
  const latestCitations = queryResult?.citations ?? [];
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
  const activeMaterialName = selectedDocumentDetail?.title || selectedDocument?.title || "No study material selected";
  const activePlaceholder = composerPlaceholder(workspaceSection, currentMode.value, activeMaterialName);
  const activeActionLabel = workspaceVerb(workspaceSection);
  const activeWorkspaceLabel =
    WORKSPACE_SECTIONS.find((section) => section.value === workspaceSection)?.label ?? "Auto";
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

  async function executeQuery(submittedQuery: string, modeOverride?: StudyMode) {
    if (!submittedQuery || !sessionId.trim() || busy !== "") return;
    const effectiveMode = modeOverride ?? defaultModeForWorkspace(workspaceSection);
    const effectiveSection = workspaceSectionForMode(effectiveMode);
    const examModes = ["exam_answer", "revision_notes", "important_questions", "compare_concepts", "study_guide"];
    if (effectiveSection !== workspaceSection) setWorkspaceSection(effectiveSection);
    if (effectiveMode !== studyMode) setStudyMode(effectiveMode);
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
      const shouldRequestDebug = true;
      const response = await runQuery({
        session_id: sessionId.trim(),
        query: submittedQuery,
        document_id: scopedDocumentId,
        mode: effectiveMode,
        retrieval_mode: retrievalMode,
        retrieval_profile: retrievalProfile,
        exam_profile:
          examModes.includes(effectiveMode)
            ? {
                marks: examMarks,
                answer_style: examAnswerStyle,
                content_type: examContentType,
                instructions: examInstructions.trim() || undefined,
              }
            : undefined,
        debug: shouldRequestDebug,
      });
      setQueryResult(response);
      setQueryHistory((current) =>
        [
          ...current,
          {
            session_id: response.session_id,
            query: submittedQuery,
            mode: effectiveMode,
            profile: retrievalProfile,
            ...sourceSnapshot,
            response,
            timestamp: new Date().toISOString(),
          },
        ].slice(-12),
      );
      setQuery("");
      setComposerCollapsed(true);
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

  async function onRateAnswer(run: ChatRun, runKey: string, rating: AnswerFeedbackRating) {
    if (busy !== "" || savedFeedback[runKey]) return;
    setBusy("feedback");
    setError("");
    try {
      await saveAnswerFeedback(run.session_id, {
        rating,
        query: run.query,
        answer: run.response.answer,
        document_id: run.document_id,
        source_title: run.source_title,
        reason: rating === "good" ? "helpful_answer" : "needs_accuracy_or_clarity_review",
      });
      setSavedFeedback((current) => ({ ...current, [runKey]: rating }));
      setError(
        rating === "good"
          ? "Saved as a strong local answer example."
          : "Saved as a local review case for retrieval and answer-quality tuning.",
      );
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy("");
    }
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
      setSavedFeedback({});
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

  function workspaceSectionForMode(mode: StudyMode): WorkspaceSection {
    if (mode === "general_chat") return "general";
    if (mode === "research_paper") return "paper";
    if (["exam_answer", "revision_notes", "important_questions", "compare_concepts", "study_guide"].includes(mode)) {
      return "exam";
    }
    return "research";
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
    setComposerCollapsed(false);
    setQuery(value);
    window.requestAnimationFrame(() => queryInputRef.current?.focus());
  }

  function applyEmptyStateSuggestion(section: WorkspaceSection, mode: StudyMode, value: string) {
    selectWorkspaceSection(section);
    setStudyMode(mode);
    applySuggestion(value);
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
            {displayName}&apos;s private workspace for asking documents clear questions and checking sources only when needed.
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

        <details className="rail-section golden-demo-card compact-rail-details">
          <summary className="rail-toggle-summary">
            Golden Demo
            <span>offline proof</span>
          </summary>
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
        </details>

        <details className="rail-section compact-rail-details">
          <summary className="rail-toggle-summary">
            Recent threads
            <span>{queryHistory.length}</span>
          </summary>
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
        </details>

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
                  <span className="tiny">Stored locally. Full path hidden.</span>
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
        <ThreadHeader
          activeMaterialName={activeMaterialName}
          activeWorkspaceLabel={activeWorkspaceLabel}
          hasSelectedDocument={Boolean(selectedDocument)}
          onToggleInspector={() => setShowInspector((current) => !current)}
          onToggleLibrary={() => setShowLibrary((current) => !current)}
          showInspector={showInspector}
          showLibrary={showLibrary}
        />

        <div className="thread-scroll">
          {queryHistory.length ? (
            <div className="turn-list">
              {queryHistory.map((run, index) => {
                const runKey = run.timestamp;
                const feedbackRating = savedFeedback[runKey];
                return (
                <article className="turn" key={runKey}>
                  <div className="bubble user">
                    <div className="message-meta">
                      <span className="tiny">You</span>
                    </div>
                    <div className="answer">{run.query}</div>
                  </div>
                  <div className="bubble assistant">
                    <div className="message-meta">
                      <span className="tiny">NIRMIQ / {formatDate(run.timestamp)}</span>
                      {getVerificationBadge(run.response) ? (
                        <span className={cx("trust-badge", getVerificationBadge(run.response)?.className)}>
                          {getVerificationBadge(run.response)?.label}
                        </span>
                      ) : null}
                    </div>
                    {run.mode === "study_guide" ? (
                      <StudyGuideAnswer answer={run.response.answer} />
                    ) : (
                      <AnswerBody answer={run.response.answer} />
                    )}
                    <div className="trust-line">
                      <span className={cx("trust-copy", run.response.grounded ? "sage" : "copper")}>
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
                        Open Sources
                      </button>
                    </div>
                    <div className="feedback-row" aria-label="Answer feedback">
                      <span>{feedbackRating ? "Saved for local quality review" : "Was this useful?"}</span>
                      <button
                        className={cx("feedback-button", feedbackRating === "good" && "active")}
                        disabled={busy !== "" || Boolean(feedbackRating)}
                        onClick={() => onRateAnswer(run, runKey, "good")}
                        type="button"
                      >
                        Good
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
                    {run.response.citations.length ? (
                      <details className="source-drawer">
                        <summary>
                          Sources used
                          <span>{run.response.citations.length}</span>
                        </summary>
                        <div className="citation-row evidence-trail">
                          {run.response.citations.slice(0, 6).map((citation, citationIndex) => (
                            <button
                              className={cx("citation-chip", citation.chunk_id === selectedChunkId && "active")}
                              key={`${run.timestamp}-${citation.chunk_id}-${citationIndex}`}
                              onClick={() => selectCitation(citation.document_id, citation.chunk_id)}
                              type="button"
                            >
                              [{citationIndex + 1}]
                              {citation.page_start ? ` page ${citation.page_start}` : ""}
                            </button>
                          ))}
                        </div>
                      </details>
                    ) : null}
                  </div>
                </article>
                );
              })}
              <div ref={chatEndRef} />
            </div>
          ) : (
            <ChatEmptyState
              busy={busy}
              onLoadGoldenDemo={onLoadGoldenDemo}
              onSuggestion={applyEmptyStateSuggestion}
            />
          )}
        </div>

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
              <div className="source-status">
                <span className={cx("source-dot", selectedDocument && "ok")} />
                <div>
                  <span className="source-label">Using</span>
                  <strong>{selectedDocument ? activeMaterialName : "No material attached"}</strong>
                </div>
              </div>
              <div className="source-actions">
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
                  onClick={() => setShowLibrary((current) => !current)}
                  type="button"
                >
                  Library
                </button>
              </div>
            </div>
            {composerCollapsed ? (
              <div className="composer-minimized">
                Composer minimized.
                <button className="clear-link" onClick={() => setComposerCollapsed(false)} type="button">
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
                        onClick={() => selectWorkspaceSection(section.value)}
                        type="button"
                        title={section.hint}
                      >
                        {section.label}
                      </button>
                    ))}
                  </div>
                  <div className="source-actions expanded">
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
                      Summarize
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
                      onClick={() => {
                        setShowInspector(true);
                        setDeepView("evidence");
                      }}
                      type="button"
                    >
                      Sources
                    </button>
                    <button
                      className="quick-action ghost"
                      onClick={() => setComposerCollapsed(true)}
                      type="button"
                    >
                      Minimize
                    </button>
                    <button className="quick-action ghost" type="button" onClick={clearThread}>
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
                  <p className="composer-hint">
                    {latestCitations.length
                      ? `${latestCitations.length} evidence links ready. Open Sources to inspect citations.`
                      : "Answers stay grounded in the selected study material when evidence is available."}
                  </p>
                </details>
              </>
            )}
          </div>
        </form>
      </section>

      <aside className="deep-rail">
        <div className="deep-panel-head">
          <div>
            <p className="eyebrow">Sources</p>
            <h2>Check the answer</h2>
          </div>
          <button className="button ghost" type="button" onClick={() => setShowInspector(false)}>
            Close
          </button>
        </div>
        <section className="grounding-meter">
          <div className="section-head">
            <div>
              <p className="eyebrow">Answer Support</p>
              <h2>{groundingLabel}</h2>
            </div>
            <span className={cx("chip", queryResult?.grounded ? "sage" : "copper")}>
              {queryResult?.grounded ? "sources found" : "needs context"}
            </span>
          </div>
          <p className="copy">
            {queryResult ? getTrustCopy(queryResult) : "Ask a question to see the sources used for the answer."}
          </p>
        </section>

        <div className="tab-row">
          {(["evidence", "context", "compare"] as DeepView[]).map((view) => (
            <button
              className={cx("tab", deepView === view && "active")}
              key={view}
              onClick={() => setDeepView(view)}
              type="button"
            >
              {view === "evidence" ? "Sources" : view === "context" ? "Source Text" : "Compare"}
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
                    <p className="tiny">Extracted from the selected document.</p>
                    {asset.caption ? <p className="chunk-text">{asset.caption}</p> : null}
                  </div>
                ))}
              </div>
            </div>
          </section>
        ) : null}

        {deepView === "evidence" ? (
          <SourceEvidencePanel
            busy={busy}
            citedChunkIds={citedChunkIds}
            documentId={documentId}
            hasSelectedDocument={Boolean(selectedDocument)}
            latestCitations={latestCitations}
            onRefreshStatus={onRefreshStatus}
            onSelectChunk={setSelectedChunkId}
            onSelectCitation={selectCitation}
            selectedChunk={selectedChunk}
            selectedChunkId={selectedChunkId}
            selectedTitle={selectedDocumentDetail?.title || selectedDocument?.title || "No material selected"}
            visibleChunks={visibleChunks}
          />
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
              <p className="copy">Compare the last two answers when you want to see what changed.</p>
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

      </aside>

      {error ? (
        <div className="toast" role="alert">
          {error}
        </div>
      ) : null}
    </main>
  );
}


