import json
import re
from uuid import uuid4

from app.api.schemas.common import Citation
from app.adapters.storage.sqlite_repo import SQLiteRepo
from app.api.schemas.query import QueryRequest, QueryResponse
from app.domain.citations import to_citations
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.paper_lab import build_paper_lab_artifact
from app.domain.query_intent import QueryIntent, detect_query_intent
from app.services.memory_service import MemoryService
from app.services.retrieval_service import RetrievalService
from app.services.synthesis_service import SynthesisService


class QueryService:
    def __init__(
        self,
        memory_service: MemoryService,
        retrieval_service: RetrievalService,
        synthesis_service: SynthesisService,
        sqlite_repo: SQLiteRepo,
    ) -> None:
        self._memory_service = memory_service
        self._retrieval_service = retrieval_service
        self._synthesis_service = synthesis_service
        self._sqlite_repo = sqlite_repo

    async def run(self, payload: QueryRequest) -> QueryResponse:
        return await self._execute(payload=payload, persist=True)

    async def preview(self, payload: QueryRequest) -> QueryResponse:
        return await self._execute(payload=payload, persist=False)

    async def _execute(self, payload: QueryRequest, persist: bool) -> QueryResponse:
        _ = await self._memory_service.get_summary(payload.session_id)
        intent = detect_query_intent(payload.query, payload.mode)
        response_mode = self._resolve_response_mode(payload.mode, intent)
        retrieval_mode = self._resolve_retrieval_mode(payload.mode, payload.retrieval_mode)
        retrieval_profile = self._resolve_retrieval_profile(payload.retrieval_profile, intent)
        cached_response = self._cached_summary_response(
            payload=payload,
            intent=intent,
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
        )
        if cached_response:
            if persist:
                self._persist_turn(
                    session_id=payload.session_id,
                    query=payload.query,
                    answer=cached_response.answer,
                    citations=cached_response.citations,
                    retrieval_meta=cached_response.retrieval_meta or {},
                )
                await self._memory_service.maybe_refresh_snapshot(payload.session_id)
            if not payload.debug:
                cached_response.retrieval_meta = None
            return cached_response

        exam_context = self._build_exam_context(payload, intent)
        retrieval_query = self._retrieval_query(payload.query, response_mode, exam_context, intent)
        bundle = await self._retrieval_service.retrieve_with_mode(
            retrieval_query,
            mode=retrieval_mode,
            document_id=payload.document_id,
            profile=retrieval_profile,
        )
        bundle = self._augment_selected_summary_bundle(payload=payload, intent=intent, bundle=bundle)
        bundle = self._augment_selected_factual_bundle(payload=payload, intent=intent, bundle=bundle)
        answer, grounded, synthesis_meta = await self._synthesis_service.synthesize(
            payload.query,
            bundle,
            response_mode=response_mode,
            exam_profile=payload.exam_profile.model_dump() if payload.exam_profile else None,
            exam_context=exam_context,
        )
        citations = self._citations_from_synthesis_context(bundle, synthesis_meta, grounded)
        combined_meta = {
            **bundle.meta,
            **synthesis_meta,
            "requested_retrieval_mode": retrieval_mode,
            "retrieval_query_expanded": retrieval_query != payload.query,
            "requested_retrieval_profile": payload.retrieval_profile,
            "effective_retrieval_profile": retrieval_profile,
            "requested_response_mode": payload.mode,
            "response_mode": response_mode,
            "cache_hit": False,
            "detected_intent": intent.intent,
            "intent_confidence": intent.confidence,
            "intent_route": intent.route,
            "exam_profile": payload.exam_profile.model_dump() if payload.exam_profile else None,
            "exam_context": {
                "question_count": len(exam_context.get("questions", [])),
                "diagram_count": len(exam_context.get("diagrams", [])),
            },
        }
        if intent.intent == "paper_draft":
            combined_meta["paper_lab"] = build_paper_lab_artifact(bundle.chunks)
        self._store_summary_if_applicable(
            payload=payload,
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
            intent=intent,
            answer=answer,
            citations=citations,
            retrieval_meta=combined_meta,
        )

        if persist:
            self._persist_turn(
                session_id=payload.session_id,
                query=payload.query,
                answer=answer,
                citations=citations,
                retrieval_meta=combined_meta,
            )
            await self._memory_service.maybe_refresh_snapshot(payload.session_id)

        return QueryResponse(
            session_id=payload.session_id,
            answer=answer,
            citations=citations,
            grounded=grounded,
            retrieval_meta=combined_meta if payload.debug else None,
        )

    def _cached_summary_response(
        self,
        *,
        payload: QueryRequest,
        intent: QueryIntent,
        retrieval_mode: str,
        retrieval_profile: str,
    ) -> QueryResponse | None:
        if not self._can_use_summary_cache(payload, intent):
            return None
        document = self._sqlite_repo.get_document_by_id(str(payload.document_id))
        if not document:
            return None
        summary_profile = self._summary_profile(
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
        )
        cached = self._sqlite_repo.get_document_summary(
            document_id=str(payload.document_id),
            content_hash=str(document["content_hash"]),
            summary_profile=summary_profile,
        )
        if not cached:
            return None
        citations = [
            Citation.model_validate(item)
            for item in json.loads(str(cached["citations_json"]) or "[]")
        ]
        retrieval_meta = json.loads(str(cached["retrieval_meta_json"]) or "{}")
        retrieval_meta.update(
            {
                "cache_hit": True,
                "detected_intent": intent.intent,
                "intent_confidence": intent.confidence,
                "intent_route": "summary_cache_hit",
                "requested_retrieval_mode": retrieval_mode,
                "requested_retrieval_profile": payload.retrieval_profile,
                "effective_retrieval_profile": retrieval_profile,
                "summary_profile": summary_profile,
            }
        )
        return QueryResponse(
            session_id=payload.session_id,
            answer=str(cached["answer"]),
            citations=citations,
            grounded=True,
            retrieval_meta=retrieval_meta,
        )

    def _store_summary_if_applicable(
        self,
        *,
        payload: QueryRequest,
        retrieval_mode: str,
        retrieval_profile: str,
        intent: QueryIntent,
        answer: str,
        citations: list[Citation],
        retrieval_meta: dict[str, object],
    ) -> None:
        if not self._can_use_summary_cache(payload, intent):
            return
        document = self._sqlite_repo.get_document_by_id(str(payload.document_id))
        if not document:
            return
        summary_profile = self._summary_profile(
            retrieval_mode=retrieval_mode,
            retrieval_profile=retrieval_profile,
        )
        cache_meta = {**retrieval_meta, "summary_profile": summary_profile}
        self._sqlite_repo.upsert_document_summary(
            summary_id=str(uuid4()),
            document_id=str(payload.document_id),
            content_hash=str(document["content_hash"]),
            summary_profile=summary_profile,
            answer=answer,
            citations_json=json.dumps([citation.model_dump() for citation in citations]),
            retrieval_meta_json=json.dumps(cache_meta),
        )

    def _persist_turn(
        self,
        *,
        session_id: str,
        query: str,
        answer: str,
        citations: list[Citation],
        retrieval_meta: dict[str, object],
    ) -> None:
        self._sqlite_repo.ensure_session(session_id)
        self._sqlite_repo.insert_message(str(uuid4()), session_id, "user", query)
        self._sqlite_repo.insert_message(
            str(uuid4()),
            session_id,
            "assistant",
            answer,
            citations_json=json.dumps([citation.model_dump() for citation in citations]),
            retrieval_meta_json=json.dumps(retrieval_meta),
        )

    @staticmethod
    def _can_use_summary_cache(payload: QueryRequest, intent: QueryIntent) -> bool:
        return bool(payload.document_id and intent.intent == "summary")

    @staticmethod
    def _summary_profile(*, retrieval_mode: str, retrieval_profile: str) -> str:
        return f"{retrieval_mode}:{retrieval_profile}:v5"

    @staticmethod
    def _citations_from_synthesis_context(
        bundle: RetrievalBundle,
        synthesis_meta: dict[str, object],
        grounded: bool,
    ) -> list[Citation]:
        if not grounded:
            return []
        raw_chunk_ids = synthesis_meta.get("cited_context_chunk_ids")
        if not isinstance(raw_chunk_ids, list) or not raw_chunk_ids:
            return []

        cited_chunk_ids: list[str] = []
        seen: set[str] = set()
        for raw_chunk_id in raw_chunk_ids:
            chunk_id = str(raw_chunk_id)
            if not chunk_id or chunk_id in seen:
                continue
            cited_chunk_ids.append(chunk_id)
            seen.add(chunk_id)

        chunks_by_id = {chunk.chunk_id: chunk for chunk in bundle.chunks}
        cited_chunks = [
            chunks_by_id[chunk_id]
            for chunk_id in cited_chunk_ids
            if chunk_id in chunks_by_id
        ]
        return to_citations(cited_chunks)

    def _build_exam_context(self, payload: QueryRequest, intent: QueryIntent) -> dict[str, object]:
        if not payload.document_id or not self._uses_exam_context(payload.mode, intent):
            return {"questions": [], "diagrams": []}
        questions = self._sqlite_repo.list_question_bank_items(payload.document_id)[:12]
        diagrams = self._sqlite_repo.list_diagram_assets(payload.document_id)[:8]
        return {
            "questions": [
                {
                    "question": str(row["question"]),
                    "marks": row.get("marks"),
                    "source_label": row.get("source_label"),
                }
                for row in questions
            ],
            "diagrams": [
                {
                    "page_number": row.get("page_number"),
                    "image_path": str(row["image_path"]),
                    "caption": row.get("caption"),
                    "width": row.get("width"),
                    "height": row.get("height"),
                }
                for row in diagrams
            ],
        }

    @staticmethod
    def _retrieval_query(
        query: str,
        mode: str,
        exam_context: dict[str, object],
        intent: QueryIntent,
    ) -> str:
        normalized_query = query.strip().lower()
        if intent.intent == "summary" or (
            any(term in normalized_query for term in ("summarize", "summary", "overview"))
            and any(term in normalized_query for term in ("pdf", "document", "paper", "material", "file", "textbook"))
        ):
            return (
                f"{query}\n\n"
                "Document overview retrieval hints: abstract introduction conclusion summary methodology "
                "architecture approach contribution results limitations key points."
            )
        if intent.intent == "compare":
            return f"{query}\n\nComparison retrieval hints: differences similarities contrast tradeoffs advantages limitations."
        if intent.intent == "paper_draft":
            return f"{query}\n\nPaper drafting retrieval hints: related work methodology results limitations future work citations."
        if intent.intent == "deep_research":
            return f"{query}\n\nDeep research retrieval hints: mechanism evidence caveats architecture results limitations implications."
        if intent.intent == "factual_lookup":
            hints = QueryService._focused_retrieval_hints(query)
            if hints:
                return f"{query}\n\nFocused retrieval hints: {hints}"
            return (
                f"{query}\n\n"
                "Focused retrieval hints: definition explanation examples types steps advantages limitations key points."
            )
        if mode.strip().lower() not in {"study_guide", "important_questions"}:
            return query
        questions = exam_context.get("questions", [])
        if not isinstance(questions, list) or not questions:
            return query
        question_text = " ".join(
            str(item.get("question", ""))
            for item in questions[:8]
            if isinstance(item, dict) and item.get("question")
        )
        if not question_text:
            return query
        return f"{query}\n\nImported questions:\n{question_text}"

    @staticmethod
    def _resolve_retrieval_mode(mode: str, retrieval_mode: str) -> str:
        direct_mode = retrieval_mode.strip().lower()
        if direct_mode in {"hybrid", "bm25", "vector"}:
            return direct_mode
        legacy_mode = mode.strip().lower()
        if legacy_mode in {"hybrid", "bm25", "vector"}:
            return legacy_mode
        return "hybrid"

    @staticmethod
    def _resolve_retrieval_profile(requested_profile: str, intent: QueryIntent) -> str:
        normalized = requested_profile.strip().lower()
        if normalized not in {"fast", "balanced", "precision"}:
            normalized = "balanced"
        if normalized != "balanced":
            return normalized
        if intent.intent in {"paper_draft", "deep_research", "exam", "compare"}:
            return "precision"
        return normalized

    @staticmethod
    def _resolve_response_mode(requested_mode: str, intent: QueryIntent) -> str:
        normalized = requested_mode.strip().lower()
        if intent.intent == "summary":
            return "summary"
        if intent.intent == "compare":
            return "compare_concepts"
        if intent.intent == "paper_draft":
            return "research_paper"
        if intent.intent == "deep_research":
            return "deep_research"
        if intent.intent == "exam":
            return normalized if normalized in QueryService._exam_modes() else "exam_answer"
        if intent.intent == "general_chat":
            return "general_chat"
        if normalized == "summary":
            return "research"
        return normalized if normalized else "research"

    @staticmethod
    def _exam_modes() -> set[str]:
        return {
            "exam_answer",
            "revision_notes",
            "important_questions",
            "compare_concepts",
            "study_guide",
        }

    @staticmethod
    def _uses_exam_context(mode: str, intent: QueryIntent) -> bool:
        return intent.intent == "exam" or mode.strip().lower() in {
            "exam_answer",
            "revision_notes",
            "important_questions",
            "study_guide",
        }

    def _augment_selected_summary_bundle(
        self,
        *,
        payload: QueryRequest,
        intent: QueryIntent,
        bundle: RetrievalBundle,
    ) -> RetrievalBundle:
        if not payload.document_id or intent.intent != "summary":
            return bundle
        rows = self._sqlite_repo.get_document_chunks(str(payload.document_id), active_only=True)
        if not rows:
            return bundle

        existing_ids = {chunk.chunk_id for chunk in bundle.chunks}
        seed_rows = sorted(
            rows[:120],
            key=lambda row: self._summary_seed_score(row),
            reverse=True,
        )[:6]
        seed_chunks: list[RetrievedChunk] = []
        for rank, row in enumerate(seed_rows):
            chunk_id = str(row["id"])
            if chunk_id in existing_ids:
                continue
            seed_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(row["document_id"]),
                    text=str(row["text"]),
                    score=max(0.01, 0.12 - (rank * 0.005)),
                    page_start=row.get("page_start"),
                    page_end=row.get("page_end"),
                    source="summary_seed",
                    quality_score=float(row.get("quality_score") or 1.0),
                    section_id=row.get("section_id"),
                    heading=row.get("heading"),
                    section_path=row.get("section_path"),
                    chunk_type=str(row.get("chunk_type") or "body"),
                )
            )
            existing_ids.add(chunk_id)

        if not seed_chunks:
            return bundle
        return RetrievalBundle(
            chunks=[*seed_chunks, *bundle.chunks],
            meta={
                **bundle.meta,
                "summary_seed_chunks": len(seed_chunks),
                "summary_seed_strategy": "early_outline_chunks",
            },
        )

    @staticmethod
    def _summary_seed_score(row: dict[str, object]) -> float:
        text = str(row.get("text") or "").lower()
        page = int(row.get("page_start") or 9999)
        quality = float(row.get("quality_score") or 1.0)
        positive_terms = {
            "this book",
            "chapter",
            "part i",
            "part ii",
            "fundamentals",
            "covers",
            "overview",
            "introduction",
            "machine learning",
            "deep learning",
            "training",
            "model",
            "algorithm",
            "project",
            "data",
            "classification",
            "regression",
        }
        negative_terms = {
            "other resources",
            "bibliography",
            "references",
            "index",
            "copyright",
            "trademark",
            "isbn",
        }
        score = quality * 2.0
        score += max(0.0, 3.0 - (page / 18.0))
        score += sum(0.7 for term in positive_terms if term in text)
        score -= sum(1.2 for term in negative_terms if term in text)
        if 80 <= len(text.split()) <= 220:
            score += 0.5
        return score

    def _augment_selected_factual_bundle(
        self,
        *,
        payload: QueryRequest,
        intent: QueryIntent,
        bundle: RetrievalBundle,
    ) -> RetrievalBundle:
        if not payload.document_id or intent.intent not in {"factual_lookup", "deep_research", "exam"}:
            return bundle
        focus_terms = self._query_focus_terms(payload.query)
        if not focus_terms:
            return bundle
        rows = self._sqlite_repo.get_document_chunks(str(payload.document_id), active_only=True)
        if not rows:
            return bundle

        scored_rows = [
            (self._factual_seed_score(row, payload.query, focus_terms), row)
            for row in rows
        ]
        seed_rows = [row for score, row in sorted(scored_rows, key=lambda item: item[0], reverse=True) if score > 0][:5]
        existing_chunks = {chunk.chunk_id: chunk for chunk in bundle.chunks}
        promoted_ids: set[str] = set()
        seed_chunks: list[RetrievedChunk] = []
        for rank, row in enumerate(seed_rows):
            chunk_id = str(row["id"])
            if chunk_id in promoted_ids:
                continue
            if chunk_id in existing_chunks:
                seed_chunks.append(existing_chunks[chunk_id])
            else:
                seed_chunks.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        document_id=str(row["document_id"]),
                        text=str(row["text"]),
                        score=max(0.01, 0.12 - (rank * 0.005)),
                        page_start=row.get("page_start"),
                        page_end=row.get("page_end"),
                        source="focused_seed",
                        quality_score=float(row.get("quality_score") or 1.0),
                        section_id=row.get("section_id"),
                        heading=row.get("heading"),
                        section_path=row.get("section_path"),
                        chunk_type=str(row.get("chunk_type") or "body"),
                    )
                )
            promoted_ids.add(chunk_id)
        if not seed_chunks:
            return bundle
        remaining_chunks = [
            chunk for chunk in bundle.chunks if chunk.chunk_id not in promoted_ids
        ]
        return RetrievalBundle(
            chunks=[*seed_chunks, *remaining_chunks],
            meta={
                **bundle.meta,
                "focused_seed_chunks": len(seed_chunks),
                "focused_seed_strategy": "definition_priority_terms",
            },
        )

    @staticmethod
    def _query_focus_terms(query: str) -> set[str]:
        stopwords = {
            "about",
            "answer",
            "briefly",
            "could",
            "does",
            "explain",
            "from",
            "give",
            "into",
            "this",
            "that",
            "what",
            "when",
            "where",
            "which",
            "with",
            "reduced",
        }
        terms: set[str] = set()
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", query.lower()):
            if token in stopwords:
                continue
            terms.add(token)
            stem = QueryService._light_stem(token)
            if stem != token:
                terms.add(stem)
        if "unsupervised" in terms and ("algorithm" in terms or "algorithms" in terms):
            terms.update(
                {
                    "clustering",
                    "cluster",
                    "density",
                    "anomaly",
                    "detection",
                    "dimensionality",
                    "reduction",
                    "pca",
                    "k-means",
                    "dbscan",
                }
            )
        return terms

    @staticmethod
    def _focused_retrieval_hints(query: str) -> str:
        normalized = query.lower()
        tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", normalized))
        hints = ["definition", "explanation", "examples", "types", "key points"]
        if {"algorithm", "algorithms"} & tokens:
            hints.extend(["algorithm", "method", "procedure", "training", "model"])
        if "unsupervised" in tokens:
            hints.extend(
                [
                    "unsupervised learning",
                    "clustering",
                    "k-means",
                    "dbscan",
                    "hierarchical clustering",
                    "density estimation",
                    "anomaly detection",
                    "dimensionality reduction",
                    "pca",
                ]
            )
        if {"supervised", "classification", "regression"} & tokens:
            hints.extend(["classification", "regression", "labels", "training examples", "prediction"])
        if {"limitation", "limitations", "caveat", "caveats"} & tokens:
            hints.extend(["limitations", "assumptions", "tradeoffs", "failure cases"])
        deduped: list[str] = []
        seen: set[str] = set()
        for hint in hints:
            if hint not in seen:
                deduped.append(hint)
                seen.add(hint)
        return " ".join(deduped)

    @staticmethod
    def _factual_seed_score(row: dict[str, object], query: str, focus_terms: set[str]) -> float:
        text = str(row.get("text") or "").lower()
        if not text:
            return 0.0
        text_terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", text))
        text_terms.update(QueryService._light_stem(term) for term in list(text_terms))
        overlap = focus_terms.intersection(text_terms)
        if not overlap:
            return 0.0

        normalized_query = query.lower()
        quality = float(row.get("quality_score") or 1.0)
        score = quality + (len(overlap) * 1.4)
        if any(phrase in normalized_query for phrase in ("what is", "define", "meaning")):
            definition_cues = {
                " is a ",
                " is an ",
                "means",
                "called",
                "occurs",
                "refers",
                "assumes",
                "generalize",
                "probabilistic model",
                "generative model",
                "generated from",
                "parameters are unknown",
                "training data",
                "new instances",
                "new data",
            }
            score += sum(0.9 for cue in definition_cues if cue in text)
            metadata = " ".join(
                str(row.get(key) or "").lower()
                for key in ("heading", "section_path", "chunk_type")
            )
            if any(term in normalized_query for term in ("gaussian mixture", "gmm")):
                if re.search(r"\bgaussian mixtures?\b", metadata):
                    score += 2.4
                if "probabilistic model" in text or "generated from a mixture" in text:
                    score += 2.0
                if "bayesian" in metadata and "bayesian" not in normalized_query:
                    score -= 1.2
        if any(term in normalized_query for term in ("reduce", "reduced", "prevent", "avoid", "fix")):
            solution_cues = {
                "possible solutions",
                "simplify",
                "fewer parameters",
                "reduce",
                "regularization",
                "constrain",
                "training data",
                "noise",
                "outliers",
                "early stopping",
            }
            score += sum(0.8 for cue in solution_cues if cue in text)
        metadata = " ".join(
            str(row.get(key) or "").lower()
            for key in ("heading", "section_path", "chunk_type")
        )
        if (
            any(marker in metadata for marker in ("references", "bibliography", "index"))
            or RetrievalService._looks_like_index_chunk(text)
        ):
            score -= 3.0
        return score

    @staticmethod
    def _light_stem(token: str) -> str:
        if len(token) > 5 and token.endswith("ing"):
            stem = token[:-3]
            if len(stem) > 3 and stem[-1] == stem[-2]:
                stem = stem[:-1]
            return stem
        if len(token) > 4 and token.endswith("ed"):
            return token[:-1] if token.endswith("eed") else token[:-2]
        if len(token) > 4 and token.endswith("e"):
            return token[:-1]
        if len(token) > 4 and token.endswith("s"):
            return token[:-1]
        return token
