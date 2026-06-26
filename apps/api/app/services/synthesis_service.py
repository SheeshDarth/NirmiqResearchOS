import re

from app.adapters.llm.generator import Generator
from app.core.config import Settings
from app.domain.citation_coverage import citation_coverage
from app.domain.models import RetrievalBundle
from app.domain.retrieval_policy import RetrievalPolicy


_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "answer",
    "about",
    "are",
    "brief",
    "briefly",
    "cite",
    "cited",
    "citation",
    "citations",
    "corpus",
    "create",
    "deep",
    "does",
    "draft",
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
    "study",
    "the",
    "this",
    "to",
    "say",
    "says",
    "what",
    "when",
    "where",
    "which",
    "who",
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
        top_grounding_score = max((float(chunk.score) for chunk in bundle.chunks), default=0.0)
        citation_count = len(bundle.chunks)
        grounding_state = self._grounding_state(top_grounding_score, citation_count)
        overview_query = self._is_document_overview_query(query, response_mode)
        relevance_query = self._relevance_query(
            query=query,
            response_mode=response_mode,
            exam_context=exam_context,
        )
        context_relevance = self._context_relevance(query=relevance_query, bundle=bundle)
        strict_relevance_required = response_mode.strip().lower() == "general_chat" or not overview_query
        low_score_overview = grounding_state == "weak" and overview_query and citation_count >= 2
        if low_score_overview:
            grounding_state = "moderate"
        if strict_relevance_required and context_relevance["context_relevance_state"] == "unrelated":
            return (
                (
                    "I do not have enough relevant uploaded context to answer that safely. "
                    "Upload source material for this question, select the right document, or use an external/internet model "
                    "later when that optional mode is available."
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
                    **context_relevance,
                },
            )

        selected = self._select_context(bundle)
        prompt = self._build_grounded_prompt(
            query,
            selected,
            response_mode=response_mode,
            exam_profile=exam_profile,
            exam_context=exam_context,
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

        if not generated:
            generated = self._fallback_answer(
                query=query,
                context_chunks=selected,
                response_mode=response_mode,
                exam_context=exam_context,
            )
        else:
            generated = self._anchor_uncited_sentences(generated, selected)

        verification = self._verify_cited_claims(generated, selected)
        answer_rewritten = False
        if self._should_rewrite_for_faithfulness(verification):
            generated = self._fallback_answer(
                query=query,
                context_chunks=selected,
                response_mode=response_mode,
                exam_context=exam_context,
            )
            fallback_verification = self._verify_cited_claims(generated, selected)
            verification = {
                **fallback_verification,
                "original_unsupported_claims": verification["unsupported_claims"],
                "original_cited_claims_checked": verification["cited_claims_checked"],
            }
            answer_rewritten = True

        meta = {
            "generation_backend": self._generator.last_backend,
            "generation_model_requested": getattr(self._generator, "last_model_requested", None),
            "generation_model_used": getattr(self._generator, "last_model_used", None),
            "generation_model_fallback": getattr(self._generator, "last_model_fallback", False),
            "generation_error": getattr(self._generator, "last_error", None),
            "grounding_score": top_grounding_score,
            "citation_count": citation_count,
            "context_chunks_used": len(selected),
            "grounding_state": grounding_state,
            "grounding_summary": self._grounding_summary(grounding_state, top_grounding_score, citation_count),
            "document_overview_request": overview_query,
            "low_score_overview_allowed": low_score_overview,
            **context_relevance,
            "exam_profile_used": bool(exam_profile),
            "exam_context_used": bool(
                exam_context and (exam_context.get("questions") or exam_context.get("diagrams"))
            ),
            "citation_verification_state": verification["state"],
            "generation_temperature": generation_temperature,
            **citation_coverage(generated),
            "cited_claims_checked": verification["cited_claims_checked"],
            "unsupported_claims": verification["unsupported_claims"],
            "original_cited_claims_checked": verification.get("original_cited_claims_checked"),
            "original_unsupported_claims": verification.get("original_unsupported_claims", []),
            "answer_rewritten_for_faithfulness": answer_rewritten,
            **self._citation_context_meta(
                answer=generated,
                bundle=bundle,
                selected_context=selected,
            ),
        }
        return (generated, True, meta)

    def _generation_temperature(
        self,
        *,
        response_mode: str,
        context_chunks: list[tuple[int, str]],
    ) -> float:
        mode = response_mode.strip().lower()
        total_words = sum(len(self._context_text(block).split()) for _, block in context_chunks)
        long_form_modes = {"deep_research", "research_paper", "study_guide"}
        if mode in long_form_modes and total_words >= 900:
            return max(0.0, min(1.0, self._settings.generator_temperature_long_context))
        return max(0.0, min(1.0, self._settings.generator_temperature_grounded))

    def _select_context(self, bundle: RetrievalBundle) -> list[tuple[int, str]]:
        selected: list[tuple[int, str]] = []
        used_words = 0
        for idx, chunk in enumerate(bundle.chunks[:8], start=1):
            text = chunk.text.strip()
            if not text:
                continue
            chunk_words = len(text.split())
            if used_words + chunk_words > self._max_context_tokens and selected:
                break
            block = (
                f"[{idx}] doc={chunk.document_id} score={chunk.score:.3f} "
                f"source={chunk.source} pages={chunk.page_start or '?'}-{chunk.page_end or '?'}\n"
                f"{text}"
            )
            selected.append((idx, block))
            used_words += chunk_words
        return selected

    @staticmethod
    def _citation_context_meta(
        *,
        answer: str,
        bundle: RetrievalBundle,
        selected_context: list[tuple[int, str]],
    ) -> dict[str, object]:
        selected_anchors = [anchor for anchor, _ in selected_context]
        chunks_by_anchor = {
            anchor: chunk
            for anchor, chunk in enumerate(bundle.chunks[:8], start=1)
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
    ) -> str:
        context = "\n\n".join(block for _, block in context_blocks)
        mode_instruction = SynthesisService._mode_instruction(response_mode)
        exam_instruction = SynthesisService._exam_instruction(exam_profile)
        artifact_instruction = SynthesisService._exam_artifact_instruction(exam_context)
        return (
            "You are NIRMIQ local research assistant.\n"
            "Use ONLY the context below. Do not invent facts.\n"
            "If evidence is insufficient, say so plainly.\n"
            "Cite claims with [n] where n is the context block number.\n"
            "Prefer higher-scoring context blocks when multiple sources support the same claim.\n"
            "Answer the user's exact question, not a generic document summary.\n"
            "Use this compact answer contract whenever possible: Direct answer, Key points, Evidence note.\n"
            "If the user asks for algorithms, examples, steps, or a list, answer as a concise list and cite each item.\n"
            "Keep paragraphs short and avoid dense textbook dumps.\n"
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
        exam_context: dict[str, object] | None = None,
    ) -> str:
        mode = response_mode.strip().lower()
        if SynthesisService._is_document_overview_query(query, response_mode):
            return SynthesisService._fallback_document_summary(
                query=query,
                context_chunks=context_chunks,
            )
        if mode == "research_paper":
            return SynthesisService._fallback_research_paper(query=query, context_chunks=context_chunks)
        if mode == "study_guide" and exam_context and exam_context.get("questions"):
            return SynthesisService._fallback_study_guide(context_chunks=context_chunks, exam_context=exam_context)
        if SynthesisService._is_list_or_algorithm_query(query):
            return SynthesisService._fallback_list_answer(
                query=query,
                context_chunks=context_chunks,
                response_mode=response_mode,
            )
        if SynthesisService._is_definition_solution_query(query):
            return SynthesisService._fallback_definition_solution_answer(
                query=query,
                context_chunks=context_chunks,
            )

        query_terms = SynthesisService._query_terms(query)
        candidates: list[tuple[float, int, str]] = []
        for idx, block in context_chunks[:6]:
            text = SynthesisService._context_text(block)
            for sentence_index, sentence in enumerate(SynthesisService._split_sentences(text)[:10]):
                if len(sentence.split()) < 6:
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
    def _mode_instruction(response_mode: str) -> str:
        mode = response_mode.strip().lower()
        if mode == "exam_answer":
            return "Format as an exam-ready answer with definition, key points, and cited support."
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
        if mode == "research_paper":
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
        marks = exam_profile.get("marks") or 10
        answer_style = str(exam_profile.get("answer_style") or "exam-ready")
        content_type = str(exam_profile.get("content_type") or "conceptual")
        instructions = str(exam_profile.get("instructions") or "").strip()
        parts = [
            "Exam Lab settings:",
            f"- Target marks: {marks}",
            f"- Answer style: {answer_style}",
            f"- Content type: {content_type}",
            "- Use only retrieved source context; do not add outside textbook knowledge.",
            "- If diagrams are requested but no source diagram context is provided, say that no source diagram was available.",
        ]
        if instructions:
            parts.append(f"- Custom instructions: {instructions}")
        return "\n".join(parts)

    @staticmethod
    def _exam_artifact_instruction(exam_context: dict[str, object] | None) -> str:
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
                path = item.get("image_path")
                parts.append(f"- D{index}: page {page}, {caption}, local path: {path}")
            parts.append("When useful, mention diagram IDs like D1 with page numbers instead of inventing drawings.")
        return "\n".join(parts)

    @staticmethod
    def _fallback_study_guide(
        context_chunks: list[tuple[int, str]], exam_context: dict[str, object]
    ) -> str:
        questions = [item for item in exam_context.get("questions", []) if isinstance(item, dict)]
        diagrams = [item for item in exam_context.get("diagrams", []) if isinstance(item, dict)]
        if not questions:
            return "Study guide from the retrieved passages:\n- No imported questions were available."

        sections = ["Study guide from imported questions and retrieved passages:"]
        for index, item in enumerate(questions[:8], start=1):
            question = str(item.get("question") or f"Question {index}")
            marks = item.get("marks")
            terms = SynthesisService._query_terms(question)
            evidence = SynthesisService._best_evidence_sentences(context_chunks, terms, limit=2)
            mark_label = f" ({marks} marks)" if marks else ""
            sections.append(f"\nQ{index}. {question}{mark_label}")
            if evidence:
                sections.extend(f"- {sentence} [{anchor}]" for anchor, sentence in evidence)
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
    def _best_evidence_sentences(
        context_chunks: list[tuple[int, str]], query_terms: set[str], limit: int
    ) -> list[tuple[int, str]]:
        candidates: list[tuple[float, int, str]] = []
        for idx, block in context_chunks[:8]:
            text = SynthesisService._context_text(block)
            for sentence_index, sentence in enumerate(SynthesisService._split_sentences(text)[:10]):
                if len(sentence.split()) < 6:
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
                if len(sentence.split()) < 7:
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
    def _dedupe_scored_sentences(
        scored: list[tuple[float, int, str]],
        *,
        limit: int,
    ) -> list[tuple[int, str]]:
        selected: list[tuple[int, str]] = []
        seen: set[str] = set()
        for _, idx, sentence in sorted(scored, key=lambda item: item[0], reverse=True):
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
        if mode == "exam_answer":
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
        asks_solution = any(term in normalized for term in ("reduce", "reduced", "prevent", "avoid", "fix"))
        return asks_definition and asks_solution

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
        if mode in {"exam_answer", "revision_notes"}:
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
        return bool(
            re.search(r"\b(list|few|some|examples?|algorithms?|types?|methods?|techniques?)\b", normalized)
        )

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
        sections.append(f"The uploaded material supports the following points. [{evidence[0][0]}]")
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
                if len(cleaned.split()) < 8 or cleaned in seen:
                    continue
                seen.add(cleaned)
                selected.append((idx, cleaned))
                if len(selected) >= limit:
                    return selected
        return selected

    @staticmethod
    def _context_text(block: str) -> str:
        lines = block.splitlines()
        text = " ".join(lines[1:] if len(lines) > 1 else lines)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        normalized = re.sub(r"\n+", " ", text)
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
        sentence_lower = sentence.lower()
        return float(
            sum(
                1
                for term in query_terms
                if term in sentence_lower or any(word.startswith(term[:5]) for word in sentence_lower.split())
            )
        )

    @staticmethod
    def _context_relevance(query: str, bundle: RetrievalBundle) -> dict[str, object]:
        query_terms = SynthesisService._query_terms(query)
        context_terms: set[str] = set()
        for chunk in bundle.chunks[:5]:
            context_terms.update(re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", chunk.text.lower()))

        matched_terms = sorted(
            term
            for term in query_terms
            if term in context_terms
            or any(len(term) >= 5 and candidate.startswith(term[:6]) for candidate in context_terms)
        )
        score = len(matched_terms) / max(len(query_terms), 1)
        if not query_terms:
            state = "unknown"
        elif len(matched_terms) >= 2 or score >= 0.34 or (
            len(matched_terms) == 1 and len(query_terms) <= 2
        ):
            state = "related"
        else:
            state = "unrelated"
        return {
            "context_relevance_score": round(score, 3),
            "context_relevance_state": state,
            "context_relevance_terms": sorted(query_terms),
            "context_relevance_matched_terms": matched_terms,
        }

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
        any_anchor = False
        for raw_line in answer.splitlines():
            line = raw_line.strip()
            if not line:
                lines.append(raw_line)
                continue
            if re.match(r"^(sources?|references?)\s*:", line, re.I):
                continue
            if SynthesisService._contains_citation_anchor(line):
                lines.append(raw_line)
                any_anchor = True
                continue
            anchored_sentences: list[str] = []
            for sentence in SynthesisService._split_sentences(line):
                if SynthesisService._contains_citation_anchor(sentence):
                    anchored_sentences.append(sentence)
                    any_anchor = True
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
                    any_anchor = True
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
                continue
            checked += 1
            support_scores = [
                SynthesisService._claim_support_score(claim_terms, context_by_anchor[anchor])
                for anchor in anchors
            ]
            best_score = max(support_scores) if support_scores else 0.0
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
        raw_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{1,}", cleaned)
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
        context_terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+-]{1,}", context_text.lower()))
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
        if mode == "summary":
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
