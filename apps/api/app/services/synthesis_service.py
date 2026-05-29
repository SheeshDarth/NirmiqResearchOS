import re

from app.adapters.llm.generator import Generator
from app.core.config import Settings
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
    "for",
    "from",
    "give",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "the",
    "this",
    "to",
    "what",
    "with",
}


class SynthesisService:
    def __init__(self, settings: Settings, policy: RetrievalPolicy, generator: Generator) -> None:
        self._settings = settings
        self._policy = policy
        self._generator = generator
        self._min_grounding_score = policy.min_grounding_score
        self._max_context_tokens = policy.max_context_tokens

    async def synthesize(
        self, query: str, bundle: RetrievalBundle, response_mode: str = "research"
    ) -> tuple[str, bool, dict[str, object]]:
        top_grounding_score = float(bundle.chunks[0].score if bundle.chunks else 0.0)
        citation_count = len(bundle.chunks)
        grounding_state = self._grounding_state(top_grounding_score, citation_count)
        grounded = grounding_state != "weak"
        if not grounded:
            return (
                "I do not have enough grounded context yet. Please ingest documents first.",
                False,
                {
                    "generation_backend": "none",
                    "grounding_score": top_grounding_score,
                    "citation_count": citation_count,
                    "grounding_state": grounding_state,
                    "grounding_summary": "weak evidence - no answer generated",
                },
            )

        selected = self._select_context(bundle)
        prompt = self._build_grounded_prompt(query, selected, response_mode=response_mode)
        generated = await self._generator.answer(prompt=prompt, model=self._settings.generator_model_default)

        if not generated:
            generated = self._fallback_answer(query=query, context_chunks=selected, response_mode=response_mode)
        elif not self._contains_citation_anchor(generated):
            generated = generated.rstrip() + "\n\nSources: [1]"

        meta = {
            "generation_backend": self._generator.last_backend,
            "grounding_score": top_grounding_score,
            "citation_count": citation_count,
            "context_chunks_used": len(selected),
            "grounding_state": grounding_state,
            "grounding_summary": self._grounding_summary(grounding_state, top_grounding_score, citation_count),
        }
        return (generated, True, meta)

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
    def _build_grounded_prompt(
        query: str, context_blocks: list[tuple[int, str]], response_mode: str = "research"
    ) -> str:
        context = "\n\n".join(block for _, block in context_blocks)
        mode_instruction = SynthesisService._mode_instruction(response_mode)
        return (
            "You are NIRMIQ local research assistant.\n"
            "Use ONLY the context below. Do not invent facts.\n"
            "If evidence is insufficient, say so plainly.\n"
            "Cite claims with [n] where n is the context block number.\n"
            "Prefer higher-scoring context blocks when multiple sources support the same claim.\n"
            "Keep the answer concise and factual.\n"
            f"{mode_instruction}\n\n"
            f"User Query:\n{query}\n\n"
            f"Context:\n{context}\n\n"
            "Answer:"
        )

    @staticmethod
    def _fallback_answer(
        query: str, context_chunks: list[tuple[int, str]], response_mode: str = "research"
    ) -> str:
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

        bullets = "\n".join(f"- {sentence} [{idx}]" for idx, sentence in selected)
        heading = SynthesisService._fallback_heading(response_mode)
        return f"{heading}\n{bullets}"

    @staticmethod
    def _mode_instruction(response_mode: str) -> str:
        mode = response_mode.strip().lower()
        if mode == "exam_answer":
            return "Format as an exam-ready answer with definition, key points, and cited support."
        if mode == "revision_notes":
            return "Format as compact revision notes with headings and high-yield bullets."
        if mode == "study_guide":
            return "Format as a study guide with important questions, concise answers, and cited evidence."
        if mode == "important_questions":
            return "Generate likely exam questions only when they are supported by the context."
        if mode == "compare_concepts":
            return "Compare concepts in a small table or structured contrast when evidence supports it."
        if mode == "general_chat":
            return "Answer conversationally, but only from relevant uploaded document evidence. If the context is not relevant, abstain."
        if mode == "deep_research":
            return "Write a deeper research-style answer with clear sections, caveats, and evidence citations."
        return "Explain clearly for a student using short sections and citations."

    @staticmethod
    def _fallback_heading(response_mode: str) -> str:
        mode = response_mode.strip().lower()
        if mode == "exam_answer":
            return "Exam-ready answer from the retrieved passages:"
        if mode == "revision_notes":
            return "Revision notes from the retrieved passages:"
        if mode == "study_guide":
            return "Study guide from the retrieved passages:"
        if mode == "important_questions":
            return "Important question leads from the retrieved passages:"
        if mode == "compare_concepts":
            return "Grounded comparison from the retrieved passages:"
        if mode == "general_chat":
            return "I can answer this from the relevant uploaded material:"
        if mode == "deep_research":
            return "Deep research synthesis from the retrieved passages:"
        return "Based on the retrieved passages:"

    @staticmethod
    def _context_text(block: str) -> str:
        lines = block.splitlines()
        text = " ".join(lines[1:] if len(lines) > 1 else lines)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        return [
            sentence.strip(" -")
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if sentence.strip(" -")
        ]

    @staticmethod
    def _query_terms(query: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", query.lower())
            if token not in _QUERY_STOPWORDS
        }

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
    def _contains_citation_anchor(text: str) -> bool:
        return bool(re.search(r"\[\d+\]", text))

    def _grounding_state(self, grounding_score: float, citation_count: int) -> str:
        if citation_count <= 0 or grounding_score < self._min_grounding_score:
            return "weak"
        if grounding_score >= max(self._min_grounding_score * 2, self._min_grounding_score + 0.2):
            return "strong"
        return "moderate"

    @staticmethod
    def _grounding_summary(grounding_state: str, grounding_score: float, citation_count: int) -> str:
        return f"{grounding_state} evidence ({citation_count} citations, score {grounding_score:.2f})"
