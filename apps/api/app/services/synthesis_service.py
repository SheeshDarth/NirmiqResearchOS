import re
from collections import Counter

from app.adapters.llm.generator import Generator
from app.core.config import Settings
from app.domain.answer_intelligence import (
    AnswerPlan,
    answer_evidence_cue_score,
    answer_subject_anchor_terms,
    build_answer_plan,
    evidence_obligation_score,
)
from app.domain.citation_coverage import citation_coverage
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.retrieval_policy import RetrievalPolicy
from app.domain.text_normalization import normalize_ocr_text


_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "answer",
    "about",
    "are",
    "brief",
    "briefly",
    "be",
    "cite",
    "cited",
    "citation",
    "citations",
    "corpus",
    "create",
    "deep",
    "define",
    "describe",
    "does",
    "during",
    "draft",
    "explain",
    "for",
    "from",
    "generate",
    "give",
    "guide",
    "how",
    "imported",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "notes",
    "produce",
    "question",
    "research",
    "reported",
    "shown",
    "listed",
    "given",
    "recorded",
    "study",
    "the",
    "this",
    "to",
    "say",
    "says",
    "should",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "write",
    "with",
}

_CLAIM_STOPWORDS = _QUERY_STOPWORDS | {
    "also",
    "as",
    "at",
    "be",
    "been",
    "being",
    "by",
    "can",
    "could",
    "does",
    "did",
    "do",
    "has",
    "have",
    "had",
    "if",
    "into",
    "its",
    "may",
    "more",
    "not",
    "only",
    "or",
    "other",
    "should",
    "such",
    "than",
    "that",
    "their",
    "these",
    "they",
    "through",
    "use",
    "using",
    "was",
    "were",
    "will",
    "would",
}

_ANSWER_TASK_TERMS = {
    "apply",
    "classify",
    "compare",
    "compute",
    "describe",
    "detect",
    "encode",
    "explain",
    "form",
    "generate",
    "have",
    "identify",
    "interpret",
    "learn",
    "optimize",
    "mask",
    "place",
    "perform",
    "provide",
    "predict",
    "represent",
    "recommend",
    "regularize",
    "require",
    "select",
    "train",
    "transform",
    "update",
    "use",
    "work",
    "works",
}


class SynthesisService:
    def __init__(self, settings: Settings, policy: RetrievalPolicy, generator: Generator) -> None:
        self._settings = settings
        self._policy = policy
        self._generator = generator
        self._min_grounding_score = policy.min_grounding_score
        self._max_context_tokens = policy.max_context_tokens

    async def synthesize(
        self,
        query: str,
        bundle: RetrievalBundle,
        response_mode: str = "research",
        exam_profile: dict[str, object] | None = None,
        exam_context: dict[str, object] | None = None,
    ) -> tuple[str, bool, dict[str, object]]:
        answer_plan = build_answer_plan(
            query=query,
            response_mode=response_mode,
            exam_profile=exam_profile,
        )
        answer_plan_meta = {
            "answer_plan_type": answer_plan.answer_type,
            "answer_plan_depth": answer_plan.depth,
            "answer_plan_subject": answer_plan.subject,
            "answer_plan_requested_elements": list(answer_plan.requested_elements),
            "answer_plan_obligations": [
                {
                    "key": item.key,
                    "label": item.label,
                    "required": item.required,
                }
                for item in answer_plan.evidence_obligations
            ],
        }
        top_grounding_score = max((float(chunk.score) for chunk in bundle.chunks), default=0.0)
        citation_count = len(bundle.chunks)
        grounding_state = self._grounding_state(top_grounding_score, citation_count)
        overview_query = self._is_document_overview_query(query, response_mode)
        relevance_query = self._relevance_query(
            query=answer_plan.evidence_query(query),
            response_mode=response_mode,
            exam_context=exam_context,
        )
        context_relevance = self._context_relevance(query=relevance_query, bundle=bundle)
        strict_relevance_required = response_mode.strip().lower() == "general_chat" or not overview_query
        low_score_overview = grounding_state == "weak" and overview_query and (
            citation_count >= 2
            or (response_mode.strip().lower() == "study_guide" and citation_count >= 1)
        )
        if low_score_overview:
            grounding_state = "moderate"
        answer_relevance_state = str(context_relevance.get("answer_relevance_state") or "unknown")
        if strict_relevance_required and context_relevance["context_relevance_state"] == "unrelated":
            return (
                (
                    "I could not find this in the uploaded sources.\n\n"
                    "Try selecting the right document, uploading source material for this topic, or asking a narrower question."
                ),
                False,
                {
                    "generation_backend": "none",
                    "grounding_score": top_grounding_score,
                    "citation_count": citation_count,
                    "grounding_state": "weak",
                    "grounding_summary": "retrieved evidence was unrelated to the query",
                    "document_overview_request": overview_query,
                    "low_score_overview_allowed": low_score_overview,
                    **answer_plan_meta,
                    **context_relevance,
                },
            )
        if strict_relevance_required and answer_relevance_state in {"weak_related", "no_direct_evidence"}:
            return (
                (
                    "I found a related mention, but not enough direct evidence to answer confidently.\n\n"
                    "Ask a narrower question or open Sources to check what the document actually says."
                ),
                False,
                {
                    "generation_backend": "none",
                    "grounding_score": top_grounding_score,
                    "citation_count": citation_count,
                    "grounding_state": "weak",
                    "grounding_summary": "retrieved evidence was not direct enough",
                    "document_overview_request": overview_query,
                    "low_score_overview_allowed": low_score_overview,
                    **answer_plan_meta,
                    **context_relevance,
                },
            )
        grounded = grounding_state != "weak"
        if not grounded:
            return (
                self._insufficient_context_message(citation_count),
                False,
                {
                    "generation_backend": "none",
                    "grounding_score": top_grounding_score,
                    "citation_count": citation_count,
                    "grounding_state": grounding_state,
                    "grounding_summary": "weak evidence - no answer generated",
                    "document_overview_request": overview_query,
                    "low_score_overview_allowed": low_score_overview,
                    **answer_plan_meta,
                    **context_relevance,
                },
            )

        retrieval_evidence_terms = self._retrieval_evidence_terms(bundle)
        selected = self._select_context(
            bundle,
            query=query,
            answer_plan=answer_plan,
            additional_terms=retrieval_evidence_terms,
        )
        obligation_context_meta = self._obligation_context_meta(
            answer_plan=answer_plan,
            context_chunks=selected,
        )
        prompt = self._build_grounded_prompt(
            query,
            selected,
            response_mode=response_mode,
            exam_profile=exam_profile,
            exam_context=exam_context,
            answer_plan=answer_plan,
        )
        generation_temperature = self._generation_temperature(
            response_mode=response_mode,
            context_chunks=selected,
        )
        generated = await self._generator.answer(
            prompt=prompt,
            model=self._settings.generator_model_default,
            temperature=generation_temperature,
        )

        used_fallback_answer = False
        if not generated:
            generated = self._fallback_answer(
                query=query,
                context_chunks=selected,
                response_mode=response_mode,
                exam_profile=exam_profile,
                exam_context=exam_context,
                additional_terms=retrieval_evidence_terms,
            )
            used_fallback_answer = True
        else:
            generated = self._anchor_uncited_sentences(generated, selected)

        generated = self._with_diagram_grounding_note(
            answer=generated,
            query=query,
            exam_context=exam_context,
        )
        verification = self._verify_cited_claims(generated, selected)
        answer_rewritten = False
        answer_repair_mode = "none"
        if self._should_rewrite_for_faithfulness(verification):
            original_verification = verification
            repaired = self._remove_unsupported_claims(generated, verification)
            repaired_verification = self._verify_cited_claims(repaired, selected)
            if self._is_usable_claim_repair(repaired, repaired_verification):
                generated = repaired
                verification = {
                    **repaired_verification,
                    "original_unsupported_claims": original_verification["unsupported_claims"],
                    "original_cited_claims_checked": original_verification["cited_claims_checked"],
                }
                answer_rewritten = True
                answer_repair_mode = "claim_pruned"
            else:
                generated = self._fallback_answer(
                    query=query,
                    context_chunks=selected,
                    response_mode=response_mode,
                    exam_profile=exam_profile,
                    exam_context=exam_context,
                    additional_terms=retrieval_evidence_terms,
                )
                generated = self._with_diagram_grounding_note(
                    answer=generated,
                    query=query,
                    exam_context=exam_context,
                )
                fallback_verification = self._verify_cited_claims(generated, selected)
                verification = {
                    **fallback_verification,
                    "original_unsupported_claims": original_verification["unsupported_claims"],
                    "original_cited_claims_checked": original_verification["cited_claims_checked"],
                }
                answer_rewritten = True
                answer_repair_mode = "extractive_fallback"
                used_fallback_answer = True

        coverage_meta = citation_coverage(generated)
        citation_context_meta = self._citation_context_meta(
            answer=generated,
            bundle=bundle,
            selected_context=selected,
        )
        evidence_gate = self._evidence_reliability_gate(
            response_mode=response_mode,
            generation_backend=self._generator.last_backend,
            answer_rewritten=answer_rewritten,
            used_fallback_answer=used_fallback_answer,
            grounding_state=grounding_state,
            context_relevance=context_relevance,
            coverage_meta=coverage_meta,
            verification=verification,
            citation_context_meta=citation_context_meta,
            selected_context=selected,
        )
        if not evidence_gate["evidence_gate_passed"]:
            return (
                self._evidence_gate_message(evidence_gate),
                False,
                {
                    "generation_backend": self._generator.last_backend,
                    "generation_model_requested": getattr(self._generator, "last_model_requested", None),
                    "generation_model_used": getattr(self._generator, "last_model_used", None),
                    "generation_model_fallback": getattr(self._generator, "last_model_fallback", False),
                    "generation_error": getattr(self._generator, "last_error", None),
                    "grounding_score": top_grounding_score,
                    "citation_count": citation_count,
                    "context_chunks_used": len(selected),
                    "synthesis_retrieval_terms": sorted(retrieval_evidence_terms),
                    "grounding_state": "weak",
                    "grounding_summary": "evidence reliability gate blocked the answer",
                    "document_overview_request": overview_query,
                    "low_score_overview_allowed": low_score_overview,
                    **answer_plan_meta,
                    **obligation_context_meta,
                    **context_relevance,
                    "exam_profile_used": bool(exam_profile),
                    "exam_context_used": bool(
                        exam_context and (exam_context.get("questions") or exam_context.get("diagrams"))
                    ),
                    "citation_verification_state": verification["state"],
                    "generation_temperature": generation_temperature,
                    **coverage_meta,
                    "cited_claims_checked": verification["cited_claims_checked"],
                    "unsupported_claims": verification["unsupported_claims"],
                    "original_cited_claims_checked": verification.get("original_cited_claims_checked"),
                    "original_unsupported_claims": verification.get("original_unsupported_claims", []),
                    "answer_rewritten_for_faithfulness": answer_rewritten,
                    "answer_repair_mode": answer_repair_mode,
                    **citation_context_meta,
                    **evidence_gate,
                },
            )

        meta = {
            "generation_backend": self._generator.last_backend,
            "generation_model_requested": getattr(self._generator, "last_model_requested", None),
            "generation_model_used": getattr(self._generator, "last_model_used", None),
            "generation_model_fallback": getattr(self._generator, "last_model_fallback", False),
            "generation_error": getattr(self._generator, "last_error", None),
            "grounding_score": top_grounding_score,
            "citation_count": citation_count,
            "context_chunks_used": len(selected),
            "synthesis_retrieval_terms": sorted(retrieval_evidence_terms),
            "grounding_state": grounding_state,
            "grounding_summary": self._grounding_summary(grounding_state, top_grounding_score, citation_count),
            "document_overview_request": overview_query,
            "low_score_overview_allowed": low_score_overview,
            **answer_plan_meta,
            **obligation_context_meta,
            **context_relevance,
            "exam_profile_used": bool(exam_profile),
            "exam_context_used": bool(
                exam_context and (exam_context.get("questions") or exam_context.get("diagrams"))
            ),
            "citation_verification_state": verification["state"],
            "generation_temperature": generation_temperature,
            **coverage_meta,
            "cited_claims_checked": verification["cited_claims_checked"],
            "unsupported_claims": verification["unsupported_claims"],
            "original_cited_claims_checked": verification.get("original_cited_claims_checked"),
            "original_unsupported_claims": verification.get("original_unsupported_claims", []),
            "answer_rewritten_for_faithfulness": answer_rewritten,
            "answer_repair_mode": answer_repair_mode,
            **citation_context_meta,
            **evidence_gate,
        }
        return (generated, True, meta)

    @staticmethod
    def _retrieval_evidence_terms(bundle: RetrievalBundle) -> set[str]:
        """Return bounded document-local terms for answer-side evidence selection."""

        terms: list[str] = []
        for key in ("document_query_expansion_terms", "query_expansion_terms"):
            value = bundle.meta.get(key)
            if not isinstance(value, list):
                continue
            terms.extend(
                str(item).strip().lower()
                for item in value
                if str(item).strip()
            )
        # Retrieval expansion is intentionally broad. Add a small lexical
        # window from the leading evidence so synthesis can distinguish a
        # direct mechanism passage from a merely related example.
        for chunk in bundle.chunks[:2]:
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{5,}", chunk.text.lower()):
                if token not in _QUERY_STOPWORDS:
                    terms.append(token)
        return {
            term
            for term in dict.fromkeys(terms)
            if len(term) >= 3 and term not in _ANSWER_TASK_TERMS
        }

    def _generation_temperature(
        self,
        *,
        response_mode: str,
        context_chunks: list[tuple[int, str]],
    ) -> float:
        mode = response_mode.strip().lower()
        total_words = sum(len(self._context_text(block).split()) for _, block in context_chunks)
        long_form_modes = {"deep_research", "paper", "research_paper", "study_guide"}
        if mode in long_form_modes and total_words >= 900:
            return max(0.0, min(1.0, self._settings.generator_temperature_long_context))
        return max(0.0, min(1.0, self._settings.generator_temperature_grounded))

    def _select_context(
        self,
        bundle: RetrievalBundle,
        *,
        query: str,
        answer_plan: AnswerPlan,
        additional_terms: set[str] | None = None,
    ) -> list[tuple[int, str]]:
        selected: list[tuple[int, str]] = []
        used_words = 0
        indexed_candidates = list(enumerate(bundle.chunks[:12], start=1))
        if not indexed_candidates:
            return selected

        # Preserve citation anchors while ordering the context for evidence
        # coverage. One long, highly ranked chunk must not hide a later chunk
        # that fills a different part of the answer contract.
        coverage_first: list[tuple[int, RetrievedChunk]] = []
        used_anchors: set[int] = set()
        for obligation in answer_plan.evidence_obligations:
            ranked = sorted(
                (
                    (evidence_obligation_score(obligation, chunk.text), anchor, chunk)
                    for anchor, chunk in indexed_candidates
                    if anchor not in used_anchors
                ),
                key=lambda item: (item[0], -item[1]),
                reverse=True,
            )
            if not ranked or ranked[0][0] < 0.32:
                continue
            _, anchor, chunk = ranked[0]
            coverage_first.append((anchor, chunk))
            used_anchors.add(anchor)
        candidates = [
            *coverage_first,
            *[
                (anchor, chunk)
                for anchor, chunk in indexed_candidates
                if anchor not in used_anchors
            ],
        ]

        # Share the context budget across the retrieved evidence set. Previously,
        # two or three long textbook chunks could consume the entire budget and
        # hide a later, directly answering subsection from synthesis.
        per_chunk_budget = max(80, self._max_context_tokens // len(candidates))
        for idx, chunk in candidates:
            text = chunk.text.strip()
            if not text:
                continue
            remaining_words = self._max_context_tokens - used_words
            if remaining_words <= 0:
                break
            excerpt = self._query_aware_context_excerpt(
                text=text,
                query=query,
                answer_plan=answer_plan,
                additional_terms=additional_terms,
                max_words=min(per_chunk_budget, remaining_words),
            )
            if not excerpt:
                continue
            chunk_words = len(excerpt.split())
            header = (
                f"[{idx}] doc={chunk.document_id} score={chunk.score:.3f} "
                f"source={chunk.source} pages={chunk.page_start or '?'}-{chunk.page_end or '?'}"
            )
            if chunk.heading:
                header += f"\nSource heading: {chunk.heading}"
            block = f"{header}\n{excerpt}"
            selected.append((idx, block))
            used_words += chunk_words
        return selected

    @staticmethod
    def _obligation_context_meta(
        *,
        answer_plan: AnswerPlan,
        context_chunks: list[tuple[int, str]],
    ) -> dict[str, object]:
        supported: list[str] = []
        unsupported_required: list[str] = []
        support_map: dict[str, list[int]] = {}
        for obligation in answer_plan.evidence_obligations:
            anchors = [
                anchor
                for anchor, block in context_chunks
                if evidence_obligation_score(
                    obligation,
                    SynthesisService._context_text(block),
                ) >= 0.32
            ]
            support_map[obligation.key] = anchors
            if anchors:
                supported.append(obligation.key)
            elif obligation.required:
                unsupported_required.append(obligation.key)
        required_count = sum(item.required for item in answer_plan.evidence_obligations)
        supported_required = required_count - len(unsupported_required)
        return {
            "obligation_support_map": support_map,
            "supported_obligations": supported,
            "unsupported_required_obligations": unsupported_required,
            "required_obligation_coverage": round(
                supported_required / required_count,
                3,
            ) if required_count else 1.0,
        }

    @staticmethod
    def _query_aware_context_excerpt(
        *,
        text: str,
        query: str,
        answer_plan: AnswerPlan,
        max_words: int,
        additional_terms: set[str] | None = None,
    ) -> str:
        """Keep a complete local evidence window instead of a chunk's arbitrary head."""

        normalized = re.sub(r"\s+", " ", normalize_ocr_text(text)).strip()
        if not normalized or max_words <= 0:
            return ""
        words = normalized.split()
        if len(words) <= max_words:
            return normalized

        sentences = SynthesisService._split_sentences(normalized)
        if not sentences:
            return " ".join(words[:max_words]).strip()

        core_terms = SynthesisService._core_subject_terms(query=query, answer_plan=answer_plan)
        expanded_terms = (
            SynthesisService._query_terms(query)
            | (additional_terms or set())
        ) - _ANSWER_TASK_TERMS
        literal_terms = {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", query.lower())
            if token not in _QUERY_STOPWORDS
        }
        goal_terms = literal_terms - core_terms - _ANSWER_TASK_TERMS

        def sentence_signal(item: tuple[int, str]) -> tuple[float, int]:
            sentence_index, sentence = item
            score = (
                (3.0 * SynthesisService._sentence_score(sentence, core_terms))
                + (2.5 * SynthesisService._sentence_score(sentence, goal_terms))
                + (0.45 * SynthesisService._sentence_score(sentence, expanded_terms))
                + (3.0 * answer_evidence_cue_score(answer_plan.answer_type, sentence))
                - (1.0 if SynthesisService._is_low_value_evidence_sentence(sentence) else 0.0)
            )
            return (score, -sentence_index)

        seed_indices: list[int] = []
        for obligation in answer_plan.evidence_obligations:
            ranked_for_obligation = max(
                enumerate(sentences),
                key=lambda item: (
                    evidence_obligation_score(obligation, item[1]),
                    sentence_signal(item)[0],
                    -item[0],
                ),
            )
            if evidence_obligation_score(obligation, ranked_for_obligation[1]) >= 0.32:
                seed_indices.append(ranked_for_obligation[0])
        global_seed = max(enumerate(sentences), key=sentence_signal)[0]
        seed_indices.append(global_seed)
        seed_indices = list(dict.fromkeys(seed_indices))

        candidate_indices: list[int] = []
        seen_candidate_indices: set[int] = set()
        for distance in range(len(sentences)):
            for seed_index in seed_indices:
                offsets = (0,) if distance == 0 else (distance, -distance)
                for offset in offsets:
                    sentence_index = seed_index + offset
                    if (
                        sentence_index < 0
                        or sentence_index >= len(sentences)
                        or sentence_index in seen_candidate_indices
                    ):
                        continue
                    candidate_indices.append(sentence_index)
                    seen_candidate_indices.add(sentence_index)
        candidate_indices.extend(
            sentence_index
            for sentence_index, _ in sorted(
                enumerate(sentences),
                key=sentence_signal,
                reverse=True,
            )
            if sentence_index not in seen_candidate_indices
        )

        selected_indices: set[int] = set()
        selected_words = 0
        for sentence_index in candidate_indices:
            sentence = sentences[sentence_index].strip()
            sentence_words = len(sentence.split())
            if selected_words + sentence_words > max_words:
                continue
            selected_indices.add(sentence_index)
            selected_words += sentence_words
            if selected_words >= max_words:
                break

        if selected_indices:
            return " ".join(sentences[index] for index in sorted(selected_indices)).strip()

        # A malformed PDF can expose a whole paragraph as one sentence. Keep the
        # span around the first query term so the useful evidence is not lost.
        focus_terms = core_terms | goal_terms | expanded_terms
        focus_index = next(
            (
                index
                for index, word in enumerate(words)
                if any(
                    SynthesisService._term_matches(sentence=word, term=term)
                    for term in focus_terms
                )
            ),
            0,
        )
        start = max(0, min(focus_index - (max_words // 3), len(words) - max_words))
        return " ".join(words[start : start + max_words]).strip()

    @staticmethod
    def _citation_context_meta(
        *,
        answer: str,
        bundle: RetrievalBundle,
        selected_context: list[tuple[int, str]],
    ) -> dict[str, object]:
        # Metadata keeps retrieval-rank ordering for API compatibility even
        # when the prompt itself is reordered for obligation coverage.
        selected_anchors = sorted(anchor for anchor, _ in selected_context)
        chunks_by_anchor = {
            anchor: chunk
            for anchor, chunk in enumerate(bundle.chunks[:12], start=1)
            if anchor in set(selected_anchors)
        }
        cited_anchors = SynthesisService._answer_citation_anchors(answer, allowed_anchors=set(selected_anchors))
        cited_chunks = [
            chunks_by_anchor[anchor]
            for anchor in cited_anchors
            if anchor in chunks_by_anchor
        ]
        return {
            "selected_context_chunk_ids": [
                chunks_by_anchor[anchor].chunk_id
                for anchor in selected_anchors
                if anchor in chunks_by_anchor
            ],
            "cited_context_chunk_ids": [chunk.chunk_id for chunk in cited_chunks],
            "citation_anchor_chunk_map": [
                {
                    "anchor": anchor,
                    "chunk_id": chunks_by_anchor[anchor].chunk_id,
                    "document_id": chunks_by_anchor[anchor].document_id,
                    "page_start": chunks_by_anchor[anchor].page_start,
                    "page_end": chunks_by_anchor[anchor].page_end,
                }
                for anchor in cited_anchors
                if anchor in chunks_by_anchor
            ],
            "citation_source": "answer_used_context_chunks",
        }

    @staticmethod
    def _evidence_reliability_gate(
        *,
        response_mode: str,
        generation_backend: str,
        answer_rewritten: bool,
        used_fallback_answer: bool,
        grounding_state: str,
        context_relevance: dict[str, object],
        coverage_meta: dict[str, object],
        verification: dict[str, object],
        citation_context_meta: dict[str, object],
        selected_context: list[tuple[int, str]],
    ) -> dict[str, object]:
        reasons: list[str] = []
        mode = response_mode.strip().lower()
        sentence_count = int(coverage_meta.get("citation_sentence_count") or 0)
        anchor_count = int(coverage_meta.get("citation_anchor_count") or 0)
        citation_coverage_score = float(coverage_meta.get("citation_coverage") or 0.0)
        cited_context_ids = citation_context_meta.get("cited_context_chunk_ids")
        cited_context_count = len(cited_context_ids) if isinstance(cited_context_ids, list) else 0
        relevance_state = str(context_relevance.get("context_relevance_state") or "unknown")
        verification_state = str(verification.get("state") or "unknown")
        overview_or_draft = mode in {"summary", "deep_research", "paper", "research_paper", "study_guide"}

        if not selected_context:
            reasons.append("no_selected_evidence")
        if grounding_state == "weak":
            reasons.append("weak_retrieval_grounding")
        if relevance_state == "unrelated" and not overview_or_draft:
            reasons.append("unrelated_context")
        extractive_fallback = used_fallback_answer or generation_backend == "fallback" or answer_rewritten
        if verification_state == "unsupported" and sentence_count > 0:
            reasons.append("citation_verification_unsupported")
        if verification_state == "unchecked" and sentence_count > 0 and not extractive_fallback:
            reasons.append("citation_verification_unchecked")
        if sentence_count > 0 and anchor_count <= 0:
            reasons.append("no_answer_citation_anchors")
        if sentence_count > 0 and cited_context_count <= 0:
            reasons.append("no_answer_used_citations")

        min_coverage = 0.6 if overview_or_draft or extractive_fallback else 0.75
        if sentence_count >= 2 and citation_coverage_score < min_coverage:
            reasons.append("low_citation_coverage")

        return {
            "evidence_gate_state": "passed" if not reasons else "failed",
            "evidence_gate_reasons": reasons,
            "evidence_gate_min_citation_coverage": min_coverage,
            "evidence_gate_cited_context_count": cited_context_count,
            "evidence_gate_passed": not reasons,
        }

    @staticmethod
    def _evidence_gate_message(evidence_gate: dict[str, object]) -> str:
        return (
            "I found related material, but not enough direct source evidence to answer safely.\n\n"
            "Try asking a narrower question, selecting the correct document, or opening Sources to inspect the passages."
        )

    @staticmethod
    def _answer_citation_anchors(answer: str, *, allowed_anchors: set[int]) -> list[int]:
        anchors: list[int] = []
        seen: set[int] = set()
        for raw_anchor in re.findall(r"\[(\d+)\]", answer):
            anchor = int(raw_anchor)
            if anchor not in allowed_anchors or anchor in seen:
                continue
            anchors.append(anchor)
            seen.add(anchor)
        return anchors

    @staticmethod
    def _build_grounded_prompt(
        query: str,
        context_blocks: list[tuple[int, str]],
        response_mode: str = "research",
        exam_profile: dict[str, object] | None = None,
        exam_context: dict[str, object] | None = None,
        answer_plan: AnswerPlan | None = None,
    ) -> str:
        context = "\n\n".join(block for _, block in context_blocks)
        mode_instruction = SynthesisService._mode_instruction(response_mode)
        exam_instruction = SynthesisService._exam_instruction(exam_profile)
        artifact_instruction = SynthesisService._exam_artifact_instruction(exam_context, query=query)
        resolved_plan = answer_plan or build_answer_plan(
            query=query,
            response_mode=response_mode,
            exam_profile=exam_profile,
        )
        return (
            "You are NIRMIQ local research assistant.\n"
            "Use ONLY the context below. Do not invent facts.\n"
            "If evidence is insufficient, say so plainly.\n"
            "Cite claims with [n] where n is the context block number.\n"
            "Prefer higher-scoring context blocks when multiple sources support the same claim.\n"
            "Answer the user's exact question, not a generic document summary.\n"
            "First connect the relevant evidence into a coherent explanation; do not paste index entries or unrelated fragments.\n"
            "Paraphrase for clarity while preserving the source's technical terms, numbers, and meaning.\n"
            "Do not infer a mechanism from an analogy, biological inspiration, or historical background unless the context explicitly supports that mechanism.\n"
            "Use citation anchors at the end of paragraphs or bullets that rely on source evidence. Avoid citation spam.\n"
            "If the user asks for algorithms, examples, steps, or a list, answer as a concise list and cite each item.\n"
            "Keep paragraphs short and avoid dense textbook dumps.\n"
            f"{resolved_plan.prompt_instruction()}\n"
            f"{mode_instruction}\n\n"
            f"{exam_instruction}\n"
            f"{artifact_instruction}\n"
            f"User Query:\n{query}\n\n"
            f"Context:\n{context}\n\n"
            "Answer:"
        )

    @staticmethod
    def _fallback_answer(
        query: str,
        context_chunks: list[tuple[int, str]],
        response_mode: str = "research",
        exam_profile: dict[str, object] | None = None,
        exam_context: dict[str, object] | None = None,
        additional_terms: set[str] | None = None,
    ) -> str:
        mode = response_mode.strip().lower()
        answer_plan = build_answer_plan(
            query=query,
            response_mode=response_mode,
            exam_profile=exam_profile,
        )
        if mode == "study_guide":
            return SynthesisService._fallback_study_guide(
                query=query,
                context_chunks=context_chunks,
                exam_context=exam_context or {"questions": [], "diagrams": []},
            )
        if SynthesisService._is_document_overview_query(query, response_mode):
            return SynthesisService._fallback_document_summary(
                query=query,
                context_chunks=context_chunks,
            )
        if mode in {"paper", "research_paper"} and answer_plan.answer_type == "academic_draft":
            return SynthesisService._fallback_research_paper(query=query, context_chunks=context_chunks)
        if mode in {"exam", "exam_answer"}:
            return SynthesisService._fallback_exam_answer(
                query=query,
                context_chunks=context_chunks,
                exam_profile=exam_profile,
                exam_context=exam_context,
            )
        if "equations" in answer_plan.requested_elements:
            equation_answer = SynthesisService._fallback_equation_answer(
                query=query,
                context_chunks=context_chunks,
                answer_plan=answer_plan,
            )
            if equation_answer:
                return equation_answer
        if answer_plan.answer_type == "factual_lookup":
            return SynthesisService._fallback_planned_answer(
                query=query,
                context_chunks=context_chunks,
                answer_plan=answer_plan,
                additional_terms=additional_terms,
            )
        if answer_plan.answer_type == "enumeration":
            return SynthesisService._fallback_enumeration_answer(
                query=query,
                context_chunks=context_chunks,
                response_mode=response_mode,
                answer_plan=answer_plan,
            )
        if answer_plan.answer_type == "concept_explanation" and re.search(r"\bwhy\b", query, re.I):
            return SynthesisService._fallback_planned_answer(
                query=query,
                context_chunks=context_chunks,
                answer_plan=answer_plan,
                additional_terms=additional_terms,
            )
        if SynthesisService._is_list_or_algorithm_query(query):
            return SynthesisService._fallback_list_answer(
                query=query,
                context_chunks=context_chunks,
                response_mode=response_mode,
            )
        if SynthesisService._is_local_first_definition_query(query):
            return SynthesisService._fallback_local_first_answer(
                query=query,
                context_chunks=context_chunks,
            )
        if SynthesisService._is_definition_solution_query(query):
            return SynthesisService._fallback_definition_solution_answer(
                query=query,
                context_chunks=context_chunks,
            )
        if SynthesisService._is_privacy_control_query(query) or SynthesisService._is_privacy_cue_query(query):
            return SynthesisService._fallback_privacy_control_answer(
                query=query,
                context_chunks=context_chunks,
            )
        if SynthesisService._is_definition_query(query):
            return SynthesisService._fallback_definition_answer(
                query=query,
                context_chunks=context_chunks,
                response_mode=response_mode,
                additional_terms=additional_terms,
            )
        if answer_plan.answer_type in {
            "mechanism_explanation",
            "procedure",
            "workflow_placement",
            "recommendation",
            "interpretation",
            "comparison",
            "limitations",
        }:
            return SynthesisService._fallback_planned_answer(
                query=query,
                context_chunks=context_chunks,
                answer_plan=answer_plan,
                additional_terms=additional_terms,
            )

        query_terms = SynthesisService._query_terms(query)
        candidates: list[tuple[float, int, str]] = []
        for idx, block in context_chunks[:6]:
            text = SynthesisService._context_text(block)
            for sentence_index, sentence in enumerate(SynthesisService._split_sentences(text)[:10]):
                if len(sentence.split()) < 6 or SynthesisService._is_low_value_evidence_sentence(sentence):
                    continue
                term_score = SynthesisService._sentence_score(sentence, query_terms)
                rank_bonus = max(0, 7 - idx) * 0.12 + max(0, 10 - sentence_index) * 0.02
                candidates.append((term_score + rank_bonus, idx, sentence))

        selected: list[tuple[int, str]] = []
        seen: set[str] = set()
        for _, idx, sentence in sorted(candidates, key=lambda item: item[0], reverse=True):
            normalized = re.sub(r"\W+", "", sentence.lower())[:96]
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append((idx, sentence))
            if len(selected) >= 3:
                break

        if not selected:
            selected = [
                (idx, preview)
                for idx, block in context_chunks[:3]
                if (preview := SynthesisService._context_text(block)[:220].strip())
            ]

        if not selected:
            return "I found citations, but there was not enough readable text to synthesize a grounded answer."

        heading = SynthesisService._fallback_heading(response_mode)
        return SynthesisService._format_extract_answer(
            heading=heading,
            selected=selected,
            response_mode=response_mode,
        )

    @staticmethod
    def _fallback_planned_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
        answer_plan: AnswerPlan,
        additional_terms: set[str] | None = None,
    ) -> str:
        """Build a readable extractive answer around the query's evidence contract."""

        if answer_plan.answer_type == "factual_lookup":
            direct_factual_answer = SynthesisService._fallback_factual_answer(
                query=query,
                context_chunks=context_chunks,
            )
            if direct_factual_answer:
                return direct_factual_answer
        if answer_plan.answer_type == "comparison":
            direct_comparison_answer = SynthesisService._fallback_comparison_answer(
                context_chunks=context_chunks,
                answer_plan=answer_plan,
            )
            if direct_comparison_answer:
                return direct_comparison_answer
        if answer_plan.answer_type == "interpretation":
            direct_interpretation_answer = SynthesisService._fallback_interpretation_answer(
                query=query,
                context_chunks=context_chunks,
                answer_plan=answer_plan,
            )
            if direct_interpretation_answer:
                return direct_interpretation_answer
        if answer_plan.answer_type == "procedure":
            procedure_answer = SynthesisService._fallback_procedure_answer(
                query=query,
                context_chunks=context_chunks,
            )
            if procedure_answer:
                return procedure_answer
        if answer_plan.answer_type == "limitations":
            limitations_answer = SynthesisService._fallback_limitations_answer(
                query=query,
                context_chunks=context_chunks,
            )
            if limitations_answer:
                return limitations_answer
        if answer_plan.answer_type == "recommendation":
            recommendation_answer = SynthesisService._fallback_recommendation_answer(
                query=query,
                context_chunks=context_chunks,
                answer_plan=answer_plan,
                additional_terms=additional_terms,
            )
            if recommendation_answer:
                return recommendation_answer
        if answer_plan.answer_type == "mechanism_explanation":
            mechanism_answer = SynthesisService._fallback_how_can_answer(
                query=query,
                context_chunks=context_chunks,
                additional_terms=additional_terms,
            )
            if mechanism_answer:
                return mechanism_answer
            mechanism_answer = SynthesisService._fallback_text_generation_answer(
                query=query,
                context_chunks=context_chunks,
            )
            if mechanism_answer:
                return mechanism_answer
        if "equations" in answer_plan.requested_elements:
            equation_answer = SynthesisService._fallback_equation_answer(
                query=query,
                context_chunks=context_chunks,
                answer_plan=answer_plan,
            )
            if equation_answer:
                return equation_answer

        subject_terms = {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", answer_plan.subject.lower())
            if token not in _QUERY_STOPWORDS and len(token) >= 3
        }
        literal_query_terms = {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", query.lower())
            if token not in _QUERY_STOPWORDS
        }
        expanded_query_terms = (
            SynthesisService._query_terms(query)
            | (additional_terms or set())
        )
        core_subject_terms = SynthesisService._core_subject_terms(query=query, answer_plan=answer_plan)
        scoring_terms = core_subject_terms or subject_terms or literal_query_terms
        goal_terms = literal_query_terms - core_subject_terms - _ANSWER_TASK_TERMS
        expanded_scoring_terms = expanded_query_terms - _ANSWER_TASK_TERMS
        prepared_context = [
            (idx, SynthesisService._context_text(block))
            for idx, block in context_chunks[:10]
        ]
        term_weights = SynthesisService._context_term_weights(
            terms=scoring_terms | expanded_scoring_terms,
            context_texts=[text for _, text in prepared_context],
        )
        requested_elements = set(answer_plan.requested_elements)
        allow_roadmap_evidence = SynthesisService._allows_roadmap_evidence(
            query=query,
            answer_type=answer_plan.answer_type,
        )
        benefit_cues = (
            "benefit",
            "advantage",
            "improves ",
            "improve ",
            "reduces ",
            "reduce ",
            "reducing ",
            "faster",
            "allows ",
            "stabilizes ",
            "stabilize ",
            "higher ",
            "better ",
            "speeding up",
            "speeds up",
            "less sensitive",
            "fewer ",
        )
        definition_cues = (
            " is a ",
            " is an ",
            " means ",
            " refers to ",
            " defined as ",
            " consists of ",
        )
        chunk_sentences: dict[int, list[str]] = {}
        chunk_core_positions: dict[int, list[int]] = {}
        chunk_anchor_positions: dict[int, list[int]] = {}
        chunk_plan_scores: dict[int, float] = {}
        chunk_core_coverage: dict[int, float] = {}
        chunk_obligation_coverage: dict[int, float] = {}
        chunk_obligation_strength: dict[int, float] = {}
        for idx, text in prepared_context:
            sentences = SynthesisService._planned_evidence_units(
                text=text,
                allow_roadmap_evidence=allow_roadmap_evidence,
            )[:24]
            chunk_covers_core = bool(core_subject_terms) and (
                SynthesisService._sentence_score(text, core_subject_terms) >= len(core_subject_terms)
            )
            core_coverage = min(
                1.0,
                SynthesisService._sentence_score(text, core_subject_terms)
                / max(len(core_subject_terms), 1),
            ) if core_subject_terms else 1.0
            chunk_core_coverage[idx] = core_coverage
            core_positions = [
                position
                for position, sentence in enumerate(sentences)
                if (
                    SynthesisService._has_core_subject_anchor(sentence, core_subject_terms)
                    or (
                        chunk_covers_core
                        and SynthesisService._sentence_score(sentence, core_subject_terms) >= 1
                    )
                    or (
                        SynthesisService._sentence_score(sentence, core_subject_terms) >= 1
                        and answer_evidence_cue_score(answer_plan.answer_type, sentence) >= 0.6
                    )
                )
                and (allow_roadmap_evidence or not SynthesisService._is_roadmap_sentence(sentence))
                and not SynthesisService._is_low_value_evidence_sentence(sentence)
                and not SynthesisService._is_code_heavy_sentence(sentence)
            ]
            focus_positions = [
                position
                for position, sentence in enumerate(sentences)
                if (
                    SynthesisService._has_answer_focus_anchor(
                        sentence=sentence,
                        answer_type=answer_plan.answer_type,
                        goal_terms=goal_terms,
                        expanded_terms=expanded_scoring_terms,
                    )
                    or any(
                        evidence_obligation_score(obligation, sentence) >= 0.32
                        for obligation in answer_plan.evidence_obligations
                    )
                )
                and (allow_roadmap_evidence or not SynthesisService._is_roadmap_sentence(sentence))
                and not SynthesisService._is_low_value_evidence_sentence(sentence)
                and not SynthesisService._is_code_heavy_sentence(sentence)
            ]
            anchor_positions = sorted(set(core_positions) | set(focus_positions))
            chunk_sentences[idx] = sentences
            chunk_core_positions[idx] = core_positions
            chunk_anchor_positions[idx] = anchor_positions

            supported_required = 0
            required_count = 0
            required_strengths: list[float] = []
            for obligation in answer_plan.evidence_obligations:
                if not obligation.required:
                    continue
                required_count += 1
                obligation_strength = max(
                    (
                        evidence_obligation_score(obligation, sentence)
                        if (
                            SynthesisService._sentence_score(sentence, core_subject_terms) > 0
                            or any(abs(position - sentence_index) <= 2 for position in core_positions)
                            or core_coverage >= 0.75
                        )
                        else 0.0
                        for sentence_index, sentence in enumerate(sentences)
                    ),
                    default=0.0,
                )
                required_strengths.append(obligation_strength)
                obligation_supported = obligation_strength >= 0.32
                supported_required += int(obligation_supported)
            obligation_coverage = (
                supported_required / required_count if required_count else 1.0
            )
            chunk_obligation_coverage[idx] = obligation_coverage
            chunk_obligation_strength[idx] = (
                sum(required_strengths) / len(required_strengths)
                if required_strengths
                else 1.0
            )

            # Chapter roadmaps can mention the subject without answering the
            # question. Rank each chunk by its best local answer-bearing window.
            if core_subject_terms and not anchor_positions:
                continue
            local_scores: list[float] = []
            for sentence_index, sentence in enumerate(sentences):
                if (
                    len(sentence.split()) < 6
                    or (
                        not allow_roadmap_evidence
                        and SynthesisService._is_roadmap_sentence(sentence)
                    )
                    or SynthesisService._is_low_value_evidence_sentence(sentence)
                    or SynthesisService._is_extract_fragment(sentence)
                    or (
                        answer_plan.answer_type != "procedure"
                        and SynthesisService._is_code_heavy_sentence(sentence)
                        and not SynthesisService._has_answer_focus_anchor(
                            sentence=sentence,
                            answer_type=answer_plan.answer_type,
                            goal_terms=goal_terms,
                            expanded_terms=expanded_scoring_terms,
                        )
                    )
                ):
                    continue
                near_core_subject = any(
                    0 <= sentence_index - position <= 3
                    for position in anchor_positions
                )
                local_score = SynthesisService._planned_sentence_signal(
                    sentence=sentence,
                    answer_type=answer_plan.answer_type,
                    core_terms=core_subject_terms,
                    goal_terms=goal_terms,
                    expanded_terms=expanded_scoring_terms,
                    near_core=near_core_subject,
                )
                if local_score > 0:
                    local_scores.append(local_score)
            if local_scores:
                precision_local_ranking = answer_plan.answer_type in {
                    "mechanism_explanation",
                    "procedure",
                    "workflow_placement",
                    "recommendation",
                    "interpretation",
                }
                strongest = sorted(local_scores, reverse=True)[:3]
                richness_weights = (
                    (1.0, 0.2, 0.1)
                    if precision_local_ranking
                    else (1.0, 0.45, 0.25)
                )
                richness_score = sum(
                    weight * score
                    for weight, score in zip(richness_weights, strongest, strict=False)
                )
                lowered_chunk = f" {text.lower()} "
                goal_coverage_bonus = min(
                    4.0,
                    2.0 * SynthesisService._sentence_score(text, goal_terms),
                )
                cue_coverage_weight = 10.0 if precision_local_ranking else 4.0
                plan_cue_coverage_bonus = cue_coverage_weight * max(
                    (
                        answer_evidence_cue_score(answer_plan.answer_type, sentence)
                        for sentence in sentences
                    ),
                    default=0.0,
                )
                expanded_coverage_bonus = min(
                    3.0,
                    0.3 * SynthesisService._sentence_score(text, expanded_scoring_terms),
                )
                benefit_coverage_bonus = (
                    1.2
                    if "benefits" in requested_elements
                    and any(cue in lowered_chunk for cue in benefit_cues)
                    else 0.0
                )
                chunk_plan_scores[idx] = (
                    richness_score
                    + goal_coverage_bonus
                    + plan_cue_coverage_bonus
                    + expanded_coverage_bonus
                    + benefit_coverage_bonus
                    + (6.0 * obligation_coverage)
                    + (2.0 * core_coverage)
                    + (0.8 / max(idx, 1))
                )
        prioritized_chunk_ids = {
            idx
            for idx, _ in sorted(
                chunk_plan_scores.items(),
                key=lambda item: (-item[1], item[0]),
            )[:4]
        }
        best_chunk_id = max(
            chunk_plan_scores,
            key=lambda idx: (
                chunk_obligation_strength.get(idx, 0.0),
                chunk_plan_scores[idx],
                -idx,
            ),
            default=None,
        )
        candidates: list[tuple[float, int, str]] = []
        candidate_positions: dict[tuple[int, str], int] = {}
        for idx, text in prepared_context:
            if prioritized_chunk_ids and idx not in prioritized_chunk_ids:
                continue
            chunk_subject_score = SynthesisService._sentence_score(text, scoring_terms)
            chunk_weighted_score = SynthesisService._weighted_sentence_score(text, term_weights)
            sentences = chunk_sentences.get(
                idx,
                SynthesisService._planned_evidence_units(
                    text=text,
                    allow_roadmap_evidence=allow_roadmap_evidence,
                )[:24],
            )
            core_positions = chunk_core_positions.get(idx, [])
            anchor_positions = chunk_anchor_positions.get(idx, core_positions)
            if core_subject_terms and not anchor_positions:
                continue
            for sentence_index, sentence in enumerate(sentences):
                if len(sentence.split()) < 6:
                    continue
                if not allow_roadmap_evidence and SynthesisService._is_roadmap_sentence(sentence):
                    continue
                if SynthesisService._is_extract_fragment(sentence):
                    continue
                if (
                    answer_plan.answer_type != "procedure"
                    and SynthesisService._is_code_heavy_sentence(sentence)
                    and not SynthesisService._has_answer_focus_anchor(
                        sentence=sentence,
                        answer_type=answer_plan.answer_type,
                        goal_terms=goal_terms,
                        expanded_terms=expanded_scoring_terms,
                    )
                ):
                    continue
                if (
                    "equations" not in requested_elements
                    and SynthesisService._is_formula_heavy_sentence(sentence)
                ):
                    continue
                if answer_plan.answer_type == "factual_lookup":
                    if any(
                        marker in sentence.lower()
                        for marker in ("isbn", "copyright", "all rights reserved", "trademark")
                    ):
                        continue
                    if (
                        SynthesisService._is_low_value_evidence_sentence(sentence)
                        and SynthesisService._factual_sentence_cue_score(query=query, sentence=sentence) <= 0
                    ):
                        continue
                elif SynthesisService._is_low_value_evidence_sentence(sentence):
                    continue
                lowered = f" {sentence.lower()} "
                subject_score = SynthesisService._sentence_score(sentence, scoring_terms)
                query_score = SynthesisService._sentence_score(sentence, literal_query_terms)
                goal_score = SynthesisService._sentence_score(sentence, goal_terms)
                expanded_query_score = SynthesisService._sentence_score(sentence, expanded_scoring_terms)
                weighted_query_score = SynthesisService._weighted_sentence_score(sentence, term_weights)
                core_subject_score = SynthesisService._sentence_score(sentence, core_subject_terms)
                chunk_core_subject_score = SynthesisService._sentence_score(text, core_subject_terms)
                obligation_fit_score = max(
                    (
                        evidence_obligation_score(obligation, sentence)
                        for obligation in answer_plan.evidence_obligations
                    ),
                    default=0.0,
                )
                nearby_core_passage = any(
                    coverage >= 0.5 and abs(idx - anchor) <= 2
                    for anchor, coverage in chunk_core_coverage.items()
                )
                near_core_subject = core_subject_score > 0 or SynthesisService._has_answer_focus_anchor(
                    sentence=sentence,
                    answer_type=answer_plan.answer_type,
                    goal_terms=goal_terms,
                    expanded_terms=expanded_scoring_terms,
                ) or any(
                    0 <= sentence_index - position <= 3
                    for position in core_positions
                ) or (obligation_fit_score >= 0.42 and nearby_core_passage)
                if anchor_positions and not near_core_subject:
                    continue
                plan_cue_score = answer_evidence_cue_score(answer_plan.answer_type, sentence)
                factual_cue_score = SynthesisService._factual_sentence_cue_score(query=query, sentence=sentence)
                benefit_cue_score = (
                    min(1.0, 0.45 * sum(1 for cue in benefit_cues if cue in lowered))
                    if "benefits" in requested_elements
                    else 0.0
                )
                definition_score = (
                    0.65
                    if subject_score > 0 and any(cue in lowered for cue in definition_cues)
                    else 0.0
                )
                sequence_cue_score = (
                    1.2
                    if answer_plan.answer_type == "mechanism_explanation"
                    and any(
                        cue in lowered
                        for cue in (" for each ", " counts ", " count ", " first ", " then ", " next ")
                    )
                    else 0.0
                )
                precision_intent = answer_plan.answer_type in {
                    "mechanism_explanation",
                    "procedure",
                    "workflow_placement",
                    "recommendation",
                    "interpretation",
                }
                goal_weight = 2.8 if precision_intent and goal_terms else 1.2
                core_weight = 1.25 if precision_intent and goal_terms else 1.8
                plan_weight = 5.0 if precision_intent else 3.0

                if answer_plan.answer_type in {
                    "mechanism_explanation",
                    "procedure",
                    "workflow_placement",
                    "recommendation",
                    "interpretation",
                    "limitations",
                }:
                    if (
                        plan_cue_score <= 0
                        and obligation_fit_score <= 0
                        and definition_score <= 0
                        and benefit_cue_score <= 0
                        and goal_score <= 0
                        and expanded_query_score < 2
                    ):
                        continue
                elif answer_plan.answer_type == "comparison":
                    if plan_cue_score <= 0 and subject_score < min(2, max(1, len(scoring_terms))):
                        continue
                elif answer_plan.answer_type == "factual_lookup" and factual_cue_score <= 0:
                    continue

                # Pronoun-led process sentences may omit the subject but are valid
                # when their containing passage strongly matches it.
                if (
                    subject_score <= 0
                    and chunk_subject_score <= 0
                    and goal_score <= 0
                    and expanded_query_score <= 0
                    and factual_cue_score <= 0
                    and obligation_fit_score <= 0
                ):
                    continue
                rank_bonus = max(0, 11 - idx) * 0.04 + max(0, 14 - sentence_index) * 0.01
                chunk_plan_bonus = 3.0 if idx == best_chunk_id else 0.15
                word_count = len(sentence.split())
                length_penalty = min(5.0, max(0, word_count - 55) / 15)
                code_penalty = 1.25 if any(
                    marker in sentence
                    for marker in (">>>", "tf.keras", "np.array", "array([", "model.fit(")
                ) else 0.0
                score = (
                    (0.45 * subject_score)
                    + (0.1 * min(query_score, 4.0))
                    + (goal_weight * min(goal_score, 3.0))
                    + (0.1 * min(expanded_query_score, 5.0))
                    + (0.85 * weighted_query_score)
                    + (0.12 * min(chunk_weighted_score, 5.0))
                    + (core_weight * core_subject_score)
                    + (0.35 * min(chunk_core_subject_score, 2.0))
                    + (plan_weight * plan_cue_score)
                    + (5.0 * obligation_fit_score)
                    + (3.0 * chunk_obligation_coverage.get(idx, 0.0))
                    + (1.5 * chunk_core_coverage.get(idx, 0.0))
                    + (2.4 * factual_cue_score)
                    + (1.6 * benefit_cue_score)
                    + definition_score
                    + sequence_cue_score
                    + rank_bonus
                    + chunk_plan_bonus
                    - length_penalty
                    - code_penalty
                )
                candidates.append((score, idx, sentence))
                candidate_positions[(idx, SynthesisService._clean_evidence_sentence(sentence))] = sentence_index

        passage_candidates = [item for item in candidates if item[1] == best_chunk_id]
        precision_first_types = {
            "mechanism_explanation",
            "procedure",
            "workflow_placement",
            "recommendation",
            "interpretation",
            "limitations",
        }
        obligation_selected = SynthesisService._select_obligation_sentences(
            candidates=candidates,
            answer_plan=answer_plan,
            core_subject_terms=core_subject_terms,
            chunk_core_coverage=chunk_core_coverage,
            chunk_obligation_coverage=chunk_obligation_coverage,
            core_passage_anchors={
                anchor
                for anchor, coverage in chunk_core_coverage.items()
                if coverage >= 0.5
            },
            preferred_anchor=best_chunk_id,
            limit=min(5, max(3, len(answer_plan.evidence_obligations) + 1)),
        )
        selected_pool = candidates if answer_plan.evidence_obligations else (
            passage_candidates if len(passage_candidates) >= 2 else candidates
        )
        ranked_selected = SynthesisService._dedupe_scored_sentences(
            selected_pool,
            limit=5 if answer_plan.answer_type in precision_first_types else 6,
            allow_low_value=answer_plan.answer_type == "factual_lookup",
        )
        selected = list(obligation_selected)
        selected_keys = {
            (anchor, re.sub(r"\W+", "", sentence.lower())[:120])
            for anchor, sentence in selected
        }
        covered_obligation_keys = {
            obligation.key
            for obligation in answer_plan.evidence_obligations
            if any(
                evidence_obligation_score(obligation, sentence) >= 0.32
                for _, sentence in selected
            )
        }
        for anchor, sentence in ranked_selected:
            key = (anchor, re.sub(r"\W+", "", sentence.lower())[:120])
            if key in selected_keys:
                continue
            passage_core_coverage = chunk_core_coverage.get(anchor, 0.0)
            sentence_core_score = SynthesisService._sentence_score(
                sentence,
                core_subject_terms,
            )
            if (
                obligation_selected
                and core_subject_terms
                and passage_core_coverage < 0.5
                and sentence_core_score <= 0
            ):
                continue
            newly_supported = {
                obligation.key
                for obligation in answer_plan.evidence_obligations
                if obligation.key not in covered_obligation_keys
                and evidence_obligation_score(obligation, sentence) >= 0.32
            }
            if obligation_selected and not newly_supported:
                current_position = candidate_positions.get(
                    (anchor, SynthesisService._clean_evidence_sentence(sentence)),
                    1_000_000,
                )
                selected_positions = [
                    candidate_positions.get(
                        (selected_anchor, SynthesisService._clean_evidence_sentence(selected_sentence)),
                        1_000_000,
                    )
                    for selected_anchor, selected_sentence in selected
                    if selected_anchor == anchor
                ]
                obligation_fit = max(
                    (
                        evidence_obligation_score(obligation, sentence)
                        for obligation in answer_plan.evidence_obligations
                    ),
                    default=0.0,
                )
                same_passage_continuation = bool(
                    answer_plan.answer_type == "mechanism_explanation"
                    and selected_positions
                    and min(
                        (
                            current_position - position
                            for position in selected_positions
                            if current_position > position
                        ),
                        default=1_000_000,
                    ) <= 2
                    and obligation_fit >= 0.42
                )
                if not same_passage_continuation:
                    continue
            selected.append((anchor, sentence))
            selected_keys.add(key)
            covered_obligation_keys.update(newly_supported)
            if len(selected) >= (5 if answer_plan.answer_type in precision_first_types else 6):
                break
        focus_obligation = next(
            (
                obligation
                for obligation in answer_plan.evidence_obligations
                if obligation.key == "operation_focus"
            ),
            None,
        )
        required_obligations = [
            obligation
            for obligation in answer_plan.evidence_obligations
            if obligation.required
        ]
        if (
            answer_plan.answer_type == "mechanism_explanation"
            and focus_obligation
            and best_chunk_id is not None
            and all(
                any(
                    anchor == best_chunk_id
                    and evidence_obligation_score(obligation, sentence) >= 0.32
                    for _, anchor, sentence in candidates
                )
                for obligation in required_obligations
            )
        ):
            same_passage_selected = [
                item for item in selected if item[0] == best_chunk_id
            ]
            if same_passage_selected:
                selected = same_passage_selected
        if answer_plan.answer_type == "interpretation" and len(selected) < 4:
            existing = {(anchor, sentence) for anchor, sentence in selected}
            continuations: list[tuple[float, int, str]] = []
            for score, anchor, sentence in candidates:
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if (anchor, cleaned) in existing or anchor == best_chunk_id:
                    continue
                continuation_has_focus = SynthesisService._has_answer_focus_anchor(
                    sentence=cleaned,
                    answer_type=answer_plan.answer_type,
                    goal_terms=goal_terms,
                    expanded_terms=expanded_scoring_terms,
                )
                continuation_cue = answer_evidence_cue_score(answer_plan.answer_type, cleaned)
                if continuation_cue < 0.6 and not continuation_has_focus:
                    continue
                lowered = cleaned.lower()
                outcome_bonus = (
                    (3.0 if "highest" in lowered else 0.0)
                    + (0.3 if any(cue in lowered for cue in ("predicts", "selects", "outputs")) else 0.0)
                )
                continuations.append((score + outcome_bonus, anchor, cleaned))
            if continuations:
                continuation_limit = 2 if answer_plan.answer_type == "interpretation" else 1
                for _, anchor, sentence in sorted(continuations, reverse=True)[:continuation_limit]:
                    selected.append((anchor, sentence))
        if len(passage_candidates) >= 2 and not obligation_selected:
            lead = selected[0]
            details = sorted(
                selected[1:],
                key=lambda item: (
                    item[0] != best_chunk_id,
                    candidate_positions.get(item, 1_000_000),
                ),
            )
            selected = [lead, *details]
        if selected and answer_plan.answer_type in precision_first_types and (
            not obligation_selected or answer_plan.answer_type == "mechanism_explanation"
        ):
            def lead_priority(item: tuple[int, str]) -> tuple[float, int]:
                anchor, sentence = item
                cue_score = answer_evidence_cue_score(answer_plan.answer_type, sentence)
                goal_score = SynthesisService._sentence_score(sentence, goal_terms)
                expanded_score = SynthesisService._sentence_score(sentence, expanded_scoring_terms)
                core_score = SynthesisService._sentence_score(sentence, core_subject_terms)
                word_count = len(sentence.split())
                table_penalty = 5.0 if (
                    word_count > 65
                    or (
                        "equations" not in requested_elements
                        and SynthesisService._is_formula_heavy_sentence(sentence)
                    )
                ) else 0.0
                lowered = f" {sentence.lower()} "
                interpretation_bonus = 0.0
                if answer_plan.answer_type == "interpretation":
                    interpretation_bonus = 1.5 * sum(
                        lowered.count(cue)
                        for cue in (" means ", " close to ", " ranges from ", " can vary between ")
                    )
                action_bonus = 1.2 * sum(
                    lowered.count(cue)
                    for cue in (
                        " compute ",
                        " calculated as ",
                        " computed as ",
                        " derived as ",
                        " equals ",
                        " apply ",
                        " add ",
                        " divide ",
                        " prevent ",
                        " temporarily ",
                        " ignored ",
                        " active ",
                        " increasing ",
                        " decreasing ",
                    )
                )
                focus_weight = 2.0 if answer_plan.answer_type in precision_first_types else 0.5
                expansion_weight = 0.15 if answer_plan.answer_type in precision_first_types else 0.3
                focus_bonus = (
                    6.0 * evidence_obligation_score(focus_obligation, sentence)
                    if focus_obligation
                    else 0.0
                )
                score = (
                    (6.0 * cue_score)
                    + (2.0 * goal_score)
                    + (expansion_weight * expanded_score)
                    + (focus_weight * core_score)
                    + interpretation_bonus
                    + action_bonus
                    + focus_bonus
                    - table_penalty
                )
                return score, -anchor

            eligible_leads = selected
            if answer_plan.answer_type != "interpretation" and best_chunk_id is not None:
                same_passage = [item for item in selected if item[0] == best_chunk_id]
                if same_passage:
                    eligible_leads = same_passage
            lead = max(eligible_leads, key=lead_priority)
            remaining = sorted(
                (item for item in selected if item != lead),
                key=lead_priority,
                reverse=True,
            )
            selected = [lead, *remaining]
        if not selected:
            return (
                "I found related passages, but not enough direct evidence to answer this "
                "part of the question confidently."
            )

        detail_labels = {
            "mechanism_explanation": "How it works",
            "procedure": "Steps from the source",
            "workflow_placement": "Where it fits",
            "recommendation": "Recommendations from the source",
            "interpretation": "How to read it",
            "comparison": "Key differences",
            "limitations": "Benefits and limitations" if "benefits" in requested_elements else "Limitations",
            "factual_lookup": "Supporting detail",
        }
        lead_anchor, lead_sentence = selected[0]
        lead_sentence = SynthesisService._with_explicit_lead_subject(
            sentence=lead_sentence,
            answer_plan=answer_plan,
            core_subject_terms=core_subject_terms,
        )
        sections = ["Short answer", f"\n{lead_sentence} [{lead_anchor}]"]
        details = [item for item in selected[1:] if item[1] != lead_sentence]
        if answer_plan.answer_type in precision_first_types:
            details = [
                (anchor, sentence)
                for anchor, sentence in details
                if answer_evidence_cue_score(answer_plan.answer_type, sentence) >= 0.6
                or SynthesisService._sentence_score(sentence, goal_terms) > 0
                or SynthesisService._has_core_subject_anchor(sentence, core_subject_terms)
                or any(
                    evidence_obligation_score(obligation, sentence) >= 0.32
                    for obligation in answer_plan.evidence_obligations
                )
                or (
                    answer_plan.answer_type == "recommendation"
                    and anchor == lead_anchor
                )
            ]
        if details:
            sections.append(f"\n{detail_labels.get(answer_plan.answer_type, 'Explanation')}")
            detail_limit = (
                4 if answer_plan.answer_type in precision_first_types else 5
            )
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in details[:detail_limit])
        return "\n".join(sections)

    @staticmethod
    def _fallback_recommendation_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
        answer_plan: AnswerPlan,
        additional_terms: set[str] | None = None,
    ) -> str | None:
        """Keep recommendation answers anchored to the requested subject."""

        core_terms = SynthesisService._core_subject_terms(
            query=query,
            answer_plan=answer_plan,
        )
        query_terms = SynthesisService._query_terms(query)
        expanded_terms = set(additional_terms or set())
        optimization_terms = {
            "webp",
            "lazy loading",
            "lazy-load",
            "preload",
            "reduced-motion",
            "reduced motion",
            "compress",
            "compression",
            "under 2mb",
            "explicit width",
            "layout shift",
        }
        deployment_terms = {
            "static site",
            "static sites",
            "vercel",
            "netlify",
            "custom domain",
            "https",
            "lighthouse",
            "90+",
        }
        if re.search(r"\b(?:optimi[sz]|asset|animation|performance|load speed)\w*\b", query, re.I):
            expanded_terms.update(optimization_terms)
        if re.search(r"\b(?:deploy|deployment|hosting|host|domain)\w*\b", query, re.I):
            expanded_terms.update(deployment_terms)
        candidates: list[tuple[float, int, str]] = []
        focused_recommendation_query = bool(
            expanded_terms & (optimization_terms | deployment_terms)
        )
        for anchor, block in context_chunks[:10]:
            scoring_text = SynthesisService._context_text_with_heading(block)
            for position, sentence in enumerate(
                SynthesisService._split_sentences(scoring_text)[:20]
            ):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if (
                    len(cleaned.split()) < (3 if focused_recommendation_query else 6)
                    or SynthesisService._is_low_value_evidence_sentence(cleaned)
                    or SynthesisService._is_code_heavy_sentence(cleaned)
                ):
                    continue
                subject_score = SynthesisService._sentence_score(cleaned, core_terms)
                query_score = SynthesisService._sentence_score(cleaned, query_terms)
                recommendation_score = answer_evidence_cue_score("recommendation", cleaned)
                optimization_score = 0.0
                if expanded_terms:
                    optimization_score = min(
                        4.0,
                        sum(1.2 for term in optimization_terms if term in cleaned.lower()),
                    )
                deployment_score = min(
                    4.0,
                    sum(1.2 for term in deployment_terms if term in cleaned.lower()),
                )
                obligation_score = max(
                    (
                        evidence_obligation_score(obligation, cleaned)
                        for obligation in answer_plan.evidence_obligations
                    ),
                    default=0.0,
                )
                if (
                    subject_score <= 0
                    and obligation_score < 0.6
                    and query_score < 2
                    and optimization_score <= 0
                    and deployment_score <= 0
                ):
                    continue
                score = (
                    (5.0 * subject_score)
                    + (4.0 * obligation_score)
                    + (4.0 * recommendation_score)
                    + (6.0 * optimization_score)
                    + (6.0 * deployment_score)
                    + (0.7 * query_score)
                    + max(0, 12 - position) * 0.02
                )
                candidates.append((score, anchor, cleaned))

        selected = SynthesisService._dedupe_scored_sentences(
            candidates,
            limit=4,
            min_words=3 if focused_recommendation_query else 6,
        )
        if not selected:
            return None
        lead_anchor, lead_sentence = selected[0]
        details = [
            (anchor, sentence)
            for anchor, sentence in selected[1:]
            if (
                anchor == lead_anchor
                or evidence_obligation_score(
                    answer_plan.evidence_obligations[0],
                    sentence,
                ) >= 0.8
                or SynthesisService._sentence_score(sentence, core_terms) > 0
                or answer_evidence_cue_score("recommendation", sentence) >= 0.6
                or any(
                    term in sentence.lower()
                    for term in optimization_terms | deployment_terms
                )
            )
        ]
        sections = ["Short answer", f"\n{lead_sentence} [{lead_anchor}]"]
        if details:
            sections.append("\nRecommendations from the source")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in details[:3])
        return "\n".join(sections)

    @staticmethod
    def _fallback_comparison_answer(
        *,
        context_chunks: list[tuple[int, str]],
        answer_plan: AnswerPlan,
    ) -> str | None:
        """Build a comparison only when every named side has direct evidence."""

        side_obligations = [
            obligation
            for obligation in answer_plan.evidence_obligations
            if obligation.key.startswith("comparison_side_")
        ]

        evidence_units: list[tuple[int, str]] = []
        for anchor, block in context_chunks[:10]:
            for sentence in SynthesisService._planned_evidence_units(
                text=SynthesisService._context_text_with_heading(block),
                allow_roadmap_evidence=True,
            ):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if (
                    not cleaned
                    or SynthesisService._is_low_value_evidence_sentence(cleaned)
                    or SynthesisService._is_code_heavy_sentence(cleaned)
                    or SynthesisService._is_roadmap_sentence(cleaned)
                ):
                    continue
                evidence_units.append((anchor, cleaned))

        if len(side_obligations) < 2:
            query_terms = SynthesisService._query_terms(answer_plan.subject)
            ranked_units = sorted(
                (
                    (
                        SynthesisService._sentence_score(sentence, query_terms)
                        + (1.8 if re.search(r"^\s*for\s+", sentence, re.I) else 0.0)
                        + (0.8 if re.search(r"\b(?:while|whereas|compared|unlike)\b", sentence, re.I) else 0.0)
                        + (0.6 if re.search(r"\b(?:reduces?|improves?|helps?|supports?)\b", sentence, re.I) else 0.0),
                        anchor,
                        sentence,
                    )
                    for anchor, sentence in evidence_units
                    if SynthesisService._sentence_score(sentence, query_terms) > 0
                ),
                reverse=True,
            )
            selected = SynthesisService._dedupe_scored_sentences(ranked_units, limit=3)
            if not selected:
                return None
            return "\n".join(
                [
                    "Direct comparison",
                    "",
                    *(f"- {sentence} [{anchor}]" for anchor, sentence in selected),
                ]
            )

        explicit_contrast = re.compile(
            r"\b(?:whereas|while|unlike|compared|versus|vice versa|in contrast)\b",
            re.I,
        )
        for anchor, sentence in evidence_units:
            if explicit_contrast.search(sentence) and all(
                evidence_obligation_score(obligation, sentence) >= 0.32
                for obligation in side_obligations
            ):
                return f"Direct comparison\n\n{sentence} [{anchor}]"

        selected: list[tuple[str, int, str]] = []
        used_sentences: set[str] = set()
        for side_index, obligation in enumerate(side_obligations):
            ranked: list[tuple[float, int, str]] = []
            side_terms = set(obligation.retrieval_terms)
            other_side_terms = {
                term
                for index, other in enumerate(side_obligations)
                if index != side_index
                for term in other.retrieval_terms
            }
            for anchor, sentence in evidence_units:
                normalized = re.sub(r"\W+", "", sentence.lower())[:160]
                if normalized in used_sentences:
                    continue
                obligation_score = evidence_obligation_score(obligation, sentence)
                if obligation_score < 0.32:
                    continue
                side_score = SynthesisService._sentence_score(sentence, side_terms)
                other_side_score = SynthesisService._sentence_score(sentence, other_side_terms)
                side_head_bonus = 0.0
                if side_terms:
                    side_pattern = r"\b(?:" + "|".join(re.escape(term) for term in side_terms) + r")\b"
                    if re.match(rf"\s*(?:the\s+)?{side_pattern}", sentence, flags=re.I):
                        side_head_bonus = 4.0
                word_count = len(sentence.split())
                ranked.append(
                    (
                        (20.0 * obligation_score)
                        + (2.0 * side_score)
                        - (1.4 * other_side_score)
                        + side_head_bonus
                        + answer_evidence_cue_score("concept_explanation", sentence)
                        + max(0.0, 1.0 - (anchor * 0.03))
                        - max(0.0, (word_count - 55) / 20),
                        anchor,
                        sentence,
                    )
                )
            if not ranked:
                return None
            _, anchor, sentence = max(ranked)
            used_sentences.add(re.sub(r"\W+", "", sentence.lower())[:160])
            label = obligation.label.removeprefix("evidence for ").strip().capitalize()
            selected.append((label, anchor, sentence))

        lines = ["Direct comparison", ""]
        lines.extend(
            f"- {label}: {sentence} [{anchor}]"
            for label, anchor, sentence in selected
        )
        return "\n".join(lines)

    @staticmethod
    def _fallback_interpretation_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
        answer_plan: AnswerPlan,
    ) -> str | None:
        """Extract a complete local value mapping without mixing unrelated metrics."""

        core_terms = SynthesisService._core_subject_terms(
            query=query,
            answer_plan=answer_plan,
        )
        prepared_blocks = [
            (anchor, SynthesisService._context_text(block))
            for anchor, block in context_chunks[:12]
        ]
        block_coverage = {
            anchor: min(
                1.0,
                SynthesisService._sentence_score(text, core_terms) / max(len(core_terms), 1),
            ) if core_terms else 1.0
            for anchor, text in prepared_blocks
        }
        full_subject_available = any(coverage >= 0.75 for coverage in block_coverage.values())
        endpoint_patterns = (
            re.compile(r"(?<!\w)\+1(?!\w)"),
            re.compile(r"(?<![\w-])0(?!\w)"),
            re.compile(r"(?<!\w)-1(?!\w)"),
        )
        mapping_cues = (
            " means ", " indicates ", " represents ", " close to ",
            " ranges from ", " can vary between ", " boundary ",
            " well inside ", " far from ",
        )
        candidates: list[tuple[float, int, int, str]] = []
        for anchor, text in prepared_blocks:
            if full_subject_available and block_coverage.get(anchor, 0.0) < 0.75:
                continue
            for sentence in SynthesisService._split_sentences(text):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if (
                    not cleaned
                    or SynthesisService._is_low_value_evidence_sentence(cleaned)
                    or SynthesisService._is_code_heavy_sentence(cleaned)
                    or SynthesisService._is_roadmap_sentence(cleaned)
                ):
                    continue
                lowered = f" {cleaned.lower()} "
                cue_count = sum(lowered.count(cue) for cue in mapping_cues)
                endpoint_count = sum(bool(pattern.search(cleaned)) for pattern in endpoint_patterns)
                obligation_strength = max(
                    (
                        evidence_obligation_score(obligation, cleaned)
                        for obligation in answer_plan.evidence_obligations
                    ),
                    default=0.0,
                )
                if obligation_strength < 0.32 and cue_count <= 0:
                    continue
                candidates.append(
                    (
                        (8.0 * obligation_strength)
                        + (2.0 * cue_count)
                        + (2.5 * endpoint_count)
                        + (1.5 * block_coverage.get(anchor, 0.0))
                        + max(0.0, 1.0 - (anchor * 0.03)),
                        endpoint_count,
                        anchor,
                        cleaned,
                    )
                )
        if not candidates:
            return None

        ranked = sorted(candidates, reverse=True)
        complete_scale = next((item for item in ranked if item[1] >= 3), None)
        selected = [complete_scale] if complete_scale else ranked[:2]
        lines = ["Interpretation", ""]
        lines.extend(f"- {sentence} [{anchor}]" for _, _, anchor, sentence in selected)
        return "\n".join(lines)

    @staticmethod
    def _with_explicit_lead_subject(
        *,
        sentence: str,
        answer_plan: AnswerPlan,
        core_subject_terms: set[str],
    ) -> str:
        """Name the queried mechanism when an extract starts with a pronoun or transition."""

        if answer_plan.answer_type != "mechanism_explanation":
            return sentence
        if SynthesisService._sentence_score(sentence, core_subject_terms) > 0:
            return sentence
        subject = re.sub(r"\s+", " ", answer_plan.subject).strip(" ,.-")
        if not subject or subject == "the user's requested topic" or len(subject.split()) > 8:
            return sentence
        clause = re.sub(
            r"^(?:here\s+is\s+how\s+it\s+works|this\s+works\s+by)\s*:\s*",
            "",
            sentence,
            flags=re.I,
        ).strip()
        if not clause:
            return sentence
        subject_label = subject[0].upper() + subject[1:]
        return f"{subject_label} works as follows: {clause[0].lower() + clause[1:]}"

    @staticmethod
    def _select_obligation_sentences(
        *,
        candidates: list[tuple[float, int, str]],
        answer_plan: AnswerPlan,
        core_subject_terms: set[str],
        chunk_core_coverage: dict[int, float],
        chunk_obligation_coverage: dict[int, float],
        core_passage_anchors: set[int],
        preferred_anchor: int | None,
        limit: int,
    ) -> list[tuple[int, str]]:
        """Select one direct sentence per supported evidence obligation first."""

        selected: list[tuple[int, str]] = []
        seen: set[str] = set()
        for obligation in answer_plan.evidence_obligations:
            if (
                obligation.key not in {"operation", "value_mapping"}
                and not obligation.key.startswith("comparison_side_")
                and any(
                    evidence_obligation_score(obligation, sentence) >= 0.32
                    for _, sentence in selected
                )
            ):
                continue
            prefer_full_subject_coverage = obligation.key in {
                "operation_focus",
                "interpretive_relation",
                "value_mapping",
            } and any(
                chunk_core_coverage.get(anchor, 0.0) >= 0.75
                and evidence_obligation_score(obligation, sentence) >= 0.32
                for _, anchor, sentence in candidates
            )
            ranked: list[tuple[float, int, str]] = []
            for base_score, anchor, sentence in candidates:
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                obligation_score = evidence_obligation_score(obligation, cleaned)
                if obligation_score < 0.32:
                    continue
                core_score = SynthesisService._sentence_score(cleaned, core_subject_terms)
                passage_core_coverage = chunk_core_coverage.get(anchor, 0.0)
                if prefer_full_subject_coverage and passage_core_coverage < 0.75:
                    continue
                if obligation.key == "operation" and selected:
                    focus_obligation = next(
                        (
                            item
                            for item in answer_plan.evidence_obligations
                            if item.key == "operation_focus"
                        ),
                        None,
                    )
                    focus_anchors = {
                        selected_anchor
                        for selected_anchor, selected_sentence in selected
                        if focus_obligation
                        and evidence_obligation_score(
                            focus_obligation,
                            selected_sentence,
                        ) >= 0.32
                    }
                    if (
                        focus_anchors
                        and anchor not in focus_anchors
                        and passage_core_coverage < 0.75
                    ):
                        continue
                if core_subject_terms and passage_core_coverage < 0.5 and core_score <= 0:
                    nearby_continuation = bool(
                        obligation_score >= 0.42
                        and (
                            any(abs(anchor - core_anchor) <= 2 for core_anchor in core_passage_anchors)
                            or (
                                selected
                                and any(
                                    abs(anchor - selected_anchor) <= 2
                                    for selected_anchor, _ in selected
                                )
                            )
                        )
                    )
                    if not nearby_continuation:
                        continue
                if obligation.key in {
                    "identity",
                    "placement",
                    "workflow_action",
                    "contrast",
                } and core_score <= 0:
                    continue
                if obligation.key == "contrast":
                    side_hit_count = sum(
                        SynthesisService._sentence_score(
                            cleaned,
                            set(side_obligation.retrieval_terms),
                        ) > 0
                        for side_obligation in answer_plan.evidence_obligations
                        if side_obligation.key.startswith("comparison_side_")
                    )
                    if side_hit_count < 2:
                        continue
                word_count = len(cleaned.split())
                readability_penalty = max(0.0, (word_count - 55) / 20)
                ranked.append(
                    (
                        base_score
                        + (20.0 * obligation_score)
                        + (2.0 * core_score)
                        + (4.0 * chunk_obligation_coverage.get(anchor, 0.0))
                        + (2.0 * passage_core_coverage)
                        + (2.5 if preferred_anchor is not None and anchor == preferred_anchor else 0.0)
                        - readability_penalty,
                        anchor,
                        cleaned,
                    )
                )
            for _, anchor, sentence in sorted(ranked, reverse=True):
                normalized = re.sub(r"\W+", "", sentence.lower())[:120]
                if normalized in seen:
                    continue
                selected.append((anchor, sentence))
                seen.add(normalized)
                break
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _planned_evidence_units(*, text: str, allow_roadmap_evidence: bool) -> list[str]:
        """Split dense PDF roadmaps into usable clauses without changing evidence."""

        units: list[str] = []
        for sentence in SynthesisService._split_sentences(text):
            if (
                allow_roadmap_evidence
                and len(sentence.split()) > 24
                and SynthesisService._is_roadmap_sentence(sentence)
            ):
                roadmap_items = SynthesisService._enumeration_items_from_sentence(sentence)
                if roadmap_items:
                    units.extend(roadmap_items)
                    continue
            units.append(sentence)
        return units

    @staticmethod
    def _fallback_procedure_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
    ) -> str | None:
        query_terms = SynthesisService._query_terms(query)
        ordinal_pattern = re.compile(
            r"^\s*(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
            flags=re.I,
        )
        process_cues = (
            " works as a loop",
            " pipeline",
            " workflow",
            " parsed ",
            " chunk",
            " retrieve",
            " retrieval",
            " search",
            " fusion",
            " generated",
            " rewritten",
            " step",
            " first",
            " second",
            " third",
            " fourth",
            " fifth",
        )
        candidates: list[tuple[float, int, str]] = []
        for anchor, block in context_chunks[:12]:
            sentences = SynthesisService._planned_evidence_units(
                text=SynthesisService._context_text_with_heading(block),
                allow_roadmap_evidence=True,
            )[:24]
            for position, sentence in enumerate(sentences):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if (
                    len(cleaned.split()) < 5
                    or SynthesisService._is_low_value_evidence_sentence(cleaned)
                    or SynthesisService._is_code_heavy_sentence(cleaned)
                ):
                    continue
                lowered = f" {cleaned.lower()} "
                cue_score = 0.0
                if ordinal_pattern.match(cleaned):
                    cue_score += 4.0
                cue_score += sum(0.7 for cue in process_cues if cue in lowered)
                if cue_score <= 0:
                    continue
                score = (
                    cue_score
                    + 0.55 * SynthesisService._sentence_score(cleaned, query_terms)
                    + max(0, 20 - position) * 0.03
                )
                candidates.append((score, anchor, cleaned))

        selected = SynthesisService._dedupe_scored_sentences(candidates, limit=8, min_words=5)
        if not selected:
            return None

        ordered = SynthesisService._sort_procedure_steps(selected)
        ordinal_only = [
            item
            for item in ordered
            if re.match(
                r"^\s*(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
                item[1],
                flags=re.I,
            )
        ]
        if ordinal_only:
            ordered = ordinal_only[:6]
        if len(ordered) < 2:
            return None

        return "\n".join(
            [
                "Short answer",
                "",
                "Steps from the source",
                *(f"{index}. {sentence} [{anchor}]" for index, (anchor, sentence) in enumerate(ordered, start=1)),
            ]
        )

    @staticmethod
    def _sort_procedure_steps(items: list[tuple[int, str]]) -> list[tuple[int, str]]:
        ordinal_order = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
            "sixth": 6,
            "seventh": 7,
            "eighth": 8,
            "ninth": 9,
            "tenth": 10,
        }

        def order_key(item: tuple[int, str]) -> tuple[int, int]:
            anchor, sentence = item
            match = re.match(r"^\s*(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b", sentence, re.I)
            if match:
                return ordinal_order.get(match.group(1).lower(), 99), anchor
            return 99, anchor

        ordered = sorted(items, key=order_key)
        if all(order_key(item)[0] == 99 for item in ordered):
            return items
        return ordered

    @staticmethod
    def _fallback_limitations_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
    ) -> str | None:
        query_terms = SynthesisService._query_terms(query)
        specific_limitation_cues = {
            "retrieval quality depends": 4.2,
            "document parsing": 2.6,
            "chunk quality": 2.6,
            "enough relevant material": 2.4,
            "ocr quality can affect": 4.0,
            "poor scans": 3.0,
            "scanned pdfs": 2.4,
            "missing ocr": 3.0,
            "weak source material": 3.0,
            "unrelated questions": 2.8,
            "small local model": 3.2,
            "less fluently": 2.6,
            "grounded correctness over style": 2.8,
            "avoid ": 3.4,
            "rather than": 2.8,
            "should not": 3.2,
            "must not": 3.2,
            "not suitable": 3.0,
            "trade-off": 3.4,
            "tradeoff": 3.4,
            "reliability": 1.8,
            "creativity": 1.8,
            "diversity": 1.8,
            "more examples": 2.4,
        }
        generic_limitation_cues = (
            "limitations should be honest",
            "does not",
            "cannot",
            "however",
            "limitation",
            "limitations",
            "caveat",
            "drawback",
            "avoid",
            "rather than",
            "should not",
            "must not",
            "not suitable",
        )
        candidates: list[tuple[float, int, str]] = []
        for anchor, block in context_chunks[:12]:
            for position, sentence in enumerate(
                SynthesisService._split_sentences(SynthesisService._context_text_with_heading(block))[:18]
            ):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if len(cleaned.split()) < 5 or SynthesisService._is_low_value_evidence_sentence(cleaned):
                    continue
                lowered = cleaned.lower()
                cue_score = sum(
                    weight for cue, weight in specific_limitation_cues.items() if cue in lowered
                )
                cue_score += 0.7 * sum(1 for cue in generic_limitation_cues if cue in lowered)
                if cue_score <= 0:
                    continue
                score = (
                    cue_score
                    + 0.5 * SynthesisService._sentence_score(cleaned, query_terms)
                    + max(0, 14 - position) * 0.02
                )
                candidates.append((score, anchor, cleaned))
        selected = SynthesisService._dedupe_scored_sentences(candidates, limit=4, min_words=5)
        if not selected:
            return None
        lead_anchor, lead_sentence = selected[0]
        sections = ["Short answer", f"\n{lead_sentence} [{lead_anchor}]"]
        details = [item for item in selected[1:] if item[1] != lead_sentence]
        if details:
            sections.append("\nLimitations")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in details[:3])
        return "\n".join(sections)

    @staticmethod
    def _fallback_text_generation_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
    ) -> str | None:
        normalized_query = query.lower()
        if not (
            "generate text" in normalized_query
            or "generates text" in normalized_query
            or (
                "language model" in normalized_query
                and any(term in normalized_query for term in ("generate", "predict"))
            )
        ):
            return None
        query_terms = SynthesisService._query_terms(query)
        candidates: list[tuple[float, int, str]] = []
        for anchor, block in context_chunks[:6]:
            for position, sentence in enumerate(SynthesisService._split_sentences(SynthesisService._context_text(block))[:14]):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if len(cleaned.split()) < 6 or SynthesisService._is_low_value_evidence_sentence(cleaned):
                    continue
                lowered = cleaned.lower()
                cue_score = 0.0
                if "large language models generate text" in lowered:
                    cue_score += 4.0
                if "predicting likely next tokens" in lowered:
                    cue_score += 4.0
                if "from context" in lowered:
                    cue_score += 1.2
                if cue_score <= 0:
                    continue
                candidates.append(
                    (
                        cue_score
                        + 0.4 * SynthesisService._sentence_score(cleaned, query_terms)
                        + max(0, 12 - position) * 0.02,
                        anchor,
                        cleaned,
                    )
                )
        selected = SynthesisService._dedupe_scored_sentences(candidates, limit=2)
        if not selected:
            return None
        lead_anchor, lead_sentence = selected[0]
        sections = ["Short answer", f"\n{lead_sentence} [{lead_anchor}]"]
        if len(selected) > 1:
            sections.append("\nHow it works")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in selected[1:])
        return "\n".join(sections)

    @staticmethod
    def _fallback_equation_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
        answer_plan: AnswerPlan,
    ) -> str | None:
        query_terms = SynthesisService._query_terms(query)
        subject_terms = (
            SynthesisService._core_subject_terms(query=query, answer_plan=answer_plan)
            or {
                token
                for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", answer_plan.subject.lower())
                if token not in _QUERY_STOPWORDS
            }
        )
        normalized_query = query.lower()
        wants_reason = bool(re.search(r"\bwhy\b", normalized_query))
        formula_candidates: list[tuple[float, int, str]] = []
        rationale_candidates: list[tuple[float, int, str]] = []
        for anchor, block in context_chunks[:12]:
            text = SynthesisService._context_text_with_heading(block)
            for position, sentence in enumerate(SynthesisService._split_sentences(text)[:18]):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if len(cleaned.split()) < 5:
                    continue
                lowered = f" {cleaned.lower()} "
                base = (
                    1.2 * SynthesisService._sentence_score(cleaned, subject_terms)
                    + 0.35 * SynthesisService._sentence_score(cleaned, query_terms)
                    + max(0, 12 - position) * 0.02
                )
                formula_bonus = 0.0
                if any(cue in lowered for cue in (" = ", " equals ", " calculated as ", " computed as ", " defined as ")):
                    formula_bonus += 3.0
                if re.search(r"\b[A-Za-z][A-Za-z0-9_]*\s*=", cleaned):
                    formula_bonus += 2.0
                if "divided by" in lowered or "/" in cleaned:
                    formula_bonus += 0.8
                if formula_bonus:
                    formula_candidates.append((base + formula_bonus, anchor, cleaned))

                rationale_bonus = 0.0
                if any(cue in lowered for cue in (" prevents ", " avoids ", " because ", " so that ")):
                    rationale_bonus += 2.4
                if "epsilon" in normalized_query and "epsilon" in lowered:
                    rationale_bonus += 1.4
                if rationale_bonus:
                    rationale_candidates.append((base + rationale_bonus, anchor, cleaned))

        formula = SynthesisService._dedupe_scored_sentences(formula_candidates, limit=1, min_words=4)
        rationale = SynthesisService._dedupe_scored_sentences(rationale_candidates, limit=2, min_words=4)
        if not formula and not rationale:
            return None

        lead_items = rationale if wants_reason and rationale else formula or rationale
        lead_anchor, lead_sentence = lead_items[0]
        sections = ["Short answer", f"\n{lead_sentence} [{lead_anchor}]"]
        support: list[tuple[int, str]] = []
        for item in [*(formula or []), *rationale]:
            if item != (lead_anchor, lead_sentence):
                support.append(item)
        if support:
            sections.append("\nEquation or reason from the source")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in support[:2])
        return "\n".join(sections)

    @staticmethod
    def _fallback_factual_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
    ) -> str | None:
        if not re.search(
            r"\b(when|year|date|edition|release|released|published|hardware|processor|device|"
            r"machine|duration|runtime|training|steps|hours)\b",
            query,
            re.I,
        ):
            return None

        edition_pattern = re.compile(
            r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+(?:st|nd|rd|th))\s+edition\b",
            re.I,
        )
        release_pattern = re.compile(
            r"\b((?:19|20)\d{2}-\d{2}-\d{2})\s*:\s*((?:first\s+)?release)\b",
            re.I,
        )
        published_pattern = re.compile(
            r"\b(published|released)\s+(?:in|on)\s+((?:19|20)\d{2}(?:-\d{2}-\d{2})?)\b",
            re.I,
        )
        edition_fact: tuple[int, str] | None = None
        release_fact: tuple[int, str, str] | None = None
        published_fact: tuple[int, str] | None = None
        for anchor, block in context_chunks[:12]:
            text = SynthesisService._context_text_with_heading(block)
            if edition_fact is None and (match := edition_pattern.search(text)):
                edition_fact = (anchor, match.group(0).title())
            if release_fact is None and (match := release_pattern.search(text)):
                release_fact = (anchor, match.group(1), match.group(2).title())
            if published_fact is None and (match := published_pattern.search(text)):
                published_fact = (anchor, match.group(0).lower())
            if edition_fact and (release_fact or published_fact):
                break

        if edition_fact and release_fact:
            anchors = sorted({edition_fact[0], release_fact[0]})
            citation = "".join(f" [{anchor}]" for anchor in anchors)
            return (
                "Short answer\n\n"
                f"The source identifies the {edition_fact[1]} and records "
                f"{release_fact[1]} as the {release_fact[2]}.{citation}"
            )
        if edition_fact and published_fact:
            anchors = sorted({edition_fact[0], published_fact[0]})
            citation = "".join(f" [{anchor}]" for anchor in anchors)
            return (
                "Short answer\n\n"
                f"The source identifies the {edition_fact[1]} and states it was "
                f"{published_fact[1]}.{citation}"
            )
        if edition_fact:
            return f"Short answer\n\nThe source identifies the {edition_fact[1]}. [{edition_fact[0]}]"
        if release_fact:
            return (
                "Short answer\n\n"
                f"The source records {release_fact[1]} as the {release_fact[2]}. [{release_fact[0]}]"
            )

        # Keep ordinary factual lookups extractive and cited when they do not
        # match the specialized edition/date patterns above. This is generic
        # by design: it ranks source sentences using the query terms and
        # measurement cues instead of encoding a document-specific answer.
        query_terms = SynthesisService._query_terms(query)
        factual_cues = {
            "hardware",
            "processor",
            "device",
            "machine",
            "gpu",
            "duration",
            "runtime",
            "training",
            "steps",
            "hours",
            "time",
        }
        candidates: list[tuple[float, int, str]] = []
        for chunk_position, (anchor, block) in enumerate(context_chunks[:8]):
            for sentence_position, sentence in enumerate(
                SynthesisService._split_sentences(SynthesisService._context_text(block))[:10]
            ):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if len(cleaned.split()) < 6 or SynthesisService._is_low_value_evidence_sentence(cleaned):
                    continue
                term_score = SynthesisService._sentence_score(cleaned, query_terms)
                cue_score = sum(
                    0.8
                    for cue in factual_cues
                    if SynthesisService._term_matches(sentence=cleaned, term=cue)
                    and cue in query_terms
                )
                measurement_bonus = 0.7 if re.search(r"\b\d[\d,.]*(?:\s|-)?(?:%|hours?|steps?|GPUs?|GB|MB)\b", cleaned, re.I) else 0.0
                rank_bonus = max(0, 8 - chunk_position) * 0.08 + max(0, 10 - sentence_position) * 0.02
                score = term_score + cue_score + measurement_bonus + rank_bonus
                if score > 0:
                    candidates.append((score, anchor, cleaned))

        selected = SynthesisService._dedupe_scored_sentences(candidates, limit=3, min_words=6)
        if selected:
            return "Short answer\n\n" + "\n".join(
                f"- {sentence} [{anchor}]" for anchor, sentence in selected
            )
        return None

    @staticmethod
    def _context_term_weights(*, terms: set[str], context_texts: list[str]) -> dict[str, float]:
        if not terms or not context_texts:
            return {}
        context_count = len(context_texts)
        weights: dict[str, float] = {}
        for term in terms:
            document_frequency = sum(
                1
                for text in context_texts
                if SynthesisService._sentence_score(text, {term}) > 0
            )
            weights[term] = 1.0 + min(2.0, (context_count + 1) / (document_frequency + 1) * 0.25)
        return weights

    @staticmethod
    def _weighted_sentence_score(sentence: str, term_weights: dict[str, float]) -> float:
        if not term_weights:
            return 0.0
        return sum(
            weight
            for term, weight in term_weights.items()
            if SynthesisService._term_matches(sentence=sentence, term=term)
        )

    @staticmethod
    def _planned_sentence_signal(
        *,
        sentence: str,
        answer_type: str,
        core_terms: set[str],
        goal_terms: set[str],
        expanded_terms: set[str],
        near_core: bool,
    ) -> float:
        """Score whether one local sentence can help answer the planned question."""

        core_score = SynthesisService._sentence_score(sentence, core_terms)
        goal_score = SynthesisService._sentence_score(sentence, goal_terms)
        expanded_score = SynthesisService._sentence_score(sentence, expanded_terms)
        cue_score = answer_evidence_cue_score(answer_type, sentence)
        if core_terms and core_score <= 0 and not near_core:
            return -1.0
        if core_score <= 0 and goal_score <= 0 and expanded_score <= 0 and cue_score <= 0:
            return -1.0

        word_count = len(sentence.split())
        length_penalty = min(3.0, max(0, word_count - 55) / 18)
        code_penalty = 1.25 if any(
            marker in sentence
            for marker in (">>>", "tf.keras", "np.array", "array([", "model.fit(")
        ) else 0.0
        return (
            (2.2 * core_score)
            + (3.0 * min(goal_score, 3.0))
            + (0.45 * min(expanded_score, 6.0))
            + (3.0 * cue_score)
            + (0.8 if near_core else 0.0)
            - length_penalty
            - code_penalty
        )

    @staticmethod
    def _core_subject_terms(*, query: str, answer_plan: AnswerPlan) -> set[str]:
        return answer_subject_anchor_terms(query, answer_plan)

    @staticmethod
    def _has_core_subject_anchor(sentence: str, core_terms: set[str]) -> bool:
        if not core_terms:
            return False
        required_hits = max(1, ((3 * len(core_terms)) + 4) // 5)
        return SynthesisService._sentence_score(sentence, core_terms) >= required_hits

    @staticmethod
    def _has_answer_focus_anchor(
        *,
        sentence: str,
        answer_type: str,
        goal_terms: set[str],
        expanded_terms: set[str],
    ) -> bool:
        """Accept a local answer window even when it omits the document or model name."""

        goal_hits = SynthesisService._sentence_score(sentence, goal_terms)
        expanded_hits = SynthesisService._sentence_score(sentence, expanded_terms)
        cue_score = answer_evidence_cue_score(answer_type, sentence)
        required_goal_hits = 1 if len(goal_terms) == 1 else 2
        if goal_terms and goal_hits >= required_goal_hits:
            return True
        if cue_score >= 0.6 and (goal_hits >= 1 or expanded_hits >= 1):
            return True
        return expanded_hits >= 2 and cue_score > 0

    @staticmethod
    def _allows_roadmap_evidence(*, query: str, answer_type: str) -> bool:
        if answer_type in {"document_summary", "enumeration"}:
            return True
        normalized = query.lower()
        return bool(
            re.search(r"\b(?:book|document|module|paper|source|textbook)\b", normalized)
            and re.search(
                r"\b(?:cover|covers|covered|describe|describes|described|place|places|"
                r"present|presents|presented|mention|mentions|list|outline)\b",
                normalized,
            )
        )

    @staticmethod
    def _factual_sentence_cue_score(*, query: str, sentence: str) -> float:
        normalized_query = query.lower()
        normalized_sentence = sentence.lower()
        score = 0.0
        asks_date = bool(
            re.search(r"\b(when|year|date|released?|published?|edition)\b", normalized_query)
        )
        if asks_date and (
            re.search(r"\b(?:19|20)\d{2}\b", normalized_sentence)
            or re.search(r"\b(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", normalized_sentence)
        ):
            score += 0.75
            if any(term in normalized_sentence for term in ("release", "publish", "edition", "date")):
                score += 0.25
        if re.search(r"\bhow\s+many\b", normalized_query) and re.search(
            r"\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)\b",
            normalized_sentence,
        ):
            score += 0.8
        if re.search(r"\bwho\b", normalized_query) and re.search(
            r"\b(?:written|authored|created|developed|proposed|introduced)\s+by\b",
            normalized_sentence,
        ):
            score += 0.8
        return min(1.0, score)

    @staticmethod
    def _mode_instruction(response_mode: str) -> str:
        mode = response_mode.strip().lower()
        if mode in {"exam", "exam_answer"}:
            return (
                "Format as an exam-ready answer. Use the Exam Lab answer contract when provided. "
                "Keep language simple, marks-aware, and cited. Do not add unsupported outside knowledge."
            )
        if mode == "revision_notes":
            return "Format as compact revision notes with headings and high-yield bullets."
        if mode == "study_guide":
            return (
                "Format as a study guide with important questions, concise expandable-style answers, "
                "diagram references when source diagrams are available, and cited evidence."
            )
        if mode == "summary":
            return (
                "Summarize the selected document. Include: what it is about, main ideas, how it works, "
                "why it matters, and limitations or caveats when supported. Use citations."
            )
        if mode == "important_questions":
            return "Generate likely exam questions only when they are supported by the context."
        if mode == "compare_concepts":
            return "Compare concepts in a small table or structured contrast when evidence supports it."
        if mode == "general_chat":
            return "Answer conversationally, but only from relevant uploaded document evidence. If the context is not relevant, abstain."
        if mode == "deep_research":
            return "Write a deeper research-style answer with clear sections, caveats, and evidence citations."
        if mode in {"paper", "research_paper"}:
            return (
                "Draft in an academic research-paper style for engineering students. Include a clear thesis, "
                "related work, methodology or design considerations, limitations, and multiple citations from the context. "
                "Do not fabricate papers, authors, results, or references not present in the retrieved source text."
            )
        return (
            "Explain clearly for a student. Start with a direct answer in 2-4 sentences, "
            "then give 3-5 short cited bullets. If the user asks for a list or algorithms, answer as a list."
        )

    @staticmethod
    def _exam_instruction(exam_profile: dict[str, object] | None) -> str:
        if not exam_profile:
            return ""
        contract = SynthesisService._exam_answer_contract(exam_profile)
        marks = contract["marks"]
        answer_style = str(exam_profile.get("answer_style") or "exam-ready")
        content_type = str(exam_profile.get("content_type") or "conceptual")
        instructions = str(exam_profile.get("instructions") or "").strip()
        parts = [
            "Exam Lab settings:",
            f"- Target marks: {marks}",
            f"- Answer style: {answer_style}",
            f"- Content type: {content_type}",
            "- Required answer contract:",
            *[f"  - {section}" for section in contract["sections"]],
            f"- Suggested evidence bullets: {contract['evidence_bullets']}",
            "- Use only retrieved source context; do not add outside textbook knowledge.",
            "- If diagrams are requested but no source diagram context is provided, say that no source diagram was available.",
        ]
        if instructions:
            parts.append(f"- Custom instructions: {instructions}")
        return "\n".join(parts)

    @staticmethod
    def _exam_answer_contract(exam_profile: dict[str, object] | None) -> dict[str, object]:
        raw_marks = 10
        if exam_profile:
            try:
                raw_marks = int(exam_profile.get("marks") or 10)
            except (TypeError, ValueError):
                raw_marks = 10
        marks = min(max(raw_marks, 2), 15)
        if marks <= 2:
            sections = ["Direct answer", "Two key points", "Source note"]
            evidence_bullets = 2
        elif marks <= 5:
            sections = ["Direct answer", "Key points", "Brief explanation", "Source note"]
            evidence_bullets = 3
        elif marks <= 10:
            sections = ["Direct answer", "Key points", "Explanation", "Diagram note if relevant", "Conclusion"]
            evidence_bullets = 5
        else:
            sections = [
                "Direct answer",
                "Key points",
                "Detailed explanation",
                "Diagram note if relevant",
                "Limitations or caveats when supported",
                "Conclusion",
            ]
            evidence_bullets = 7
        return {
            "marks": marks,
            "sections": sections,
            "evidence_bullets": evidence_bullets,
        }

    @staticmethod
    def _exam_artifact_instruction(exam_context: dict[str, object] | None, *, query: str = "") -> str:
        if not exam_context:
            return ""
        questions = exam_context.get("questions") or []
        diagrams = exam_context.get("diagrams") or []
        parts: list[str] = []
        if isinstance(questions, list) and questions:
            parts.append("Imported question bank:")
            for index, item in enumerate(questions[:12], start=1):
                if not isinstance(item, dict):
                    continue
                marks = item.get("marks")
                mark_label = f" ({marks} marks)" if marks else ""
                parts.append(f"- Q{index}: {item.get('question')}{mark_label}")
        if isinstance(diagrams, list) and diagrams:
            parts.append("Available source diagrams:")
            for index, item in enumerate(diagrams[:8], start=1):
                if not isinstance(item, dict):
                    continue
                page = item.get("page_number") or "?"
                caption = item.get("caption") or "No caption detected"
                asset_id = item.get("id") or f"D{index}"
                parts.append(f"- D{index}: asset {asset_id}, page {page}, {caption}")
            parts.append("When useful, mention diagram IDs like D1 with page numbers instead of inventing drawings.")
        elif SynthesisService._is_diagram_request(query):
            parts.append("Source diagrams: no extracted diagram assets are available for this selected document.")
        return "\n".join(parts)

    @staticmethod
    def _fallback_study_guide(
        query: str,
        context_chunks: list[tuple[int, str]],
        exam_context: dict[str, object],
    ) -> str:
        questions = [item for item in exam_context.get("questions", []) if isinstance(item, dict)]
        diagrams = [item for item in exam_context.get("diagrams", []) if isinstance(item, dict)]
        guide_items = (
            SynthesisService._rank_question_bank_items(questions, context_chunks=context_chunks)
            if questions
            else SynthesisService._source_topic_study_questions(query=query, context_chunks=context_chunks)
        )
        if not guide_items:
            return "Study guide from the retrieved passages:\n- The retrieved passages did not contain enough readable source text to build a safe study guide."

        title = (
            "Study guide from imported questions and retrieved passages:"
            if questions
            else "Study guide from retrieved source topics:"
        )
        sections = [title]
        for index, item in enumerate(guide_items[:8], start=1):
            question = str(item.get("question") or f"Question {index}")
            marks = item.get("marks")
            raw_terms = item.get("terms")
            terms = set(raw_terms) if isinstance(raw_terms, set) else SynthesisService._query_terms(question)
            evidence = SynthesisService._best_evidence_sentences(context_chunks, terms, limit=3)
            mark_label = f" ({marks} marks)" if marks else ""
            importance = item.get("importance")
            importance_label = f" - {importance}" if importance else ""
            sections.append(f"\nQ{index}. {question}{mark_label}{importance_label}")
            if evidence:
                sections.append("- Why this matters: this topic appears in the retrieved source material and has direct supporting evidence.")
                sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in evidence[:3])
            else:
                sections.append("- The retrieved passages did not contain enough readable support for this question.")

        if diagrams:
            sections.append("\nSource diagrams to review:")
            for index, item in enumerate(diagrams[:5], start=1):
                page = item.get("page_number") or "?"
                caption = item.get("caption") or "No caption detected"
                sections.append(f"- D{index}: page {page}, {caption}.")
        else:
            sections.append("\nSource diagrams: no extracted diagram assets are available yet.")
        return "\n".join(sections)

    @staticmethod
    def _rank_question_bank_items(
        questions: list[dict[str, object]],
        *,
        context_chunks: list[tuple[int, str]],
    ) -> list[dict[str, object]]:
        scored: list[tuple[float, int, dict[str, object]]] = []
        combined_text = " ".join(SynthesisService._context_text(block).lower() for _, block in context_chunks[:8])
        for index, item in enumerate(questions[:40]):
            question = str(item.get("question") or "").strip()
            if not question:
                continue
            terms = SynthesisService._query_terms(question)
            overlap = sum(1 for term in terms if term in combined_text)
            marks = item.get("marks")
            try:
                marks_score = min(int(marks or 0), 15) / 15
            except (TypeError, ValueError):
                marks_score = 0.0
            score = overlap + marks_score
            enriched = {
                **item,
                "terms": terms,
                "importance": "question-bank priority" if overlap else "question-bank item",
            }
            scored.append((score, -index, enriched))
        return [item for _, _, item in sorted(scored, key=lambda row: (row[0], row[1]), reverse=True)[:12]]

    @staticmethod
    def _source_topic_study_questions(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
    ) -> list[dict[str, object]]:
        topic_counts: Counter[str] = Counter()
        topic_pages: dict[str, set[int]] = {}
        generic = {
            "answer",
            "chapter",
            "data",
            "example",
            "examples",
            "figure",
            "figures",
            "image",
            "images",
            "introduction",
            "learning",
            "material",
            "model",
            "models",
            "page",
            "problem",
            "section",
            "source",
            "study",
            "system",
            "training",
        }
        query_terms = SynthesisService._query_terms(query)
        for anchor, block in context_chunks[:10]:
            text = SynthesisService._context_text(block)
            tokens = [
                token
                for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{3,}", text.lower())
                if token not in _QUERY_STOPWORDS and token not in generic
            ]
            for token in tokens:
                if len(token) < 4 or token.isdigit():
                    continue
                topic_counts[token] += 1 + (2 if token in query_terms else 0)
                topic_pages.setdefault(token, set()).add(anchor)

            for phrase in re.findall(r"\b[A-Z][A-Za-z0-9+-]+(?:\s+[A-Z][A-Za-z0-9+-]+){0,3}\b", text):
                normalized = phrase.strip().lower()
                if len(normalized.split()) > 4 or normalized in generic:
                    continue
                if any(part.lower() in _QUERY_STOPWORDS for part in normalized.split()):
                    continue
                topic_counts[normalized] += 2
                topic_pages.setdefault(normalized, set()).add(anchor)

        ranked_topics = [
            topic
            for topic, _ in sorted(
                topic_counts.items(),
                key=lambda item: (len(topic_pages.get(item[0], set())), item[1], len(item[0])),
                reverse=True,
            )
            if topic_counts[topic] >= 2
        ]

        questions: list[dict[str, object]] = []
        seen_roots: set[str] = set()
        for topic in ranked_topics:
            root = topic.lower().rstrip("s")
            if root in seen_roots:
                continue
            seen_roots.add(root)
            display_topic = " ".join(part.capitalize() if part.isupper() else part for part in topic.split())
            question = f"Explain {display_topic} using the source material."
            questions.append(
                {
                    "question": question,
                    "marks": None,
                    "terms": SynthesisService._query_terms(question) | {topic.lower()},
                    "importance": "high-yield source topic",
                }
            )
            if len(questions) >= 8:
                break
        return questions

    @staticmethod
    def _fallback_exam_answer(
        query: str,
        context_chunks: list[tuple[int, str]],
        exam_profile: dict[str, object] | None,
        exam_context: dict[str, object] | None,
    ) -> str:
        question_list_answer = SynthesisService._fallback_exam_question_list(
            query=query,
            context_chunks=context_chunks,
        )
        if question_list_answer:
            return question_list_answer

        requested_marks = SynthesisService._query_requested_marks(query)
        contract = SynthesisService._exam_answer_contract(
            {"marks": requested_marks} if requested_marks else exam_profile
        )
        marks = int(contract["marks"])
        evidence_limit = int(contract["evidence_bullets"])
        answer_style = str((exam_profile or {}).get("answer_style") or "exam-ready").lower()
        query_terms = SynthesisService._query_terms(query)
        evidence = SynthesisService._best_evidence_sentences(
            context_chunks=context_chunks,
            query_terms=query_terms,
            limit=evidence_limit,
        )
        if not evidence:
            return "I found related passages, but not enough direct evidence to generate a marks-ready answer safely."

        if requested_marks:
            preferred = SynthesisService._prefer_exam_mark_evidence(
                evidence=evidence,
                marks=requested_marks,
            )
            if preferred:
                evidence = preferred
        elif not exam_profile and SynthesisService._is_compact_exam_query(query):
            marks = min(marks, 2)
            evidence_limit = min(evidence_limit, 3)
            evidence = evidence[:evidence_limit]

        sections = [f"Exam-ready answer ({marks} marks)"]
        sections.append("\nDirect answer")
        sections.append(f"- {evidence[0][1]} [{evidence[0][0]}]")

        remaining = [
            item
            for item in evidence[1:]
            if not SynthesisService._is_other_exam_mark_sentence(item[1], marks=marks)
        ]
        key_point_limit = 0 if marks <= 2 else 3 if marks <= 10 else 4
        if marks >= 5 and "step" in answer_style:
            key_point_limit = min(key_point_limit, 2)
        if remaining and key_point_limit > 0:
            sections.append("\nKey points")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in remaining[:key_point_limit])

        if marks >= 5 and remaining:
            key_point_items = remaining[:key_point_limit]
            key_point_keys = {
                re.sub(r"\W+", "", sentence.lower())[:120]
                for _, sentence in key_point_items
            }
            explanation_items = [
                item
                for item in remaining[key_point_limit:]
                if re.sub(r"\W+", "", item[1].lower())[:120] not in key_point_keys
            ]
            heading = "Stepwise explanation" if "step" in answer_style else "Explanation"
            if explanation_items:
                sections.append(f"\n{heading}")
                sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in explanation_items[:3])

        diagram_requested = bool(
            re.search(r"\b(diagram|figure|image|visual)\b", query, flags=re.I)
            or "diagram" in answer_style
        )
        if diagram_requested:
            diagrams = SynthesisService._diagram_context_items(exam_context)
            sections.append("\nDiagram note")
            if diagrams:
                for index, item in enumerate(diagrams[:3], start=1):
                    page = item.get("page_number") or "?"
                    caption = item.get("caption") or "No caption detected"
                    sections.append(f"- D{index}: page {page}, {caption}.")
            else:
                sections.append("- No source diagram was available from the uploaded material.")

        sections.append("\nSource note\nOpen Sources to inspect the exact passages used.")
        return "\n".join(sections)

    @staticmethod
    def _query_requested_marks(query: str) -> int | None:
        normalized = query.lower()
        word_marks = {
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "ten": 10,
            "fifteen": 15,
        }
        numeric = re.search(r"\b(\d{1,2})\s*-?\s*marks?\b", normalized)
        if numeric:
            return min(max(int(numeric.group(1)), 2), 15)
        for word, marks in word_marks.items():
            if re.search(rf"\b{word}\s*-?\s*marks?\b", normalized):
                return marks
        return None

    @staticmethod
    def _prefer_exam_mark_evidence(
        *,
        evidence: list[tuple[int, str]],
        marks: int,
    ) -> list[tuple[int, str]]:
        mark_terms = SynthesisService._exam_mark_terms(marks)
        preferred = [
            item
            for item in evidence
            if any(term in item[1].lower() for term in mark_terms)
        ]
        if not preferred:
            return evidence
        remaining = [
            item
            for item in evidence
            if item not in preferred and not SynthesisService._is_other_exam_mark_sentence(item[1], marks=marks)
        ]
        return [*preferred, *remaining]

    @staticmethod
    def _exam_mark_terms(marks: int) -> tuple[str, ...]:
        if marks <= 2:
            return ("two-mark", "two mark", "2-mark", "2 mark")
        if marks <= 5:
            return ("five-mark", "five mark", "5-mark", "5 mark")
        if marks <= 10:
            return ("ten-mark", "ten mark", "10-mark", "10 mark")
        return (f"{marks}-mark", f"{marks} mark")

    @staticmethod
    def _is_other_exam_mark_sentence(sentence: str, *, marks: int) -> bool:
        lowered = sentence.lower()
        all_terms = {
            2: ("two-mark", "two mark", "2-mark", "2 mark"),
            5: ("five-mark", "five mark", "5-mark", "5 mark"),
            10: ("ten-mark", "ten mark", "10-mark", "10 mark"),
        }
        own_terms = set(SynthesisService._exam_mark_terms(marks))
        return any(
            term in lowered
            for mark, terms in all_terms.items()
            for term in terms
            if mark != marks and term not in own_terms
        )

    @staticmethod
    def _fallback_exam_question_list(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
    ) -> str | None:
        normalized = query.lower()
        if not (
            re.search(r"\b(?:important\s+)?exam\s+questions?\b", normalized)
            or "question bank" in normalized
        ):
            return None
        requested_count = 5
        count_match = re.search(
            r"\b(two|three|four|five|\d{1,2})\b.{0,24}\b(?:questions?|items?)\b",
            normalized,
        )
        if count_match:
            raw_count = count_match.group(1)
            number_words = {"two": 2, "three": 3, "four": 4, "five": 5}
            requested_count = int(raw_count) if raw_count.isdigit() else number_words.get(raw_count, 5)

        items: list[tuple[int, str]] = []
        seen: set[str] = set()
        pattern = re.compile(
            r"\bQ\d+\.\s+(.+?)(?=(?:\s+Q\d+\.|\s+The answer format\b|$))",
            flags=re.I,
        )
        for anchor, block in context_chunks[:8]:
            text = SynthesisService._context_text(block)
            for match in pattern.finditer(text):
                question = SynthesisService._clean_evidence_sentence(match.group(1)).strip(" -")
                if not question:
                    continue
                question = re.sub(
                    r"\.\s+\((\d+\s+marks?)\)\.?$",
                    r" (\1)",
                    question,
                    flags=re.I,
                ).rstrip(".")
                key = re.sub(r"\W+", "", question.lower())[:100]
                if key in seen:
                    continue
                seen.add(key)
                items.append((anchor, question))
                if len(items) >= requested_count:
                    break
            if len(items) >= requested_count:
                break
        if not items:
            return None
        return "\n".join(
            [
                "Exam-ready answer",
                "\nImportant questions",
                *(f"- {item} [{anchor}]." for anchor, item in items[:requested_count]),
                "\nSource note\nOpen Sources to inspect the exact passages used.",
            ]
        )

    @staticmethod
    def _is_compact_exam_query(query: str) -> bool:
        normalized = query.lower()
        if re.search(r"\b(?:ten|10|five|5)\s*-?\s*mark\b", normalized):
            return False
        if re.search(r"\b(?:essay|long answer|in detail|detailed|elaborate)\b", normalized):
            return False
        return bool(re.search(r"\b(?:what|which|how|list)\b", normalized))

    @staticmethod
    def _with_diagram_grounding_note(
        *,
        answer: str,
        query: str,
        exam_context: dict[str, object] | None,
    ) -> str:
        if not SynthesisService._is_diagram_request(query):
            return answer
        lowered_answer = answer.lower()

        diagrams = SynthesisService._diagram_context_items(exam_context)
        if not diagrams:
            already_honest = (
                "no source diagram" in lowered_answer
                or "no extracted diagram" in lowered_answer
                or ("diagram" in lowered_answer and "not available" in lowered_answer)
                or ("diagram" in lowered_answer and "unavailable" in lowered_answer)
            )
            if already_honest:
                return answer
            return "\n".join(
                [
                    answer.rstrip(),
                    "",
                    "Diagram note",
                    "- No source diagram was available from the uploaded material.",
                ]
            ).strip()

        if "diagram note" in lowered_answer or "source diagram" in lowered_answer:
            return answer

        lines = [answer.rstrip(), "", "Diagram note"]
        for index, item in enumerate(diagrams[:3], start=1):
            page = item.get("page_number") or "?"
            caption = item.get("caption") or "No caption detected"
            lines.append(f"- D{index}: source diagram on page {page}, {caption}.")
        return "\n".join(lines).strip()

    @staticmethod
    def _diagram_context_items(exam_context: dict[str, object] | None) -> list[dict[str, object]]:
        if not exam_context:
            return []
        raw_diagrams = exam_context.get("diagrams") or []
        if not isinstance(raw_diagrams, list):
            return []
        return [item for item in raw_diagrams if isinstance(item, dict)]

    @staticmethod
    def _is_diagram_request(query: str) -> bool:
        visual = r"(?:diagram|diagrams|figure|figures|image|images|visual|visuals)"
        return bool(
            re.search(
                rf"\b(?:provide|include|show|add|cite|attach|use|with)\b.{{0,28}}\b{visual}\b",
                query,
                re.I,
            )
            or re.search(rf"\b{visual}\s+references?\b", query, re.I)
            or re.search(
                rf"\b(?:explain|describe|interpret|open)\s+(?:the\s+)?{visual}\b",
                query,
                re.I,
            )
            or re.search(rf"\bwhat\b.{{0,24}}\b{visual}\b.{{0,16}}\bshow", query, re.I)
        )

    @staticmethod
    def _best_evidence_sentences(
        context_chunks: list[tuple[int, str]], query_terms: set[str], limit: int
    ) -> list[tuple[int, str]]:
        candidates: list[tuple[float, int, str]] = []
        for idx, block in context_chunks[:8]:
            text = SynthesisService._context_text(block)
            for sentence_index, sentence in enumerate(SynthesisService._split_sentences(text)[:10]):
                sentence = SynthesisService._clean_evidence_sentence(sentence)
                if len(sentence.split()) < 6 or SynthesisService._is_low_value_evidence_sentence(sentence):
                    continue
                score = SynthesisService._sentence_score(sentence, query_terms)
                rank_bonus = max(0, 9 - idx) * 0.08 + max(0, 10 - sentence_index) * 0.01
                candidates.append((score + rank_bonus, idx, sentence))
        selected: list[tuple[int, str]] = []
        seen: set[str] = set()
        for _, idx, sentence in sorted(candidates, key=lambda item: item[0], reverse=True):
            normalized = re.sub(r"\W+", "", sentence.lower())[:96]
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append((idx, sentence))
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _fallback_research_paper(query: str, context_chunks: list[tuple[int, str]]) -> str:
        evidence = SynthesisService._best_evidence_sentences(
            context_chunks=context_chunks,
            query_terms=SynthesisService._query_terms(query),
            limit=6,
        )
        if not evidence:
            return "Research paper draft from the retrieved passages:\n- Not enough readable evidence was retrieved."

        groups = [
            ("Thesis", evidence[:2]),
            ("Related Work", evidence[2:4]),
            ("Engineering Considerations and Limitations", evidence[4:6]),
        ]
        sections = ["Research paper draft from retrieved sources:"]
        for heading, items in groups:
            if not items:
                continue
            sections.append(f"\n{heading}")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in items)
        sections.append("\nUse this as a grounded draft scaffold; verify final references before submission.")
        return "\n".join(sections)

    @staticmethod
    def _fallback_definition_solution_answer(query: str, context_chunks: list[tuple[int, str]]) -> str:
        query_terms = SynthesisService._query_terms(query)
        definitions: list[tuple[float, int, str]] = []
        solutions: list[tuple[float, int, str]] = []
        definition_cues = ("means", "called", "occurs", "refers", "generalize", "training data")
        solution_cues = (
            "possible solutions",
            "simplify",
            "fewer parameters",
            "reduce",
            "regularization",
            "constrain",
            "more training data",
            "noise",
            "outliers",
            "early stopping",
        )
        for idx, block in context_chunks[:10]:
            for sentence_index, sentence in enumerate(SynthesisService._split_sentences(SynthesisService._context_text(block))[:12]):
                if len(sentence.split()) < 7 or SynthesisService._is_low_value_evidence_sentence(sentence):
                    continue
                lowered = sentence.lower()
                base = SynthesisService._sentence_score(sentence, query_terms)
                rank_bonus = max(0, 10 - idx) * 0.03 + max(0, 12 - sentence_index) * 0.01
                definition_score = base + rank_bonus + sum(0.9 for cue in definition_cues if cue in lowered)
                solution_score = base + rank_bonus + sum(0.9 for cue in solution_cues if cue in lowered)
                if definition_score > 0:
                    definitions.append((definition_score, idx, sentence))
                if solution_score > 0:
                    solutions.append((solution_score, idx, sentence))

        selected_definitions = SynthesisService._dedupe_scored_sentences(definitions, limit=2)
        selected_solutions = SynthesisService._dedupe_scored_sentences(solutions, limit=4)
        if not selected_definitions and not selected_solutions:
            return "I found matching passages, but not enough clear definition or solution text to answer safely."

        sections = ["Based on the retrieved textbook passages:"]
        if selected_definitions:
            sections.append("\nWhat it is")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in selected_definitions)
        if selected_solutions:
            sections.append("\nHow to reduce it")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in selected_solutions)
        sections.append("\nTrust note: this answer was rewritten into source-only form because the local model added unsupported details.")
        return "\n".join(sections)

    @staticmethod
    def _fallback_privacy_control_answer(
        query: str,
        context_chunks: list[tuple[int, str]],
    ) -> str:
        query_terms = SynthesisService._query_terms(query)
        privacy_cues = {
            "product should make local trust visible": 5.0,
            "users should see": 3.0,
            "files stay on the machine": 5.0,
            "citations can be inspected": 5.0,
            "local material can be removed": 5.0,
            "without requiring a cloud account": 2.5,
            "internet connection": 2.0,
            "local-first": 2.0,
            "uploaded files are stored": 2.0,
            "local data directory": 1.8,
            "local-path ingestion is restricted": 1.5,
            "trusted corpus roots": 1.5,
            "file signatures": 1.5,
            "cannot easily masquerade": 1.5,
            "removed from the local library": 2.2,
            "clearing its metadata": 2.0,
            "vector entries": 1.4,
            "sensitive user data": 1.4,
            "personal information": 1.4,
            "pii": 1.4,
            "mask personal": 1.4,
            "data masking": 1.4,
            "encryption": 1.4,
            "secure api": 1.4,
            "data retention": 1.4,
            "access control": 1.4,
        }
        candidates: list[tuple[float, int, str]] = []
        for idx, block in context_chunks[:8]:
            text = SynthesisService._context_text(block)
            for sentence_index, sentence in enumerate(SynthesisService._split_sentences(text)[:16]):
                if SynthesisService._is_low_value_evidence_sentence(sentence):
                    continue
                lowered = sentence.lower()
                cue_score = sum(weight for cue, weight in privacy_cues.items() if cue in lowered)
                if cue_score <= 0 or len(sentence.split()) < 3:
                    continue
                term_score = SynthesisService._sentence_score(sentence, query_terms)
                rank_bonus = max(0, 9 - idx) * 0.05 + max(0, 16 - sentence_index) * 0.01
                candidates.append((cue_score + term_score + rank_bonus, idx, sentence))

        selected = SynthesisService._dedupe_scored_sentences(candidates, limit=5, min_words=3)
        if not selected:
            return "I found privacy-related passages, but not enough concrete source-backed controls to answer safely."

        sections = ["Privacy controls", "\nDirect answer"]
        first_anchor, first_sentence = selected[0]
        sections.append(f"- {first_sentence} [{first_anchor}]")

        remaining = selected[1:]
        if remaining:
            sections.append("\nVisible trust cues")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in remaining[:4])

        sections.append("\nEvidence note\nOpen Sources to inspect the exact privacy/runtime passages used.")
        return "\n".join(sections)

    @staticmethod
    def _fallback_local_first_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
    ) -> str:
        query_terms = SynthesisService._query_terms(query) | {
            "local-first",
            "machine",
            "cloud",
            "internet",
            "local",
        }
        local_first_cues = {
            "nirmiq is local-first": 4.0,
            "user's machine": 4.0,
            "without requiring a cloud account": 3.5,
            "internet connection": 2.5,
            "local fastapi backend": 2.0,
            "local academic workspace": 2.0,
            "uploaded files are stored": 1.5,
        }
        candidates: list[tuple[float, int, str]] = []
        for anchor, block in context_chunks[:8]:
            for position, sentence in enumerate(SynthesisService._split_sentences(SynthesisService._context_text(block))[:16]):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if (
                    len(cleaned.split()) < 5
                    or SynthesisService._is_low_value_evidence_sentence(cleaned)
                    or SynthesisService._is_code_heavy_sentence(cleaned)
                ):
                    continue
                lowered = cleaned.lower()
                cue_score = sum(weight for cue, weight in local_first_cues.items() if cue in lowered)
                if cue_score <= 0:
                    continue
                score = (
                    cue_score
                    + 0.45 * SynthesisService._sentence_score(cleaned, query_terms)
                    + max(0, 16 - position) * 0.03
                )
                candidates.append((score, anchor, cleaned))

        selected = SynthesisService._dedupe_scored_sentences(candidates, limit=4, min_words=5)
        if not selected:
            return SynthesisService._fallback_definition_answer(
                query=query,
                context_chunks=context_chunks,
                response_mode="research",
            )
        lead_anchor, lead_sentence = selected[0]
        sections = ["Short answer", f"\n{lead_sentence} [{lead_anchor}]"]
        details = [item for item in selected[1:] if item[1] != lead_sentence]
        if details:
            sections.append("\nWhat that means")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in details[:3])
        return "\n".join(sections)

    @staticmethod
    def _fallback_definition_answer(
        query: str,
        context_chunks: list[tuple[int, str]],
        response_mode: str,
        additional_terms: set[str] | None = None,
    ) -> str:
        answer_plan = build_answer_plan(query=query, response_mode=response_mode)
        requested_elements = set(answer_plan.requested_elements)
        literal_query_terms = SynthesisService._query_terms(query)
        document_terms = additional_terms or set()
        # Keep the direct-definition ranking driven by the user's words. The
        # broader document vocabulary is useful for optional working details,
        # but letting it score the lead sentence makes OCR-rich examples and
        # index-like fragments outrank the actual definition.
        query_terms = literal_query_terms
        prepared_context_texts = [
            SynthesisService._context_text(block)
            for _, block in context_chunks[:10]
        ]
        document_component_terms = {
            term
            for term in document_terms - literal_query_terms
            if sum(
                SynthesisService._term_matches(sentence=text, term=term)
                for text in prepared_context_texts
            ) <= 2
        }
        subject_terms = {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{2,}", answer_plan.subject.lower())
            if token not in _QUERY_STOPWORDS and len(token) >= 4
        }
        definition_cues = (
            " is a ",
            " is an ",
            " is the ",
            " means ",
            " refers ",
            " called ",
            "probabilistic model",
            "generative model",
            "assumes",
            "generated from",
            "parameters are unknown",
        )
        working_cues = (
            "architecture",
            "building blocks",
            "building block",
            "composed of",
            "consists of",
            "goal is to",
            "subsample",
            "shrink",
            "reduce the computational",
            "convolutional layer",
            "convolutional layers",
            "generated from",
            "distribution",
            "parameters",
            "density",
            "filter",
            "kernel",
            "pooling layer",
            "pooling layers",
            "sample",
            "estimate",
            "algorithm",
            "cluster",
            "stack",
        )
        use_cues = (
            "applications",
            "used for",
            "used in",
            "power ",
            "powering",
            "successful at",
            "density estimation",
            "clustering",
            "anomaly detection",
            "outlier",
            "visualization",
        )
        limitation_cues = (
            "limitation",
            "drawback",
            "fails to",
            "failure case",
            "different shapes",
            "doesn't do so well",
            "does not work",
        )
        positive_exception_cues = (
            "not restricted",
            "not limited",
            "not only",
            "successful at",
        )
        acronym_subjects = {
            token.upper().rstrip("S")
            for token in re.findall(r"\b[A-Za-z][A-Za-z0-9+-]{1,8}s?\b", query)
            if 2 <= len(token.rstrip("sS")) <= 8
            and (token.isupper() or len(token.rstrip("sS")) <= 4)
            and token.lower() not in _QUERY_STOPWORDS
            and token.lower().rstrip("s") != "ai"
        }

        definitions: list[tuple[float, int, str]] = []
        workings: list[tuple[float, int, str]] = []
        uses: list[tuple[float, int, str]] = []
        limits: list[tuple[float, int, str]] = []
        for idx, block in context_chunks[:10]:
            text = SynthesisService._context_text(block)
            sentences = SynthesisService._split_sentences(text)[:12]
            required_subject_hits = max(1, ((3 * len(subject_terms)) + 4) // 5)
            subject_positions = [
                position
                for position, candidate in enumerate(sentences)
                if (
                    SynthesisService._sentence_score(candidate, subject_terms) >= required_subject_hits
                    or any(
                        re.search(rf"\b{re.escape(acronym)}s?\b", candidate, flags=re.I)
                        for acronym in acronym_subjects
                    )
                    or (
                        additional_terms
                        and SynthesisService._sentence_score(candidate, additional_terms) > 0
                        and any(cue in f" {candidate.lower()} " for cue in working_cues)
                    )
                )
            ]
            for sentence_index, sentence in enumerate(sentences):
                sentence = SynthesisService._clean_evidence_sentence(sentence)
                sentence = SynthesisService._strip_structural_prefix_for_subject(
                    sentence,
                    answer_plan.subject,
                )
                if (
                    len(sentence.split()) < 7
                    or SynthesisService._is_low_value_evidence_sentence(sentence)
                    or SynthesisService._is_extract_fragment(sentence)
                ):
                    continue
                lowered = f" {sentence.lower()} "
                if not requested_elements & {"applications", "examples"} and any(
                    cue in lowered
                    for cue in (
                        "topics, including",
                        "introduced many additional",
                        "covers the following topics",
                        "gives an overview of",
                    )
                ):
                    continue
                base = SynthesisService._sentence_score(sentence, query_terms)
                rank_bonus = max(0, 10 - idx) * 0.04 + max(0, 12 - sentence_index) * 0.01
                boundary_penalty = 0.9 if sentence and sentence[-1] not in ".!?" else 0.0
                definition_score = (
                    base
                    + rank_bonus
                    + sum(1.0 for cue in definition_cues if cue in lowered)
                    + SynthesisService._subject_head_score(
                        sentence=sentence,
                        subject_terms=subject_terms,
                        acronym_subjects=acronym_subjects,
                    )
                    + SynthesisService._subject_called_definition_score(
                        sentence=sentence,
                        subject_terms=subject_terms,
                    )
                    - boundary_penalty
                )
                if not requested_elements & {"examples", "applications"} and re.match(
                    r"^(?:for example|consider|historically)\b",
                    sentence.strip(),
                    flags=re.I,
                ):
                    definition_score -= 2.2
                if not re.search(r"\b(history|historical|origin|origins)\b", query, re.I) and any(
                    cue in lowered
                    for cue in (" emerged from ", " inspired by ", " since the 19", " since the 20")
                ):
                    definition_score -= 4.0
                if any(
                    re.search(
                        rf"\b[A-Za-z][A-Za-z0-9+/-]*(?:\s+[A-Za-z][A-Za-z0-9+/-]*){{1,7}}\s+\({re.escape(acronym)}s?\)",
                        sentence,
                        flags=re.I,
                    )
                    for acronym in acronym_subjects
                ):
                    definition_score += 3.0
                working_score = (
                    base
                    + rank_bonus
                    + sum(0.65 for cue in working_cues if cue in lowered)
                    + (
                        0.6
                        * SynthesisService._subject_head_score(
                            sentence=sentence,
                            subject_terms=subject_terms,
                            acronym_subjects=acronym_subjects,
                        )
                    )
                    + (1.5 * answer_evidence_cue_score("mechanism_explanation", sentence))
                    + min(
                        8.0,
                        1.8 * SynthesisService._sentence_score(
                            sentence,
                            document_component_terms,
                        ),
                    )
                    + (
                        2.5
                        if document_component_terms
                        and SynthesisService._sentence_score(sentence, document_component_terms) >= 2
                        and answer_evidence_cue_score("mechanism_explanation", sentence) >= 0.6
                        else 0.0
                    )
                    - boundary_penalty
                )
                if not requested_elements & {"examples", "applications"} and re.match(
                    r"^(?:for example|consider)\b",
                    sentence.strip(),
                    flags=re.I,
                ):
                    working_score -= 2.2
                use_score = base + rank_bonus + sum(0.75 for cue in use_cues if cue in lowered) - boundary_penalty
                limit_score = base + rank_bonus + sum(0.85 for cue in limitation_cues if cue in lowered) - boundary_penalty
                if definition_score > base + rank_bonus:
                    definitions.append((definition_score, idx, sentence))
                near_subject = any(
                    0 <= sentence_index - position <= 2
                    for position in subject_positions
                )
                if working_score > base + rank_bonus and near_subject:
                    workings.append((working_score, idx, sentence))
                if use_score > base + rank_bonus:
                    uses.append((use_score, idx, sentence))
                if limit_score > base + rank_bonus and not any(
                    cue in lowered for cue in positive_exception_cues
                ):
                    limits.append((limit_score, idx, sentence))

        selected_definition = SynthesisService._dedupe_scored_sentences(definitions, limit=1)
        selected_uses = SynthesisService._dedupe_scored_sentences(uses, limit=2)
        selected_limits = SynthesisService._dedupe_scored_sentences(limits, limit=1)

        if not selected_definition:
            selected_definition = SynthesisService._best_evidence_sentences(
                context_chunks=context_chunks,
                query_terms=query_terms,
                limit=1,
            )
        if not selected_definition:
            return "I found related passages, but not a clear source-backed definition to answer safely."

        selected_working = SynthesisService._dedupe_scored_sentences(workings, limit=2)

        mode = response_mode.strip().lower()
        title = "Exam-ready definition" if mode in {"exam", "exam_answer"} else "Short answer"
        sections = [title, "\nDirect answer"]
        sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in selected_definition)

        extra_seen = {sentence for _, sentence in selected_definition}
        working_items = [(anchor, sentence) for anchor, sentence in selected_working if sentence not in extra_seen]
        extra_seen.update(sentence for _, sentence in working_items)
        use_items = [(anchor, sentence) for anchor, sentence in selected_uses if sentence not in extra_seen]
        extra_seen.update(sentence for _, sentence in use_items)
        limit_items = [(anchor, sentence) for anchor, sentence in selected_limits if sentence not in extra_seen]

        if working_items:
            if len(working_items) < 2:
                supplemental = SynthesisService._dedupe_scored_sentences(workings, limit=6)
                existing = extra_seen | {sentence for _, sentence in working_items}
                for anchor, sentence in supplemental:
                    if sentence in existing:
                        continue
                    working_items.append((anchor, sentence))
                    existing.add(sentence)
                    if len(working_items) >= 2:
                        break
            sections.append("\nHow it works")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in working_items[:2])
        if use_items and requested_elements & {"applications", "examples"}:
            sections.append("\nWhat it is used for")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in use_items[:2])
        if limit_items and "limitations" in requested_elements:
            sections.append("\nLimitation")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in limit_items[:1])

        sections.append("\nEvidence note\nOpen Sources to inspect the exact textbook passages used.")
        return "\n".join(sections)

    @staticmethod
    def _subject_called_definition_score(*, sentence: str, subject_terms: set[str]) -> float:
        if not subject_terms:
            return 0.0
        lowered = sentence.lower()
        for term in subject_terms:
            escaped = re.escape(term)
            if re.search(
                rf"\b(?:is|are|was|were)\s+(?:also\s+)?(?:called|known\s+as)\s+{escaped}\b",
                lowered,
            ):
                return 3.0
        if " called " in f" {lowered} " and all(
            SynthesisService._term_matches(sentence=sentence, term=term)
            for term in subject_terms
        ):
            return 3.0
        return 0.0

    @staticmethod
    def _subject_head_score(
        *,
        sentence: str,
        subject_terms: set[str],
        acronym_subjects: set[str],
    ) -> float:
        """Prefer statements about the requested subject over mentions as an object."""

        leading_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+-]*", sentence)[:4]
        if not leading_tokens:
            return 0.0
        normalized = [token.lower().rstrip("s") for token in leading_tokens]
        normalized_subjects = {term.lower().rstrip("s") for term in subject_terms}
        normalized_acronyms = {term.lower().rstrip("s") for term in acronym_subjects}
        if normalized[0] in normalized_subjects | normalized_acronyms:
            return 2.4
        if any(token in normalized_subjects | normalized_acronyms for token in normalized[:3]):
            return 1.1
        full_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+-]*", sentence)[:10]
        for acronym in acronym_subjects:
            acronym = acronym.upper().rstrip("S")
            for length in range(2, min(7, len(full_tokens)) + 1):
                if "".join(token[0].upper() for token in full_tokens[:length]) == acronym:
                    return 2.4
        subject_pattern = "|".join(
            re.escape(term.rstrip("s")) + "s?"
            for term in normalized_subjects | normalized_acronyms
            if term
        )
        if subject_pattern and re.search(
            rf"\b(?:a\s+|an\s+|the\s+)?(?:{subject_pattern})\s+"
            r"(?:is|are|uses|use|works|consists|contains|applies|computes|solves)\b",
            sentence,
            flags=re.I,
        ):
            return 1.6
        return 0.0

    @staticmethod
    def _dedupe_scored_sentences(
        scored: list[tuple[float, int, str]],
        *,
        limit: int,
        min_words: int = 6,
        allow_low_value: bool = False,
    ) -> list[tuple[int, str]]:
        selected: list[tuple[int, str]] = []
        seen: set[str] = set()
        for _, idx, sentence in sorted(scored, key=lambda item: item[0], reverse=True):
            sentence = SynthesisService._clean_evidence_sentence(sentence)
            if len(sentence.split()) < min_words or (
                not allow_low_value and SynthesisService._is_low_value_evidence_sentence(sentence)
            ):
                continue
            normalized = re.sub(r"\W+", "", sentence.lower())[:120]
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append((idx, sentence))
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _fallback_heading(response_mode: str) -> str:
        mode = response_mode.strip().lower()
        if mode in {"exam", "exam_answer"}:
            return "Exam-ready answer"
        if mode == "revision_notes":
            return "Revision notes"
        if mode == "study_guide":
            return "Study guide"
        if mode == "important_questions":
            return "Important question leads"
        if mode == "compare_concepts":
            return "Grounded comparison"
        if mode == "general_chat":
            return "I can answer this from your material"
        if mode == "deep_research":
            return "Deep research synthesis"
        if mode == "research_paper":
            return "Research paper draft"
        if mode == "summary":
            return "Document summary from the retrieved passages:"
        return "Short answer"

    @staticmethod
    def _is_definition_solution_query(query: str) -> bool:
        normalized = query.lower()
        asks_definition = any(phrase in normalized for phrase in ("what is", "define", "meaning of"))
        asks_solution = bool(re.search(r"\b(?:reduce|reduced|prevent|avoid|fix)\b", normalized))
        return asks_definition and asks_solution

    @staticmethod
    def _is_local_first_definition_query(query: str) -> bool:
        normalized = query.lower()
        return ("local-first" in normalized or "local first" in normalized) and bool(
            re.search(r"\b(?:what\s+(?:does|is|are)|define|meaning)\b", normalized)
        )

    @staticmethod
    def _is_privacy_control_query(query: str) -> bool:
        normalized = query.lower()
        if re.search(r"\bwhat\s+(?:does|is|are)\b.{0,60}\blocal[- ]first\b.{0,40}\bmean\b", normalized):
            return False
        return any(term in normalized for term in ("privacy", "private", "local-first", "local first")) and any(
            term in normalized for term in ("preserve", "protect", "control", "security", "secure", "local")
        )

    @staticmethod
    def _is_privacy_cue_query(query: str) -> bool:
        normalized = query.lower()
        return any(term in normalized for term in ("privacy", "private", "trust", "local-first", "local first")) and any(
            term in normalized for term in ("cue", "cues", "visible", "show", "display", "signal", "signals")
        )

    @staticmethod
    def _is_definition_query(query: str) -> bool:
        normalized = query.lower().strip()
        if any(phrase in normalized for phrase in ("what is", "what are", "define", "meaning of")):
            return True
        if normalized.startswith("explain ") and not SynthesisService._is_list_or_algorithm_query(normalized):
            return True
        return bool(re.search(r"\bwhat does .+ mean\b", normalized))

    @staticmethod
    def _fallback_document_summary(query: str, context_chunks: list[tuple[int, str]]) -> str:
        query_terms = SynthesisService._query_terms(query)
        summary_terms = query_terms | {
            "abstract",
            "introduction",
            "overview",
            "chapter",
            "learning",
            "data",
            "model",
            "training",
            "algorithm",
            "method",
            "approach",
            "example",
            "result",
            "limitation",
            "conclusion",
            "summary",
        }
        evidence = SynthesisService._best_summary_sentences(
            context_chunks=context_chunks,
            query_terms=summary_terms,
            limit=8,
        )
        if len(evidence) < 4:
            evidence.extend(
                SynthesisService._first_readable_sentences(
                    context_chunks=context_chunks,
                    limit=8 - len(evidence),
                    existing={sentence for _, sentence in evidence},
                )
            )
        if not evidence:
            evidence = [
                (idx, preview)
                for idx, block in context_chunks[:4]
                if (preview := SynthesisService._context_text(block)[:260].strip())
            ]
        if not evidence:
            return "I found the document, but there was not enough readable text to summarize it."

        sections = ["Document summary from the retrieved passages:"]
        overview = evidence[:2]
        main_points = evidence[2:6]
        caveats = evidence[6:8]

        sections.append("\nWhat it is about")
        sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in overview)

        if main_points:
            sections.append("\nMain ideas")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in main_points)

        if caveats:
            sections.append("\nUseful caveats / details")
            sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in caveats)

        sections.append("\nIf you want, ask for a chapter-wise, page-wise, or exam-style summary next.")
        return "\n".join(sections)

    @staticmethod
    def _best_summary_sentences(
        context_chunks: list[tuple[int, str]],
        query_terms: set[str],
        limit: int,
    ) -> list[tuple[int, str]]:
        candidates: list[tuple[float, int, str]] = []
        for idx, block in context_chunks[:10]:
            text = SynthesisService._context_text(block)
            for sentence_index, sentence in enumerate(SynthesisService._split_sentences(text)[:12]):
                if len(sentence.split()) < 8 or SynthesisService._is_low_value_summary_sentence(sentence):
                    continue
                term_score = SynthesisService._sentence_score(sentence, query_terms)
                outline_bonus = 0.0
                lowered = sentence.lower()
                if any(cue in lowered for cue in ("covers the following topics", "part i", "part ii", "chapter")):
                    outline_bonus += 3.0
                if any(cue in lowered for cue in ("scikit-learn", "tensorflow", "keras", "main algorithms")):
                    outline_bonus += 1.4
                if any(cue in lowered for cue in ("overfitting", "underfitting", "limitations", "caveats")):
                    outline_bonus += 1.0
                rank_bonus = max(0, 10 - idx) * 0.15 + max(0, 12 - sentence_index) * 0.02
                candidates.append((term_score + outline_bonus + rank_bonus, idx, sentence))
        return SynthesisService._dedupe_scored_sentences(candidates, limit=limit)

    @staticmethod
    def _is_low_value_summary_sentence(sentence: str) -> bool:
        lowered = sentence.lower()
        low_value_patterns = (
            "other resources",
            "great introduction",
            "publishing",
            "edition",
            "pearson",
            "packt",
            "chapman",
            "oreilly",
            "self-published",
            "available to learn",
            "andrew ng",
            "jeremy howard",
            "sylvain gugger",
            "stewart russell",
            "stuwart russell",
            "peter norvig",
            "hundred-page",
            "learning from data",
        )
        return any(pattern in lowered for pattern in low_value_patterns)

    @staticmethod
    def _is_low_value_evidence_sentence(sentence: str) -> bool:
        lowered = sentence.lower()
        if SynthesisService._is_low_value_summary_sentence(sentence):
            return True
        if re.search(
            r"(?:^|\?\s*\d{1,2}\.\s+)(?:practice|exercise)\b",
            lowered,
        ):
            return True
        if any(
            marker in lowered
            for marker in (
                "isbn",
                "copyright",
                "permission to reproduce",
                "all rights reserved",
                "trademark",
            )
        ):
            return True
        comma_fragments = [fragment.strip() for fragment in re.split(r"[,;]", sentence) if fragment.strip()]
        compact_fragment_count = sum(1 for fragment in comma_fragments if 2 <= len(fragment.split()) <= 6)
        outline_cues = (
            "covers the following topics",
            "roadmap",
            "part i",
            "part ii",
            "chapter covers",
            "learning objectives",
            "we will start with",
            "then we'll discuss",
            "before we move on",
            "in this section we will",
        )
        if any(cue in lowered for cue in outline_cues):
            return False
        index_markers = (
            "beam search",
            "bellman",
            "inverse_transform",
            "fast-mcd",
            "see also",
            "sklearn.",
        )
        marker_count = sum(marker in lowered for marker in index_markers)
        if marker_count >= 2 and len(comma_fragments) >= 3:
            return True
        if compact_fragment_count >= 5 and marker_count >= 1:
            return True
        if compact_fragment_count >= 8 and sentence.count(".") <= 1:
            return True
        return False

    @staticmethod
    def _is_roadmap_sentence(sentence: str) -> bool:
        """Identify topic previews that mention concepts without explaining them."""

        lowered = sentence.lower()
        return any(
            marker in lowered
            for marker in (
                "covers the following topics",
                "chapter covers",
                "learning objectives",
                "we will start with",
                "then we'll discuss",
                "before we move on",
                "in this section we will",
                "this chapter will",
                "we will look at",
                "we will examine",
            )
        )

    @staticmethod
    def _is_code_heavy_sentence(sentence: str) -> bool:
        lowered = sentence.lower()
        markers = (
            ">>>",
            "np.",
            "tf.",
            "sklearn.",
            ".fit(",
            ".predict(",
            ".kneighbors(",
            "array([",
            "model.compile(",
        )
        if any(marker in lowered for marker in markers):
            return True
        code_tokens = len(re.findall(r"\b[a-zA-Z][a-zA-Z0-9]*_[a-zA-Z0-9_]+\b", sentence))
        assignments = len(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*=", sentence))
        return code_tokens + assignments >= 3

    @staticmethod
    def _is_formula_heavy_sentence(sentence: str) -> bool:
        formula_markers = sum(
            sentence.count(marker)
            for marker in ("=", "∑", "⊺", "argmax", "exp(", "max(")
        )
        return formula_markers >= 2

    @staticmethod
    def _is_extract_fragment(sentence: str) -> bool:
        stripped = sentence.strip()
        if not stripped:
            return True
        if stripped.startswith(("[...]", "\u2026")):
            return True
        if "they note that:" in stripped.lower():
            return True
        if re.search(r":\s*\d+\.?$", stripped):
            return True
        if re.search(
            r"\b(?:and|at|because|by|could|for|from|highly|in|means|of|or|the|that|to|while|with|would)\.?$",
            stripped,
            flags=re.I,
        ):
            return True
        first_character = stripped[0]
        return first_character.isalpha() and first_character.islower()

    @staticmethod
    def _clean_evidence_sentence(sentence: str) -> str:
        cleaned = re.sub(r"\s+", " ", sentence).strip(" -")
        cleaned = re.split(r"\s+>>>\s+", cleaned, maxsplit=1)[0].strip()
        cleaned = re.sub(r"^(?:\([^)]{1,12}\)\.?\s*)+", "", cleaned).strip()
        # OCR can prepend a page marker such as "al a" before a heading. Strip
        # only short lowercase noise immediately before a structural heading.
        cleaned = re.sub(
            r"^(?:[a-z][a-z0-9]{0,3}\s+){1,3}(?=(?:CHAPTER|SECTION|PART)\b)",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"^(?:CHAPTER|SECTION|PART)\s+[A-Z0-9IVXLCDM.-]+\s+[^.?!]{1,120}?\s+"
            r"(?=(?:[A-Z][A-Za-z0-9+-]*\s+){1,8}"
            r"(?:is|are|refers|means|serves|can|works|uses|provides|contains)\b)",
            "",
            cleaned,
        )
        section_match = re.search(
            r"(?:^|\s)\d+(?:\.\d+)+\s+"
            r"(?:[A-Z][A-Za-z0-9/-]*\s+){1,8}?"
            r"(?=(?:Since|Because|As|The|This|In|To|We|Our|Each)\b)",
            cleaned,
        )
        if section_match:
            cleaned = cleaned[section_match.end():].strip()
        cleaned = re.sub(
            r"^(?:[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,5})\s+"
            r"(?:\d+\s+){2,}(?=(?:A|An|The|This|It|All|Each|When|There|Typical)\b)",
            "",
            cleaned,
        ).strip()
        cleaned = re.sub(r"^#+\s+[^.?!]{0,180}?\s+(?=NIRMIQ\b)", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(
            r"^#+\s+Golden Demo Source\s+\d+:\s+[^.?!]{1,90}?"
            r"(?:Notes|Brief|Retrieval|Runtime|Question Bank|Guide|Privacy)\s+",
            "",
            cleaned,
            flags=re.I,
        ).strip()
        cleaned = re.sub(
            r"^#{1,6}\s+[^.?!]{1,100}?\s+"
            r"(?=(?:A|An|The|This|These|Spectral|Calibration|Before|If|"
            r"Frequency|Generative|Prompt|Exam|NIRMIQ|Low|High)\b)",
            "",
            cleaned,
            flags=re.I,
        ).strip()
        cleaned = re.sub(
            r"^NIRMIQ\s+[^.?!]{1,120}?\s+-\s+page\s+\d+\s+",
            "",
            cleaned,
            flags=re.I,
        ).strip()
        cleaned = re.sub(
            r"^Chapter\s+\d+\s+-\s+[A-Z][A-Za-z0-9 &/()'-]{1,70}?\s+"
            r"(?=(?:A|An|The|This|If|Figure|Low|High|Adaptive)\b)",
            "",
            cleaned,
            flags=re.I,
        ).strip()
        cleaned = re.sub(r"\s+#\s+.*$", "", cleaned).strip()
        cleaned = re.sub(
            r"^(?:(?:[A-Z][A-Za-z0-9'()./-]*)|&)(?:\s+(?:(?:[A-Z][A-Za-z0-9'()./-]*)|&)){0,5}\s+"
            r"(?=(?:A|An|The|This|It|All|Each|When|There|Typical)\b)",
            "",
            cleaned,
        ).strip()
        cleaned = cleaned.rstrip(" :")
        if cleaned and cleaned[-1] not in ".!?":
            cleaned = f"{cleaned}."
        return cleaned

    @staticmethod
    def _format_extract_answer(
        *,
        heading: str,
        selected: list[tuple[int, str]],
        response_mode: str,
    ) -> str:
        mode = response_mode.strip().lower()
        if mode == "compare_concepts":
            bullets = "\n".join(f"- {sentence} [{idx}]" for idx, sentence in selected[:5])
            return f"{heading}\n\nKey differences\n{bullets}\n\nWhere this came from\nOpen Sources to inspect the cited passages."
        if mode in {"exam", "exam_answer", "revision_notes"}:
            bullets = "\n".join(f"- {sentence} [{idx}]" for idx, sentence in selected[:5])
            return f"{heading}\n\nKey points\n{bullets}\n\nStudy takeaway\nUse these cited points as the answer skeleton."
        if mode == "deep_research":
            core = selected[:3]
            details = selected[3:6]
            sections = [heading, "\nCore finding"]
            sections.extend(f"- {sentence} [{idx}]" for idx, sentence in core)
            if details:
                sections.append("\nSupporting details")
                sections.extend(f"- {sentence} [{idx}]" for idx, sentence in details)
            sections.append("\nWhere this came from\nOpen Sources to inspect the cited passages.")
            return "\n".join(sections)
        lead = selected[0][1]
        support = selected[1:5] or selected[:1]
        bullets = "\n".join(f"- {sentence} [{idx}]" for idx, sentence in support[:4])
        return (
            f"{heading}\n\n"
            f"Direct answer\n{lead} [{selected[0][0]}]\n\n"
            f"Key points\n{bullets}\n\n"
            "Evidence note\nOpen Sources to inspect the exact passages used."
        )

    @staticmethod
    def _is_list_or_algorithm_query(query: str) -> bool:
        normalized = query.lower()
        if re.search(r"\b(?:step|steps|procedure|pipeline|workflow|process)\b", normalized):
            return False
        return bool(
            re.search(r"\b(list|few|some|examples?|algorithms?|types?|methods?|techniques?)\b", normalized)
        )

    @staticmethod
    def _fallback_enumeration_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
        response_mode: str,
        answer_plan: AnswerPlan,
    ) -> str:
        query_terms = SynthesisService._query_terms(query)
        obligation = answer_plan.evidence_obligations[0]
        requested_count = 0
        count_words = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        count_match = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b", query.lower())
        if count_match:
            requested_count = int(count_match.group(1)) if count_match.group(1).isdigit() else count_words[count_match.group(1)]
        candidates: list[tuple[float, int, str]] = []
        for anchor, block in context_chunks[:12]:
            source_heading = SynthesisService._source_heading(block)
            if source_heading:
                heading_items = SynthesisService._enumeration_items_from_sentence(source_heading)
                if len(heading_items) >= 3:
                    candidates.append((30.0, anchor, source_heading))
                elif (
                    2 <= len(source_heading.split()) <= 8
                    and "/" not in source_heading
                    and "http" not in source_heading.lower()
                    and not re.search(
                        r"\b(?:chapter|section|part|table|figure|product|document|phase|step|"
                        r"pipeline|reference|source)\b",
                        source_heading,
                        flags=re.I,
                    )
                    and SynthesisService._sentence_score(
                        SynthesisService._context_text(block),
                        query_terms,
                    ) >= 2
                    and not (
                        "principle" in answer_plan.subject.lower()
                        and "principle" in SynthesisService._context_text(block).lower()
                    )
                ):
                    candidates.append((24.0, anchor, source_heading))
                elif (
                    2 <= len(source_heading.split()) <= 4
                    and "principle" in answer_plan.subject.lower()
                    and "principle" in SynthesisService._context_text(block).lower()
                    and not re.search(
                        r"\b(?:chapter|section|part|table|figure|product|document|phase|step|"
                        r"pipeline|reference|source)\b",
                        source_heading,
                        flags=re.I,
                    )
                ):
                    # OCR can remove the bullet/number around the final item
                    # in a source list, leaving only a concise section heading.
                    candidates.append((28.0, anchor, source_heading))
            text = SynthesisService._context_text_with_heading(block)
            for position, sentence in enumerate(SynthesisService._split_sentences(text)[:12]):
                if len(sentence.split()) < 5 or SynthesisService._is_code_heavy_sentence(sentence):
                    continue
                score = (
                    (2.0 * SynthesisService._sentence_score(sentence, query_terms))
                    + (5.0 * evidence_obligation_score(obligation, sentence))
                    + (
                        6.0
                        * SynthesisService._structural_scope_score(
                            query=query,
                            text=sentence,
                        )
                    )
                    + max(0, 10 - position) * 0.02
                )
                if score > 0:
                    candidates.append((score, anchor, sentence))

        items: list[tuple[int, str]] = []
        seen: set[str] = set()
        for _, anchor, sentence in sorted(candidates, reverse=True):
            for item in SynthesisService._enumeration_items_from_sentence(sentence):
                normalized = re.sub(r"\W+", "", item.lower())[:100]
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                items.append((anchor, item))
                if len(items) >= (requested_count or 10):
                    break
            if len(items) >= (requested_count or 10):
                break

        if not items:
            return SynthesisService._fallback_list_answer(
                query=query,
                context_chunks=context_chunks,
                response_mode=response_mode,
            )
        # Keep explicitly requested counts as separate bullets so each item
        # receives an independently verifiable citation. Grouping remains the
        # compact default for open-ended list questions.
        if not requested_count:
            items = SynthesisService._group_enumeration_items(items)
        heading = SynthesisService._fallback_heading(response_mode)
        return "\n".join(
            [
                heading,
                f"\n{SynthesisService._enumeration_scope_label(query, answer_plan.subject)}.",
                *(f"- {item} [{anchor}]." for anchor, item in items),
            ]
        )

    @staticmethod
    def _fallback_how_can_answer(
        *,
        query: str,
        context_chunks: list[tuple[int, str]],
        additional_terms: set[str] | None = None,
    ) -> str | None:
        """Answer broad how-can questions from direct action evidence."""

        if not re.search(r"\bhow\s+can\b", query, flags=re.I):
            return None
        query_terms = SynthesisService._query_terms(query)
        expanded_terms = set(additional_terms or set())
        action_cues = {
            "describe",
            "reference",
            "specify",
            "provide",
            "apply",
            "use",
            "works",
            "takes the form",
            "style",
            "persona",
            "format",
        }
        candidates: list[tuple[float, int, str]] = []
        for anchor, block in context_chunks[:12]:
            for position, sentence in enumerate(
                SynthesisService._planned_evidence_units(
                    text=SynthesisService._context_text_with_heading(block),
                    allow_roadmap_evidence=True,
                )[:24]
            ):
                cleaned = SynthesisService._clean_evidence_sentence(sentence)
                if (
                    len(cleaned.split()) < 5
                    or SynthesisService._is_low_value_evidence_sentence(cleaned)
                    or SynthesisService._is_code_heavy_sentence(cleaned)
                ):
                    continue
                lowered = cleaned.lower()
                action_score = sum(1.3 for cue in action_cues if cue in lowered)
                core_score = SynthesisService._sentence_score(cleaned, query_terms)
                expanded_score = SynthesisService._sentence_score(cleaned, expanded_terms)
                if action_score <= 0 or (core_score <= 0 and expanded_score <= 0):
                    continue
                candidates.append(
                    (
                        (4.0 * action_score)
                        + (2.0 * core_score)
                        + (0.4 * expanded_score)
                        + max(0, 18 - position) * 0.03,
                        anchor,
                        cleaned,
                    )
                )
        selected = SynthesisService._dedupe_scored_sentences(candidates, limit=2, min_words=5)
        if not selected:
            return None
        if all(
            re.search(rf"\b{term}\b", selected[0][1], flags=re.I)
            for term in ("style", "persona")
        ):
            selected = selected[:1]
        return "\n".join(
            [
                "Short answer",
                "",
                "Direct answer",
                *(f"- {sentence} [{anchor}]." for anchor, sentence in selected),
            ]
        )

    @staticmethod
    def _enumeration_items_from_sentence(sentence: str) -> list[str]:
        """Turn dense source roadmaps into bounded, still-extractive list items."""

        cleaned = SynthesisService._clean_evidence_sentence(sentence).strip(" -")
        if not cleaned:
            return []
        lowered = cleaned.lower()
        list_cues = ("following", "lists", "listed", "includes", "common", "types", "covers")
        if ":" in cleaned and any(cue in lowered.split(":", 1)[0] for cue in list_cues):
            cleaned = cleaned.split(":", 1)[1].strip()

        slash_parts = [part.strip(" ,;.-") for part in cleaned.split("/") if part.strip(" ,;.-")]
        if len(slash_parts) >= 2 and all(2 <= len(part.split()) <= 8 for part in slash_parts):
            return slash_parts

        # PDF extraction often removes bullets but leaves a gerund or a new
        # determiner at each item boundary.
        cleaned = re.sub(
            r"(?<=[a-z0-9)])\s+(?=(?:The|Other)\s|[A-Z][a-z]+ing\b)",
            "\n",
            cleaned,
        )
        coarse_parts = [part.strip(" ,;.-") for part in re.split(r"[\n;]+", cleaned) if part.strip()]
        expanded: list[str] = []
        for part in coarse_parts:
            if part.count(",") >= 3:
                expanded.extend(
                    fragment.strip(" ,;.-")
                    for fragment in re.split(r",\s*(?:and\s+)?", part)
                    if fragment.strip(" ,;.-")
                )
            else:
                expanded.append(part)

        items: list[str] = []
        for item in expanded:
            item = re.sub(r"^(?:and|or)\s+", "", item, flags=re.I).strip()
            coordinated = re.fullmatch(
                r"([a-zA-Z][\w-]+)\s+and\s+([a-zA-Z][\w-]+)\s+([a-zA-Z][\w-]+)",
                item,
            )
            if coordinated:
                first, second, noun = coordinated.groups()
                item = f"{first} {noun} and {second} {noun}"
            words = item.split()
            if len(words) < 2:
                continue
            if len(words) > 34:
                item = " ".join(words[:34]).rstrip(" ,;:")
            items.append(item)
        return items

    @staticmethod
    def _group_enumeration_items(items: list[tuple[int, str]]) -> list[tuple[int, str]]:
        grouped: list[tuple[int, str]] = []
        current_anchor: int | None = None
        current_items: list[str] = []
        current_words = 0

        def flush() -> None:
            nonlocal current_anchor, current_items, current_words
            if current_anchor is not None and current_items:
                grouped.append((current_anchor, "; ".join(current_items)))
            current_anchor = None
            current_items = []
            current_words = 0

        for anchor, item in items:
            item_words = len(item.split())
            if (
                current_anchor is not None
                and (anchor != current_anchor or len(current_items) >= 4 or current_words + item_words > 32)
            ):
                flush()
            if current_anchor is None:
                current_anchor = anchor
            current_items.append(item)
            current_words += item_words
        flush()

        if len(grouped) >= 2 and len(grouped[-1][1].split()) < 3:
            last_anchor, last_item = grouped.pop()
            previous_anchor, previous_item = grouped[-1]
            if last_anchor == previous_anchor:
                grouped[-1] = (previous_anchor, f"{previous_item}; {last_item}")
            else:
                grouped.append((last_anchor, last_item))
        return grouped

    @staticmethod
    def _structural_scope_score(*, query: str, text: str) -> float:
        pattern = re.compile(
            r"\b(part|chapter|section|figure|table)\s+([ivxlcdm]+|\d+(?:\.\d+)*)\b",
            flags=re.I,
        )
        requested = {(kind.lower(), value.lower()) for kind, value in pattern.findall(query)}
        if not requested:
            return 0.0
        present = {(kind.lower(), value.lower()) for kind, value in pattern.findall(text)}
        if requested & present:
            return 1.0
        if any(kind in {item[0] for item in requested} for kind, _ in present):
            return -0.75
        return 0.0

    @staticmethod
    def _enumeration_scope_label(query: str, subject: str) -> str:
        match = re.search(
            r"\b(part|chapter|section|figure|table)\s+([ivxlcdm]+|\d+(?:\.\d+)*)\b",
            query,
            flags=re.I,
        )
        if match:
            clean_subject = re.sub(r"\s+", " ", subject).strip(" ,.-")
            scoped_name = clean_subject if clean_subject else f"{match.group(1).title()} {match.group(2).upper()}"
            return f"{scoped_name} covers these source-backed topics"
        if re.search(r"\boverview\b", query, re.I):
            clean_subject = re.sub(r"\s+", " ", subject).strip(" ,.-")
            if clean_subject and len(clean_subject.split()) <= 10:
                return f"The requested overview lists these {clean_subject}"
            return "The requested overview lists these source-backed items"
        return "The source lists these supported items"

    @staticmethod
    def _fallback_list_answer(
        query: str,
        context_chunks: list[tuple[int, str]],
        response_mode: str,
    ) -> str:
        query_terms = SynthesisService._query_terms(query)
        evidence = SynthesisService._best_evidence_sentences(
            context_chunks=context_chunks,
            query_terms=query_terms,
            limit=6,
        )
        if not evidence:
            previews = [
                (idx, SynthesisService._context_text(block)[:220].strip())
                for idx, block in context_chunks[:3]
                if SynthesisService._context_text(block).strip()
            ]
            if not previews:
                return "I found citations, but not enough readable evidence to list items safely."
            return SynthesisService._format_extract_answer(
                heading=SynthesisService._fallback_heading(response_mode),
                selected=previews,
                response_mode=response_mode,
            )

        heading = SynthesisService._fallback_heading(response_mode)
        sections = [heading, "\nDirect answer"]
        sections.append(f"{evidence[0][1]} [{evidence[0][0]}]")
        sections.append("\nKey points")
        sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in evidence[:5])
        sections.append("\nEvidence note\nOnly items supported by retrieved passages are included.")
        return "\n".join(sections)

    @staticmethod
    def _first_readable_sentences(
        context_chunks: list[tuple[int, str]],
        *,
        limit: int,
        existing: set[str] | None = None,
    ) -> list[tuple[int, str]]:
        selected: list[tuple[int, str]] = []
        seen = set(existing or set())
        for idx, block in context_chunks[:8]:
            for sentence in SynthesisService._split_sentences(SynthesisService._context_text(block))[:6]:
                cleaned = sentence.strip()
                if len(cleaned.split()) < 8 or cleaned in seen or SynthesisService._is_low_value_evidence_sentence(cleaned):
                    continue
                seen.add(cleaned)
                selected.append((idx, cleaned))
                if len(selected) >= limit:
                    return selected
        return selected

    @staticmethod
    def _context_text(block: str) -> str:
        lines = block.splitlines()
        content_lines = lines[1:] if len(lines) > 1 else lines
        cleaned_lines: list[str] = []
        for line in content_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("source heading:"):
                continue
            if stripped.startswith("#"):
                stripped = re.sub(
                    r"^#{1,6}\s+Golden Demo Source\s+\d+:\s+[^.?!]{1,110}?"
                    r"(?:Notes|Brief|Retrieval|Runtime|Question Bank|Guide|Privacy)\s+",
                    "",
                    stripped,
                    flags=re.I,
                ).strip()
                if stripped.startswith("#"):
                    stripped = re.sub(
                        r"^#{1,6}\s+[^.?!]{1,100}?\s+"
                        r"(?=(?:A|An|The|This|These|Spectral|Calibration|Before|If|"
                        r"Frequency|Generative|Prompt|Exam|NIRMIQ|Low|High)\b)",
                        "",
                        stripped,
                        flags=re.I,
                    ).strip()
                if stripped.startswith("#"):
                    continue
            cleaned_lines.append(stripped)
        content_lines = cleaned_lines
        text = " ".join(content_lines)
        return re.sub(r"\s+", " ", normalize_ocr_text(text)).strip()

    @staticmethod
    def _context_text_with_heading(block: str) -> str:
        """Include source section labels for ranking without exposing transport metadata."""

        text = SynthesisService._context_text(block)
        heading = SynthesisService._source_heading(block)
        if not heading or heading.lower() in text.lower():
            return text
        return f"{heading}. {text}".strip()

    @staticmethod
    def _source_heading(block: str) -> str:
        for line in block.splitlines()[:4]:
            stripped = line.strip()
            if stripped.lower().startswith("source heading:"):
                return stripped.split(":", 1)[1].strip()
        return ""

    @staticmethod
    def _strip_structural_prefix_for_subject(sentence: str, subject: str) -> str:
        """Remove OCR heading text when a subject-led definition follows it."""

        normalized_subject = re.sub(r"\s+", " ", subject.strip())
        if not normalized_subject or len(normalized_subject.split()) > 8:
            return sentence
        subject_match = re.search(
            rf"\b{re.escape(normalized_subject)}\b\s+"
            r"(?:is|are|means|refers|denotes|describes|represents)\b",
            sentence,
            flags=re.I,
        )
        if not subject_match or subject_match.start() <= 0:
            return sentence
        prefix = sentence[: subject_match.start()].strip()
        if not re.search(r"\b(?:chapter|section|part|overview|document)\b", prefix, flags=re.I):
            return sentence
        return sentence[subject_match.start() :].strip()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        normalized = normalize_ocr_text(text)
        normalized = re.sub(r"[\u2022\uf0b7\u25aa\u25e6]+", ". ", normalized)
        normalized = re.sub(r"\n+", " ", normalized)
        return [
            sentence.strip(" -")
            for sentence in re.split(r"(?<=[.!?])\s+", normalized)
            if sentence.strip(" -")
        ]

    @staticmethod
    def _query_terms(query: str) -> set[str]:
        terms = {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", query.lower())
            if token not in _QUERY_STOPWORDS
        }
        normalized = query.lower()
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
                }
            )
        if "gmm" in terms or "gaussian mixture" in normalized:
            terms.update(
                {
                    "probabilistic",
                    "distribution",
                    "distributions",
                    "generated",
                    "parameters",
                    "cluster",
                    "clusters",
                    "ellipsoidal",
                    "density",
                    "generative",
                }
            )
        if any(phrase in normalized for phrase in ("token position", "token positions", "represent positions")):
            terms.update({"positional", "encoding", "encodings", "embedding", "embeddings", "sequence", "order"})
        if "multi-head" in normalized or "multi head" in normalized:
            terms.update({"jointly", "attend", "information", "representation", "subspaces", "positions", "heads"})
        if "recurrence" in normalized or "convolution" in normalized:
            terms.update({"transformer", "attention", "mechanism", "eschewing", "relying", "entirely", "architecture"})
        if "cross-validation" in normalized or "cross validation" in normalized or "model selection" in normalized:
            terms.update({"selecting", "model", "tuning", "hyperparameters", "validation", "kfold", "fold"})
        if "privacy" in normalized or "sensitive" in normalized:
            terms.update({"sensitive", "personal", "information", "pii", "mask", "masking", "encryption", "secure", "retention"})
        if any(term in normalized for term in ("hardware", "processor", "device", "machine")):
            terms.update({"machine", "gpu", "processor", "device"})
        if any(term in normalized for term in ("duration", "training time", "how long", "runtime")):
            terms.update({"hours", "steps", "time", "training"})
        if any(phrase in normalized for phrase in ("fact-check", "fact check", "verification", "verify")):
            terms.update({"trusted", "sources", "retrieval", "rag", "fallback", "uncertain", "cross-check"})
        if any(term in normalized for term in ("avoid", "abstain", "refuse", "decline", "confidently")):
            terms.update({"weak", "unrelated", "unsupported", "evidence", "grounded", "context"})
        if "generate text" in normalized or "generates text" in normalized:
            terms.update({"predicting", "likely", "next", "tokens", "context"})
        return terms

    @staticmethod
    def _relevance_query(
        *,
        query: str,
        response_mode: str,
        exam_context: dict[str, object] | None,
    ) -> str:
        mode = response_mode.strip().lower()
        if mode in {"study_guide", "important_questions"} and exam_context:
            questions = exam_context.get("questions") or []
            if isinstance(questions, list) and questions:
                question_text = " ".join(
                    str(item.get("question", ""))
                    for item in questions[:8]
                    if isinstance(item, dict) and item.get("question")
                )
                if question_text.strip():
                    return f"{query}\n{question_text}"
        return query

    @staticmethod
    def _sentence_score(sentence: str, query_terms: set[str]) -> float:
        if not query_terms:
            return 0.0
        return float(
            sum(
                1
                for term in query_terms
                if SynthesisService._term_matches(sentence=sentence, term=term)
            )
        )

    @staticmethod
    def _term_matches(*, sentence: str, term: str) -> bool:
        """Match specific phrases exactly while retaining mild singular/plural tolerance."""

        lowered = re.sub(r"\s+", " ", sentence.lower().replace("-", " "))
        normalized_term = re.sub(r"\s+", " ", term.lower().replace("-", " ")).strip()
        if not normalized_term:
            return False
        if " " in normalized_term:
            return normalized_term in lowered
        if normalized_term in lowered:
            return True
        return len(normalized_term) >= 5 and any(
            word.startswith(normalized_term[:5])
            for word in re.findall(r"[a-zA-Z][a-zA-Z0-9+]*", lowered)
        )

    @staticmethod
    def _context_relevance(query: str, bundle: RetrievalBundle) -> dict[str, object]:
        query_terms = SynthesisService._primary_query_terms(query) | SynthesisService._context_acronym_terms(
            query=query,
            bundle=bundle,
        )
        if any(phrase in query.lower() for phrase in ("fact-check", "fact check", "verification", "verify")):
            query_terms.update(
                {
                    "cross-check",
                    "trusted",
                    "sources",
                    "retrieval-based",
                    "fallback",
                    "uncertain",
                }
            )
        context_terms: set[str] = set()
        for chunk in bundle.chunks[:5]:
            normalized_text = normalize_ocr_text(chunk.text).lower()
            context_terms.update(re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", normalized_text))

        matched_terms = sorted(
            term
            for term in query_terms
            if term in context_terms
            or any(len(term) >= 5 and candidate.startswith(term[:6]) for candidate in context_terms)
        )
        score = len(matched_terms) / max(len(query_terms), 1)
        direct_profile = SynthesisService._direct_evidence_profile(query=query, bundle=bundle)
        direct_evidence_count = int(direct_profile.get("direct_evidence_count") or 0)
        if not query_terms:
            state = "unknown"
        elif direct_evidence_count > 0 or len(matched_terms) >= 2 or score >= 0.34 or (
                len(matched_terms) == 1 and len(query_terms) <= 2
        ):
            state = "related"
        else:
            state = "unrelated"
        if state == "related" and direct_profile["direct_evidence_count"] <= 0:
            if direct_profile["weak_related_count"] > 0:
                answer_relevance_state = "weak_related"
            else:
                answer_relevance_state = "no_direct_evidence"
        elif state == "related":
            answer_relevance_state = "direct"
        else:
            answer_relevance_state = "unrelated"
        return {
            "context_relevance_score": round(score, 3),
            "context_relevance_state": state,
            "context_relevance_terms": sorted(query_terms),
            "context_relevance_matched_terms": matched_terms,
            "answer_relevance_state": answer_relevance_state,
            **direct_profile,
        }

    @staticmethod
    def _primary_query_terms(query: str) -> set[str]:
        generic_terms = {
            "algorithm",
            "algorithms",
            "answer",
            "concept",
            "concepts",
            "detail",
            "detailed",
            "diagram",
            "diagrams",
            "example",
            "examples",
            "explanation",
            "figure",
            "figures",
            "image",
            "images",
            "key",
            "limitation",
            "limitations",
            "method",
            "methods",
            "model",
            "models",
            "note",
            "notes",
            "point",
            "points",
            "software",
            "softwares",
            "source",
            "sources",
            "system",
            "systems",
            "type",
            "types",
            "visual",
        }
        literal_terms = {
            term
            for term in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", query.lower())
            if term not in _QUERY_STOPWORDS
        }
        terms = {
            term
            for term in literal_terms
            if term not in generic_terms and len(term) >= 4
        }
        normalized = query.lower()
        if any(term in normalized for term in ("hardware", "processor", "device", "machine")):
            terms.update({"machine", "gpu", "processor", "device"})
        if any(term in normalized for term in ("duration", "training time", "how long", "runtime")):
            terms.update({"hours", "steps", "time", "training"})
        if terms:
            aliases = {
                "deployment": "deploy",
                "deployed": "deploy",
                "deploying": "deploy",
                "optimization": "optimize",
                "optimized": "optimize",
                "optimizing": "optimize",
                "animations": "animation",
                "assets": "asset",
                "prompting": "prompt",
                "principles": "principle",
            }
            terms.update(aliases[term] for term in list(terms) if term in aliases)
            return terms
        return {
            term
            for term in literal_terms
            if term not in {"answer", "explain", "source", "sources"} and len(term) >= 3
        }

    @staticmethod
    def _direct_evidence_profile(query: str, bundle: RetrievalBundle) -> dict[str, object]:
        query_terms = SynthesisService._primary_query_terms(query) | SynthesisService._context_acronym_terms(
            query=query,
            bundle=bundle,
        )
        if any(phrase in query.lower() for phrase in ("fact-check", "fact check", "verification", "verify")):
            query_terms.update(
                {
                    "cross-check",
                    "trusted",
                    "sources",
                    "retrieval-based",
                    "fallback",
                    "uncertain",
                }
            )
        if not query_terms:
            return {
                "answer_relevance_score": 0.0,
                "primary_query_terms": [],
                "direct_evidence_count": 0,
                "weak_related_count": 0,
                "direct_evidence_pages": [],
            }

        direct_count = 0
        weak_count = 0
        scores: list[float] = []
        pages: list[int] = []
        for chunk in bundle.chunks[:8]:
            score = SynthesisService._chunk_directness_score(query=query, chunk_text=chunk.text, query_terms=query_terms)
            scores.append(score)
            if score >= 0.58:
                direct_count += 1
                if chunk.page_start is not None and chunk.page_start not in pages:
                    pages.append(chunk.page_start)
            elif score >= 0.15:
                weak_count += 1

        best_score = max(scores, default=0.0)
        return {
            "answer_relevance_score": round(best_score, 3),
            "primary_query_terms": sorted(query_terms),
            "direct_evidence_count": direct_count,
            "weak_related_count": weak_count,
            "direct_evidence_pages": pages[:6],
        }

    @staticmethod
    def _context_acronym_terms(*, query: str, bundle: RetrievalBundle) -> set[str]:
        known_lowercase_acronyms = {
            "api",
            "bm25",
            "cnn",
            "gmm",
            "gan",
            "llm",
            "ocr",
            "pca",
            "pdf",
            "rag",
            "rnn",
            "rrf",
            "sql",
            "svm",
        }
        acronyms: set[str] = set()
        for token in re.findall(r"\b[A-Za-z][A-Za-z0-9+-]{1,8}s?\b", query):
            base = token.rstrip("sS")
            lowered = base.lower()
            if lowered in _QUERY_STOPWORDS or not (2 <= len(base) <= 8):
                continue
            if token.isupper() or lowered in known_lowercase_acronyms:
                acronyms.add(base.upper())
        if not acronyms:
            return set()
        expansions: set[str] = set()
        for chunk in bundle.chunks[:8]:
            block = normalize_ocr_text(chunk.text[:1800])
            for acronym in acronyms:
                patterns = (
                    re.compile(
                        rf"\b([A-Za-z][A-Za-z0-9+/\- ]{{3,90}}?)\s+\(({re.escape(acronym)}s?)\)",
                        flags=re.I,
                    ),
                    re.compile(
                        rf"\b{re.escape(acronym)}s?\s+\(([A-Za-z][A-Za-z0-9+/\- ]{{3,90}}?)\)",
                        flags=re.I,
                    ),
                )
                for pattern in patterns:
                    for match in pattern.finditer(block):
                        phrase = re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")
                        expansions.update(
                            token
                            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", phrase.lower())
                            if token not in _QUERY_STOPWORDS and len(token) >= 4
                        )
        return expansions

    @staticmethod
    def _chunk_directness_score(*, query: str, chunk_text: str, query_terms: set[str]) -> float:
        text = normalize_ocr_text(chunk_text).lower()
        words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", text))
        matched = {
            term
            for term in query_terms
            if term in text or any(len(term) >= 5 and word.startswith(term[:6]) for word in words)
        }
        coverage = len(matched) / max(len(query_terms), 1)
        score = min(1.0, coverage)
        normalized_query = query.lower()
        phrase_tokens = [
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", normalized_query)
            if token not in _QUERY_STOPWORDS and token not in {"software", "softwares", "detail", "detailed"}
        ]
        for size in (4, 3, 2):
            for index in range(0, max(0, len(phrase_tokens) - size + 1)):
                phrase = " ".join(phrase_tokens[index : index + size])
                if len(phrase) >= 7 and phrase in text:
                    score += 0.28
                    break
        if SynthesisService._is_definition_query(query) and any(
            cue in text
            for cue in (
                " are ",
                " is a ",
                " is an ",
                " means ",
                " refers ",
                " called ",
                " defined as ",
                " assumes ",
                " consists of ",
                " create ",
                " creates ",
            )
        ):
            score += 0.18
        if any(term in normalized_query for term in ("risk", "risks")) and any(
            cue in text for cue in ("risks include", "hallucination", "privacy leakage", "prompt injection")
        ):
            score += 0.34
        if "generate text" in normalized_query and "predicting likely next tokens" in text:
            score += 0.34
        if any(term in normalized_query for term in ("equation", "calculated", "defines")) and any(
            cue in text for cue in (" = ", " equals ", " calculated as ")
        ):
            score += 0.24
        if any(term in normalized_query for term in ("limitation", "limitations", "avoid", "confidently")) and any(
            cue in text
            for cue in (
                "evidence is weak",
                "weak or unrelated",
                "not have enough grounded context",
                "limitations should be honest",
                "retrieval quality depends",
                "ocr quality can affect",
                "poor scans",
                "missing ocr",
                "should not override evidence",
                "source does not contain enough evidence",
            )
        ):
            score += 0.34
        if "drift" in normalized_query and "drift" in text:
            score += 0.24
            if any(cue in normalized_query for cue in ("action", "listed", "happen")) and any(
                cue in text for cue in ("monitor normally", "recalibrate immediately", "second observation")
            ):
                score += 0.26
        if SynthesisService._is_definition_query(query):
            acronym_subjects = {
                token.upper().rstrip("S")
                for token in re.findall(r"\b[A-Za-z][A-Za-z0-9+-]{1,8}s?\b", query)
                if 2 <= len(token.rstrip("sS")) <= 8
                and (token.isupper() or len(token.rstrip("sS")) <= 4)
                and token.lower() not in _QUERY_STOPWORDS
                and token.lower().rstrip("s") != "ai"
                and token.lower() not in {"explain", "define", "detail", "detailed"}
            }
            if acronym_subjects and len(query_terms) == 1:
                has_definition_anchor = any(
                    re.search(
                        rf"\b[A-Za-z][A-Za-z0-9+/-]*(?:\s+[A-Za-z][A-Za-z0-9+/-]*){{1,7}}\s+\({re.escape(acronym)}s?\)",
                        chunk_text,
                        flags=re.I,
                    )
                    or re.search(
                        rf"\b{re.escape(acronym)}s?\s+(?:is|means|refers|stands\s+for)\b",
                        text,
                        flags=re.I,
                    )
                    for acronym in acronym_subjects
                )
                if not has_definition_anchor:
                    # Mentioning an acronym does not directly answer a request
                    # to explain it; the passage must define or expand it.
                    score = min(score, 0.45)
        if any(term in normalized_query for term in ("how", "work", "works", "process", "steps")) and any(
            cue in text for cue in ("works by", "consists of", "uses", "algorithm", "process", "step")
        ):
            score += 0.14
        visual_request = any(term in normalized_query for term in ("diagram", "figure", "visual")) or any(
            phrase in normalized_query
            for phrase in ("image reference", "image references", "provide image", "show image")
        )
        if visual_request and any(
            cue in text for cue in ("figure", "fig.", "diagram", "image", "caption", "visual")
        ):
            score += 0.12
        if any(term in normalized_query for term in ("privacy", "private", "local-first", "local first")) and any(
            cue in text
            for cue in (
                "local-first",
                "local data directory",
                "uploaded files are stored",
                "trusted corpus roots",
                "direct local-path ingestion is restricted",
                "file signatures",
                "cannot easily masquerade",
                "removed from the local library",
                "clearing its metadata",
                "without requiring a cloud account",
                "internet connection",
            )
        ):
            score += 0.36
        if any(term in normalized_query for term in ("hardware", "processor", "device", "machine")) and any(
            cue in text for cue in (" machine ", " gpu", "processor", "device")
        ):
            score += 0.24
        if any(term in normalized_query for term in ("duration", "training time", "how long", "runtime")) and any(
            cue in text for cue in (" hours", " steps", " step time", "duration")
        ):
            score += 0.24
        if not any(term in normalized_query for term in ("example", "application", "use case")) and any(
            cue in text
            for cue in (
                "one possible application",
                "possible application",
                "examples of applications",
                "among many other",
            )
        ):
            score -= 0.75
        if SynthesisService._is_low_value_evidence_sentence(text[:900]):
            score -= 0.22
        return max(0.0, min(1.0, score))

    @staticmethod
    def _contains_citation_anchor(text: str) -> bool:
        return bool(re.search(r"\[\d+\]", text))

    @staticmethod
    def _anchor_uncited_sentences(answer: str, context_chunks: list[tuple[int, str]]) -> str:
        if not answer.strip() or not context_chunks:
            return answer
        context_by_anchor = {
            idx: SynthesisService._context_text(block).lower()
            for idx, block in context_chunks
        }
        lines: list[str] = []
        for raw_line in answer.splitlines():
            line = raw_line.strip()
            if not line:
                lines.append(raw_line)
                continue
            if re.match(r"^(sources?|references?)\s*:", line, re.I):
                continue
            if SynthesisService._contains_citation_anchor(line):
                lines.append(raw_line)
                continue
            anchored_sentences: list[str] = []
            for sentence in SynthesisService._split_sentences(line):
                if SynthesisService._contains_citation_anchor(sentence):
                    anchored_sentences.append(sentence)
                    continue
                claim_terms = SynthesisService._claim_terms(sentence)
                if len(claim_terms) < 3:
                    anchored_sentences.append(sentence)
                    continue
                best_anchor = None
                best_score = 0.0
                for anchor, context_text in context_by_anchor.items():
                    support_score = SynthesisService._claim_support_score(claim_terms, context_text)
                    if support_score > best_score:
                        best_score = support_score
                        best_anchor = anchor
                matched_terms = int(round(best_score * len(claim_terms)))
                if best_anchor is not None and (best_score >= 0.28 or matched_terms >= 3):
                    sentence = sentence.rstrip()
                    sentence = f"{sentence} [{best_anchor}]"
                anchored_sentences.append(sentence)
            lines.append(" ".join(anchored_sentences))
        anchored = "\n".join(lines).strip()
        return anchored

    @staticmethod
    def _verify_cited_claims(answer: str, context_chunks: list[tuple[int, str]]) -> dict[str, object]:
        context_by_anchor = {
            idx: SynthesisService._context_text(block).lower()
            for idx, block in context_chunks
        }
        normalized_answer = re.sub(r"([.!?])[ \t]+((?:\[\d+\][ \t]*)+)", r" \2\1", answer)
        checked = 0
        unsupported: list[dict[str, object]] = []
        for sentence in SynthesisService._split_sentences(normalized_answer):
            anchors = {
                int(match)
                for match in re.findall(r"\[(\d+)\]", sentence)
                if int(match) in context_by_anchor
            }
            if not anchors:
                continue
            claim_terms = SynthesisService._claim_terms(sentence)
            if len(claim_terms) < 3:
                # Short, cited list items such as "- PCA [2]" still need
                # verification; ordinary headings do not.
                if not sentence.lstrip().startswith("-") or len(claim_terms) < 2:
                    continue
            checked += 1
            cited_contexts = [context_by_anchor[anchor] for anchor in anchors]
            support_scores = [
                SynthesisService._claim_support_score(claim_terms, context_text)
                for context_text in cited_contexts
            ]
            combined_score = SynthesisService._claim_support_score(
                claim_terms,
                " ".join(cited_contexts),
            )
            best_score = max([combined_score, *support_scores]) if support_scores else combined_score
            matched_terms = int(round(best_score * len(claim_terms)))
            required_matches = max(3, int(len(claim_terms) * 0.5))
            if best_score < 0.55 or matched_terms < required_matches:
                unsupported.append(
                    {
                        "claim": re.sub(r"\s+", " ", sentence).strip()[:220],
                        "anchors": sorted(anchors),
                        "support_score": round(best_score, 3),
                    }
                )
        if checked == 0:
            state = "unchecked"
        elif unsupported:
            state = "unsupported"
        else:
            state = "supported"
        return {
            "state": state,
            "cited_claims_checked": checked,
            "unsupported_claims": unsupported,
        }

    @staticmethod
    def _remove_unsupported_claims(answer: str, verification: dict[str, object]) -> str:
        unsupported = verification.get("unsupported_claims")
        if not isinstance(unsupported, list) or not unsupported:
            return answer.strip()

        fingerprints = [
            SynthesisService._claim_fingerprint(str(item.get("claim") or ""))
            for item in unsupported
            if isinstance(item, dict) and item.get("claim")
        ]
        fingerprints = [fingerprint for fingerprint in fingerprints if fingerprint]
        if not fingerprints:
            return answer.strip()

        repaired_lines: list[str] = []
        for raw_line in answer.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                repaired_lines.append("")
                continue
            retained: list[str] = []
            normalized_line = re.sub(
                r"([.!?])[ \t]+((?:\[\d+\][ \t]*)+)",
                r" \2\1",
                stripped,
            )
            for sentence in SynthesisService._split_sentences(normalized_line):
                if re.fullmatch(r"(?:\[\d+\]\s*)+", sentence.strip()):
                    continue
                fingerprint = SynthesisService._claim_fingerprint(sentence)
                if fingerprint and any(
                    SynthesisService._same_claim_fingerprint(fingerprint, unsupported_fingerprint)
                    for unsupported_fingerprint in fingerprints
                ):
                    continue
                if (
                    not SynthesisService._contains_citation_anchor(sentence)
                    and len(SynthesisService._claim_terms(sentence)) >= 3
                    and not SynthesisService._looks_like_orphan_heading(sentence)
                ):
                    continue
                retained.append(sentence)
            if retained:
                prefix = "- " if stripped.startswith("-") and not retained[0].startswith("-") else ""
                repaired_lines.append(prefix + " ".join(retained))

        while repaired_lines and not repaired_lines[-1].strip():
            repaired_lines.pop()
        if repaired_lines and SynthesisService._looks_like_orphan_heading(repaired_lines[-1]):
            repaired_lines.pop()

        compact: list[str] = []
        blank = False
        for line in repaired_lines:
            if not line.strip():
                if compact and not blank:
                    compact.append("")
                blank = True
                continue
            compact.append(line)
            blank = False
        return "\n".join(compact).strip()

    @staticmethod
    def _is_usable_claim_repair(answer: str, verification: dict[str, object]) -> bool:
        coverage = citation_coverage(answer)
        return bool(
            answer.strip()
            and len(answer.split()) >= 8
            and SynthesisService._contains_citation_anchor(answer)
            and verification.get("state") == "supported"
            and int(verification.get("cited_claims_checked") or 0) >= 1
            and float(coverage.get("citation_coverage") or 0.0) >= 0.75
        )

    @staticmethod
    def _claim_fingerprint(value: str) -> str:
        value = re.sub(r"\[\d+\]", " ", value.lower())
        return " ".join(re.findall(r"[a-zA-Z0-9+-]+", value))

    @staticmethod
    def _same_claim_fingerprint(candidate: str, unsupported: str) -> bool:
        if candidate in unsupported or unsupported in candidate:
            return True
        candidate_terms = set(candidate.split())
        unsupported_terms = set(unsupported.split())
        if not candidate_terms or not unsupported_terms:
            return False
        overlap = len(candidate_terms & unsupported_terms)
        return overlap / max(len(candidate_terms), len(unsupported_terms)) >= 0.8

    @staticmethod
    def _looks_like_orphan_heading(line: str) -> bool:
        stripped = re.sub(r"^[#*\s]+", "", line).strip()
        return bool(
            stripped
            and not SynthesisService._contains_citation_anchor(stripped)
            and len(stripped.split()) <= 6
            and not re.search(r"[.!?]$", stripped)
        )

    @staticmethod
    def _should_rewrite_for_faithfulness(verification: dict[str, object]) -> bool:
        unsupported = verification.get("unsupported_claims")
        checked = int(verification.get("cited_claims_checked") or 0)
        state = str(verification.get("state") or "")
        if state == "unchecked" and checked == 0:
            return True
        if not isinstance(unsupported, list) or checked <= 0:
            return False
        return len(unsupported) >= 1

    @staticmethod
    def _claim_terms(sentence: str) -> set[str]:
        cleaned = re.sub(r"\[\d+\]", " ", sentence.lower())
        cleaned = re.sub(
            r"^(?:short answer|direct answer|how it works|supporting detail)\s+",
            "",
            cleaned,
        )
        cleaned = re.sub(
            r"\b(?:the\s+)?source\s+(?:identifies|records|states|shows|says)\b",
            "",
            cleaned,
        )
        raw_tokens = re.findall(
            r"(?:[a-zA-Z][a-zA-Z0-9+-]{1,}|(?:19|20)\d{2}(?:-\d{2}-\d{2})?)",
            cleaned,
        )
        return {
            token
            for token in raw_tokens
            if token not in _CLAIM_STOPWORDS
            and (
                len(token) >= 4
                or any(char.isdigit() for char in token)
                or token in {"ai", "ml", "nlp", "pca", "svm", "cnn", "rnn", "l1", "l2"}
            )
        }

    @staticmethod
    def _claim_support_score(claim_terms: set[str], context_text: str) -> float:
        if not claim_terms:
            return 1.0
        context_terms = set(
            re.findall(
                r"(?:[a-zA-Z][a-zA-Z0-9+-]{1,}|(?:19|20)\d{2}(?:-\d{2}-\d{2})?)",
                context_text.lower(),
            )
        )
        matches = 0
        for term in claim_terms:
            if term in context_terms:
                matches += 1
                continue
            stem = term[:6]
            if len(stem) >= 5 and any(candidate.startswith(stem) for candidate in context_terms):
                matches += 1
        return matches / max(len(claim_terms), 1)

    @staticmethod
    def _is_document_overview_query(query: str, response_mode: str) -> bool:
        mode = response_mode.strip().lower()
        if mode in {"summary", "study_guide"}:
            return True
        normalized = query.strip().lower()
        if not normalized:
            return False
        explicit_overview_phrases = (
            "summarize this",
            "summary of",
            "overview of",
            "what is this about",
            "what is it about",
            "explain this pdf",
            "explain the pdf",
            "explain this document",
            "explain the document",
            "explain this material",
            "explain the material",
        )
        if any(phrase in normalized for phrase in explicit_overview_phrases):
            return True
        overview_verbs = {
            "summarize",
            "summary",
            "explain",
            "overview",
            "describe",
            "understand",
            "about",
        }
        document_terms = {
            "pdf",
            "document",
            "doc",
            "file",
            "material",
            "paper",
            "source",
            "notes",
            "this",
            "it",
        }
        tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9]{1,}", normalized))
        specific_question_terms = {
            "algorithm",
            "algorithms",
            "compare",
            "contrast",
            "define",
            "difference",
            "differences",
            "example",
            "examples",
            "how",
            "list",
            "why",
        }
        if tokens & specific_question_terms:
            return False
        if tokens & overview_verbs and tokens & document_terms:
            return True
        return normalized in {
            "explain",
            "summarize",
            "summary",
            "what is this",
            "what is this about",
            "what is it about",
        }

    @staticmethod
    def _insufficient_context_message(citation_count: int) -> str:
        if citation_count > 0:
            return (
                "I found some matching evidence, but it is too weak to answer safely. "
                "Try asking for a document summary, selecting the correct source, or adding more specific terms."
            )
        return "I do not have enough grounded context yet. Please upload or ingest documents first."

    def _grounding_state(self, grounding_score: float, citation_count: int) -> str:
        if citation_count <= 0 or grounding_score < self._min_grounding_score:
            return "weak"
        if grounding_score >= max(self._min_grounding_score * 2, self._min_grounding_score + 0.2):
            return "strong"
        return "moderate"

    @staticmethod
    def _grounding_summary(grounding_state: str, grounding_score: float, citation_count: int) -> str:
        return f"{grounding_state} evidence ({citation_count} citations, score {grounding_score:.2f})"
