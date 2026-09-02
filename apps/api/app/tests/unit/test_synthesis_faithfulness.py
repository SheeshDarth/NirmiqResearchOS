import asyncio

from app.core.config import Settings
from app.domain.models import RetrievalBundle, RetrievedChunk
from app.domain.retrieval_policy import RetrievalPolicy
from app.domain.answer_intelligence import build_answer_plan
from app.services.query_service import QueryService
from app.services.synthesis_service import SynthesisService
from app.domain.query_intent import QueryIntent


class FakeGenerator:
    def __init__(self, answer: str) -> None:
        self._answer = answer
        self.last_backend = "fake"
        self.temperature = 0.0

    async def answer(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> str:
        self.last_backend = "fake"
        self.temperature = temperature
        return self._answer


def _settings() -> Settings:
    settings = Settings.from_env()
    return settings.model_copy(update={"use_ollama_generation": False})


def _bundle() -> RetrievalBundle:
    return RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="NIRMIQ uses grounded retrieval and local citation-aware synthesis for academic documents.",
                score=1.0,
                page_start=1,
                page_end=1,
                source="bm25",
            )
        ],
        meta={},
    )


def test_unsupported_cited_generation_is_rewritten_to_grounded_fallback() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator("The moon is made of cheese and NIRMIQ proves it. [1]"),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert "moon" not in answer.lower()
    assert "grounded retrieval" in answer.lower()
    assert meta["answer_rewritten_for_faithfulness"] is True
    assert meta["citation_verification_state"] == "supported"
    assert meta["original_unsupported_claims"]


def test_supported_cited_generation_is_preserved() -> None:
    generated = "NIRMIQ uses grounded retrieval and citation-aware synthesis for academic documents. [1]"
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert answer == generated
    assert meta["answer_rewritten_for_faithfulness"] is False
    assert meta["citation_verification_state"] == "supported"
    assert meta["unsupported_claims"] == []


def test_mixed_generation_prunes_only_unsupported_claim() -> None:
    generated = (
        "Direct answer\n"
        "NIRMIQ uses grounded retrieval for academic documents. [1]\n\n"
        "Explanation\n"
        "NIRMIQ also uses local citation-aware synthesis for academic documents. [1]\n"
        "It also operates an interplanetary payment network. [1]"
    )
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="How does NIRMIQ answer academic questions?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert "grounded retrieval" in answer.lower()
    assert "citation-aware synthesis" in answer.lower()
    assert "interplanetary" not in answer.lower()
    assert meta["answer_repair_mode"] == "claim_pruned"
    assert meta["answer_rewritten_for_faithfulness"] is True
    assert meta["citation_verification_state"] == "supported"


def test_uncited_generated_sentences_are_anchored_to_best_context() -> None:
    generated = "NIRMIQ uses grounded retrieval and citation-aware synthesis for academic documents."
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert answer.endswith("[1]")
    assert meta["citation_coverage"] == 1.0
    assert meta["citation_verification_state"] == "supported"


def test_claim_to_span_verification_accepts_supported_claim() -> None:
    verification = SynthesisService._verify_claim_to_spans(
        "CNN architectures use convolutional layers for visual features. [1]",
        [(1, "[1] pages=1-1 CNN architectures use convolutional layers to learn visual features.")],
    )

    assert verification["state"] == "supported"
    assert verification["claims_checked"] == 1
    assert verification["claim_span_coverage"] == 1.0
    assert verification["claims_without_spans"] == []


def test_claim_to_span_verification_rejects_uncited_substantive_claim() -> None:
    verification = SynthesisService._verify_claim_to_spans(
        "CNN architectures use convolutional layers for visual features.",
        [(1, "[1] pages=1-1 CNN architectures use convolutional layers to learn visual features.")],
    )

    assert verification["state"] == "unsupported"
    assert len(verification["claims_without_spans"]) == 1
    assert verification["claim_span_coverage"] == 0.0


def test_claim_to_span_verification_rejects_irrelevant_citation() -> None:
    verification = SynthesisService._verify_claim_to_spans(
        "CNNs operate an interplanetary payment network. [1]",
        [(1, "[1] pages=1-1 CNNs use convolutional layers for visual feature extraction.")],
    )

    assert verification["state"] == "unsupported"
    assert len(verification["unsupported_claims"]) == 1
    assert verification["claims_without_spans"] == []


def test_claim_to_span_verification_ignores_honest_diagram_note() -> None:
    verification = SynthesisService._verify_claim_to_spans(
        "Diagram note\n- No source diagram was available from the uploaded material.",
        [],
    )

    assert verification["state"] == "unchecked"
    assert verification["claims_checked"] == 0

def test_claim_can_be_supported_jointly_by_multiple_citations() -> None:
    verification = SynthesisService._verify_cited_claims(
        (
            "CNN architectures combine convolutional layers with pooling layers "
            "to build visual feature representations. [1] [2]"
        ),
        [
            (1, "[1] pages=1-1\nCNN architectures use convolutional layers to learn visual features."),
            (2, "[2] pages=2-2\nPooling layers reduce feature-map dimensions in CNN architectures."),
        ],
    )

    assert verification["state"] == "supported"
    assert verification["unsupported_claims"] == []


def test_joint_citations_do_not_approve_unrelated_claims() -> None:
    verification = SynthesisService._verify_cited_claims(
        "CNNs operate an interplanetary payment network. [1] [2]",
        [
            (1, "[1] pages=1-1\nCNNs use convolutional layers for visual feature extraction."),
            (2, "[2] pages=2-2\nPooling layers reduce feature-map dimensions."),
        ],
    )

    assert verification["state"] == "unsupported"
    assert len(verification["unsupported_claims"]) == 1


def test_claim_repair_removes_uncited_orphan_fragments() -> None:
    answer = (
        "Direct answer\n"
        "Random forests average many decision trees to improve stability. [1]\n"
        "They operate an interplanetary payment network. [1]\n"
        "- Although the validation error remains lower vs."
    )
    verification = {
        "state": "unsupported",
        "cited_claims_checked": 2,
        "unsupported_claims": [
            {
                "claim": "They operate an interplanetary payment network. [1]",
                "anchors": [1],
                "support_score": 0.1,
            }
        ],
    }

    repaired = SynthesisService._remove_unsupported_claims(answer, verification)

    assert "interplanetary" not in repaired
    assert "validation error remains lower vs" not in repaired
    assert "average many decision trees" in repaired


def test_synthesis_reports_only_answer_cited_context_chunks() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="NIRMIQ stores uploaded material locally for private academic workflows.",
                score=1.0,
                page_start=1,
                page_end=1,
                source="bm25",
            ),
            RetrievedChunk(
                chunk_id="chunk-2",
                document_id="doc-1",
                text="NIRMIQ uses citation-aware synthesis to reduce hallucinated academic answers.",
                score=0.9,
                page_start=2,
                page_end=2,
                source="bm25",
            ),
        ],
        meta={},
    )
    generated = "NIRMIQ uses citation-aware synthesis to reduce hallucinated academic answers. [2]"
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="How does NIRMIQ reduce hallucinations?",
            bundle=bundle,
            response_mode="research",
        )
    )

    assert grounded is True
    assert answer == generated
    assert meta["selected_context_chunk_ids"] == ["chunk-1", "chunk-2"]
    assert meta["cited_context_chunk_ids"] == ["chunk-2"]
    assert meta["citation_anchor_chunk_map"] == [
        {
            "anchor": 2,
            "chunk_id": "chunk-2",
            "document_id": "doc-1",
            "page_start": 2,
            "page_end": 2,
        }
    ]


def test_citation_context_maps_multi_digit_selected_anchor() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id=f"chunk-{index}",
                document_id="doc-1",
                text=f"Evidence passage {index}.",
                score=1.0,
                page_start=index,
                page_end=index,
            )
            for index in range(1, 11)
        ],
        meta={},
    )

    meta = SynthesisService._citation_context_meta(
        answer="The late passage supports this claim. [10]",
        bundle=bundle,
        selected_context=[(10, "[10] Evidence passage 10.")],
    )

    assert meta["cited_context_chunk_ids"] == ["chunk-10"]
    assert meta["citation_anchor_chunk_map"][0]["anchor"] == 10


def test_query_citations_are_limited_to_synthesis_used_chunks() -> None:
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="unused",
                document_id="doc-1",
                text="This chunk was retrieved but not cited by the final answer.",
                score=1.0,
            ),
            RetrievedChunk(
                chunk_id="used",
                document_id="doc-1",
                text="This chunk directly supports the final answer.",
                score=0.8,
            ),
        ],
        meta={},
    )

    citations = QueryService._citations_from_synthesis_context(
        bundle,
        {"cited_context_chunk_ids": ["used"]},
        grounded=True,
    )

    assert [citation.chunk_id for citation in citations] == ["used"]
    assert citations[0].excerpt == "This chunk directly supports the final answer."


def test_factual_retrieval_query_expands_unsupervised_algorithm_terms() -> None:
    query = "Explain a few unsupervised algorithms from this textbook"
    expanded = QueryService._retrieval_query(
        query,
        "research",
        {"questions": [], "diagrams": []},
        QueryIntent("factual_lookup", 0.68, "default_grounded_retrieval"),
    )

    assert expanded != query
    assert "clustering" in expanded.lower()
    assert "anomaly detection" in expanded.lower()


def test_fallback_list_answer_uses_compact_answer_contract() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(""),  # type: ignore[arg-type]
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text=(
                    "Unsupervised learning techniques include clustering, density estimation, "
                    "dimensionality reduction, and anomaly detection."
                ),
                score=1.0,
                page_start=1,
                page_end=1,
                source="bm25",
            )
        ],
        meta={},
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="Explain a few unsupervised algorithms",
            bundle=bundle,
            response_mode="research",
        )
    )

    assert grounded is True
    assert "Direct answer" in answer
    assert "Key points" in answer
    assert "clustering" in answer.lower()
    assert meta["citation_coverage"] >= 0.5


def test_exam_answer_fallback_uses_marks_aware_contract() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(""),  # type: ignore[arg-type]
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="exam-1",
                document_id="doc-1",
                text=(
                    "Retrieval augmented generation combines search with grounded answer synthesis. "
                    "The system retrieves relevant passages before generating an answer. "
                    "Citations help verify where the answer came from. "
                    "This reduces unsupported claims by keeping the answer tied to source evidence."
                ),
                score=1.0,
                page_start=2,
                page_end=2,
                source="bm25",
            )
        ],
        meta={},
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="Explain retrieval augmented generation as a 10 mark answer.",
            bundle=bundle,
            response_mode="exam_answer",
            exam_profile={
                "marks": 10,
                "answer_style": "stepwise",
                "content_type": "conceptual",
            },
        )
    )

    assert grounded is True
    assert "Exam-ready answer (10 marks)" in answer
    assert "Direct answer" in answer
    assert "Key points" in answer
    assert "Stepwise explanation" in answer
    assert "[1]" in answer
    assert meta["citation_coverage"] >= 0.6


def test_exam_answer_contract_clamps_marks_and_changes_depth() -> None:
    short_contract = SynthesisService._exam_answer_contract({"marks": 1})
    long_contract = SynthesisService._exam_answer_contract({"marks": 25})

    assert short_contract["marks"] == 2
    assert short_contract["evidence_bullets"] == 2
    assert long_contract["marks"] == 15
    assert long_contract["evidence_bullets"] == 7
    assert "Detailed explanation" in long_contract["sections"]


def test_diagram_request_adds_honest_missing_diagram_note() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator("CNNs use convolutional layers for image recognition. [1]"),  # type: ignore[arg-type]
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="cnn-1",
                document_id="doc-1",
                text="CNNs use convolutional layers for image recognition and visual perception tasks.",
                score=1.0,
                page_start=7,
                page_end=7,
                source="bm25",
            )
        ],
        meta={},
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="Explain CNNs for image recognition and include image references.",
            bundle=bundle,
            response_mode="research",
            exam_context={"questions": [], "diagrams": []},
        )
    )

    assert grounded is True
    assert "Diagram note" in answer
    assert "No source diagram was available" in answer
    assert meta["citation_coverage"] >= 1.0


def test_image_topic_does_not_trigger_a_missing_diagram_note() -> None:
    assert SynthesisService._is_diagram_request(
        "How do image generation systems create concept art?"
    ) is False
    assert SynthesisService._is_diagram_request(
        "Explain the system and include image references."
    ) is True


def test_diagram_context_uses_asset_ids_without_local_paths() -> None:
    instruction = SynthesisService._exam_artifact_instruction(
        {
            "questions": [],
            "diagrams": [
                {
                    "id": "asset-123",
                    "page_number": 9,
                    "caption": "Figure 2. CNN architecture",
                    "image_path": "C:\\Users\\Siddharth\\private\\figure.png",
                }
            ],
        },
        query="include diagram references",
    )

    assert "asset-123" in instruction
    assert "page 9" in instruction
    assert "CNN architecture" in instruction
    assert "C:\\Users\\Siddharth" not in instruction


def test_missing_diagram_note_overrides_unsupported_diagram_wording() -> None:
    answer = SynthesisService._with_diagram_grounding_note(
        answer="CNNs are often shown with a source diagram. [1]",
        query="Explain CNNs with a source diagram.",
        exam_context={"questions": [], "diagrams": []},
    )

    assert "No source diagram was available" in answer


def test_study_guide_fallback_derives_topics_without_question_bank() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(""),  # type: ignore[arg-type]
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="guide-1",
                document_id="doc-1",
                text=(
                    "Retrieval augmented generation combines retrieval with grounded synthesis. "
                    "Grounded synthesis uses retrieved passages to keep answers tied to evidence. "
                    "Citation coverage helps students verify which source passages support an answer."
                ),
                score=1.0,
                page_start=4,
                page_end=4,
                source="bm25",
            ),
            RetrievedChunk(
                chunk_id="guide-2",
                document_id="doc-1",
                text=(
                    "Retrieval quality depends on matching the query to relevant chunks. "
                    "When evidence is weak, the system should abstain instead of hallucinating."
                ),
                score=0.9,
                page_start=5,
                page_end=5,
                source="bm25",
            ),
        ],
        meta={},
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="Generate a comprehensive study guide from this material.",
            bundle=bundle,
            response_mode="study_guide",
            exam_context={"questions": [], "diagrams": []},
        )
    )

    assert grounded is True
    assert "Study guide from retrieved source topics" in answer
    assert "Q1." in answer
    assert "Why this matters" in answer
    assert "No imported questions" not in answer
    assert meta["citation_coverage"] >= 0.6


def test_question_bank_study_guide_prioritizes_supported_questions() -> None:
    context_chunks = [
        (
            1,
            "[1] doc=doc-1 score=1.000 source=bm25 pages=1-1\n"
            "Retrieval augmented generation retrieves evidence before grounded synthesis. "
            "Citation coverage helps verify answers.",
        )
    ]
    guide = SynthesisService._fallback_study_guide(
        query="Generate a study guide.",
        context_chunks=context_chunks,
        exam_context={
            "questions": [
                {"question": "Explain unrelated payment analytics.", "marks": 10},
                {"question": "Explain retrieval augmented generation.", "marks": 5},
            ],
            "diagrams": [],
        },
    )

    assert "Q1. Explain retrieval augmented generation." in guide
    assert "question-bank priority" in guide
    assert "Citation coverage" in guide or "retrieves evidence" in guide


def test_diagram_request_references_available_source_diagrams() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator("CNNs use convolutional layers for image recognition. [1]"),  # type: ignore[arg-type]
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="cnn-1",
                document_id="doc-1",
                text="CNNs use convolutional layers for image recognition and visual perception tasks.",
                score=1.0,
                page_start=7,
                page_end=7,
                source="bm25",
            )
        ],
        meta={},
    )

    answer, grounded, _ = asyncio.run(
        service.synthesize(
            query="Explain CNNs for image recognition and include figure references.",
            bundle=bundle,
            response_mode="research",
            exam_context={
                "questions": [],
                "diagrams": [
                    {
                        "id": "asset-123",
                        "page_number": 9,
                        "caption": "Figure 2. CNN architecture",
                        "image_path": "C:\\Users\\Siddharth\\private\\figure.png",
                    }
                ],
            },
        )
    )

    assert grounded is True
    assert "D1: source diagram on page 9" in answer
    assert "CNN architecture" in answer
    assert "C:\\Users\\Siddharth" not in answer


def test_any_unsupported_cited_claim_forces_rewrite() -> None:
    generated = (
        "NIRMIQ uses grounded retrieval for academic documents. [1]\n"
        "NIRMIQ is also a cloud payments platform with social analytics. [1]\n"
        "NIRMIQ uses citation-aware synthesis. [1]"
    )
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert "cloud payments" not in answer.lower()
    assert meta["answer_rewritten_for_faithfulness"] is True
    assert len(meta["original_unsupported_claims"]) >= 1


def test_unsupported_uncited_generation_does_not_receive_fabricated_anchor() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator("Quantum bananas calculate ocean treaties."),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is True
    assert "quantum bananas" not in answer.lower()
    assert meta["answer_rewritten_for_faithfulness"] is True
    assert meta["citation_verification_state"] == "supported"


def test_low_citation_coverage_fails_evidence_reliability_gate() -> None:
    generated = (
        "NIRMIQ uses grounded retrieval for academic documents. [1]\n"
        "The system guarantees perfect answers forever."
    )
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1),
        generator=FakeGenerator(generated),  # type: ignore[arg-type]
    )

    answer, grounded, meta = asyncio.run(
        service.synthesize(
            query="What does NIRMIQ use?",
            bundle=_bundle(),
            response_mode="research",
        )
    )

    assert grounded is False
    assert "not enough direct source evidence" in answer
    assert meta["evidence_gate_state"] == "failed"
    assert "low_citation_coverage" in meta["evidence_gate_reasons"]
    assert "claim_without_source_span" in meta["evidence_gate_reasons"]
    assert meta["citation_coverage"] < meta["evidence_gate_min_citation_coverage"]


def test_long_context_deep_research_uses_configured_creative_temperature() -> None:
    generator = FakeGenerator("NIRMIQ uses grounded retrieval and citation-aware synthesis. [1]")
    service = SynthesisService(
        settings=_settings().model_copy(
            update={
                "generator_temperature_grounded": 0.15,
                "generator_temperature_long_context": 0.85,
            }
        ),
        policy=RetrievalPolicy(min_grounding_score=0.1, max_context_tokens=2000),
        generator=generator,  # type: ignore[arg-type]
    )
    repeated_text = (
        "NIRMIQ uses grounded retrieval and local citation-aware synthesis for academic documents. "
        * 120
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="doc-1",
                text=repeated_text,
                score=1.0,
                page_start=1,
                page_end=2,
                source="bm25",
            )
        ],
        meta={},
    )

    _, grounded, meta = asyncio.run(
        service.synthesize(
            query="Write deep research notes.",
            bundle=bundle,
            response_mode="deep_research",
        )
    )

    assert grounded is True
    assert generator.temperature == 0.85
    assert meta["generation_temperature"] == 0.85


def test_context_budget_preserves_later_direct_evidence() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1, max_context_tokens=320),
        generator=FakeGenerator(""),  # type: ignore[arg-type]
    )
    broad_text = (
        "Convolutional neural networks process images with learned feature maps. "
        "This chapter also discusses training data, optimization, and model evaluation. "
        * 30
    )
    pooling_text = (
        "The second common building block of CNNs is the pooling layer. "
        "Its goal is to subsample or shrink feature maps to reduce the computational load."
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id=f"chunk-{index}",
                document_id="doc-1",
                text=broad_text,
                score=1.0 - (index * 0.05),
            )
            for index in range(1, 4)
        ]
        + [
            RetrievedChunk(
                chunk_id="chunk-4",
                document_id="doc-1",
                text=pooling_text,
                score=0.8,
            )
        ],
        meta={},
    )
    query = "Explain CNN"

    selected = service._select_context(
        bundle,
        query=query,
        answer_plan=build_answer_plan(query=query, response_mode="research"),
    )

    assert sorted(anchor for anchor, _ in selected) == [1, 2, 3, 4]
    assert any("pooling layer" in block for _, block in selected)
    assert sum(len(service._context_text(block).split()) for _, block in selected) <= 320


def test_context_selection_considers_late_required_comparison_evidence() -> None:
    service = SynthesisService(
        settings=_settings(),
        policy=RetrievalPolicy(min_grounding_score=0.1, max_context_tokens=420),
        generator=FakeGenerator(""),  # type: ignore[arg-type]
    )
    bundle = RetrievalBundle(
        chunks=[
            RetrievedChunk(
                chunk_id=f"broad-{index}",
                document_id="doc-1",
                text="Classifier evaluation includes several charts and thresholds.",
                score=1.0 - (index * 0.02),
            )
            for index in range(1, 9)
        ]
        + [
            RetrievedChunk(
                chunk_id="precision",
                document_id="doc-1",
                text="The accuracy of positive predictions is called precision.",
                score=0.8,
            ),
            RetrievedChunk(
                chunk_id="recall",
                document_id="doc-1",
                text="Recall is the ratio of positive instances correctly detected.",
                score=0.78,
            ),
        ],
        meta={},
    )
    query = "Compare precision and recall."

    selected = service._select_context(
        bundle,
        query=query,
        answer_plan=build_answer_plan(query=query, response_mode="research"),
    )

    assert {9, 10}.issubset({anchor for anchor, _ in selected})
    assert sum(len(service._context_text(block).split()) for _, block in selected) <= 420


def test_evidence_cleanup_removes_dense_table_prefix_before_numbered_section() -> None:
    sentence = (
        "Layer Type Complexity Operations Self-Attention O(n2 d) O(1) "
        "3.5 Positional Encoding Since the model has no recurrence, it adds position information."
    )

    cleaned = SynthesisService._clean_evidence_sentence(sentence)

    assert cleaned == (
        "Since the model has no recurrence, it adds position information."
    )


def test_context_excerpt_preserves_separated_benefit_and_limitation_evidence() -> None:
    query = "What benefit and runtime limitation does batch normalization have?"
    plan = build_answer_plan(query=query, response_mode="research")
    filler = "The chapter discusses implementation details and training settings. " * 20
    text = (
        "Batch normalization acts like a regularizer and speeds up training. "
        f"{filler}"
        "However, batch normalization adds complexity and a runtime penalty that slows predictions."
    )

    excerpt = SynthesisService._query_aware_context_excerpt(
        text=text,
        query=query,
        answer_plan=plan,
        max_words=90,
    )

    assert "acts like a regularizer" in excerpt
    assert "runtime penalty" in excerpt
