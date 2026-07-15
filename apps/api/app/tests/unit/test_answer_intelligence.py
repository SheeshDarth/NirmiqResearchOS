from app.domain.answer_intelligence import (
    answer_evidence_cue_score,
    answer_subject_anchor_terms,
    build_answer_plan,
)
from app.domain.query_intent import QueryIntent
from app.services.query_service import QueryService
from app.services.synthesis_service import SynthesisService


def test_concept_query_builds_query_specific_plan() -> None:
    plan = build_answer_plan(
        "Explain convolutional neural networks in detail with image references.",
        "research",
    )

    assert plan.answer_type == "concept_explanation"
    assert plan.depth == "detailed"
    assert plan.subject == "convolutional neural networks"
    assert plan.sections[:2] == ("Direct answer", "How it works")
    assert "diagram references" in plan.requested_elements
    assert "Source diagram references" in plan.sections


def test_concept_evidence_cues_reward_definitions_and_components() -> None:
    assert answer_evidence_cue_score("concept_explanation", "This is called transfer learning.") > 0
    assert answer_evidence_cue_score("concept_explanation", "Pooling is a building block of CNNs.") > 0


def test_mechanism_query_does_not_force_unrequested_sections() -> None:
    plan = build_answer_plan("How does gradient descent update a model?", "research")

    assert plan.answer_type == "mechanism_explanation"
    assert plan.sections == ("Direct answer", "How it works", "Why it matters")
    assert "Limitations" not in plan.sections
    assert "Applications" not in plan.sections


def test_comparison_and_procedure_queries_get_different_contracts() -> None:
    comparison = build_answer_plan("Compare supervised and unsupervised learning", "research")
    procedure = build_answer_plan("How to evaluate a classifier step by step", "research")

    assert comparison.answer_type == "comparison"
    assert comparison.sections[0] == "Direct comparison"
    assert procedure.answer_type == "procedure"
    assert procedure.sections[:2] == ("Goal", "Steps")


def test_date_question_gets_factual_lookup_contract() -> None:
    plan = build_answer_plan("When was the third edition released?", "research")

    assert plan.answer_type == "factual_lookup"
    assert plan.sections == ("Direct answer", "Supporting detail")


def test_subject_anchor_extracts_named_model_from_generic_mechanism_predicate() -> None:
    query = "How does softmax regression perform multiclass classification?"
    plan = build_answer_plan(query, "research")

    assert answer_subject_anchor_terms(query, plan) == {"softmax", "regression"}


def test_subject_anchor_extracts_owner_of_requested_benefit_and_limitation() -> None:
    query = "What benefit and runtime limitation does batch normalization have?"
    plan = build_answer_plan(query, "research")

    assert answer_subject_anchor_terms(query, plan) == {"batch", "normalization"}


def test_subject_anchor_keeps_requested_mechanism_instead_of_document_actor() -> None:
    query = "How does the book place cross-validation in the ML workflow?"
    plan = build_answer_plan(query, "research")

    assert answer_subject_anchor_terms(query, plan) == {"cross-validation"}


def test_subject_anchor_preserves_hyphenated_focus_terms() -> None:
    query = "How does the Transformer learning-rate schedule use warmup?"
    plan = build_answer_plan(query, "research")

    assert answer_subject_anchor_terms(query, plan) == {
        "learning-rate",
        "schedule",
        "transformer",
    }


def test_recommendation_query_builds_clean_evidence_contract() -> None:
    query = "What does the paper recommend for fact-checking and verification?"
    plan = build_answer_plan(query, "research")

    assert plan.answer_type == "recommendation"
    assert answer_subject_anchor_terms(query, plan) == {"fact-checking", "verification"}


def test_interpretation_query_uses_value_reading_contract() -> None:
    query = "How should the silhouette coefficient be interpreted?"
    plan = build_answer_plan(query, "research")

    assert plan.answer_type == "interpretation"
    assert plan.sections[:2] == ("Direct answer", "How to read the value")
    assert answer_subject_anchor_terms(query, plan) == {"coefficient", "silhouette"}


def test_prompt_contains_answer_plan_and_anti_fragment_guidance() -> None:
    prompt = SynthesisService._build_grounded_prompt(
        query="Explain a decision tree briefly.",
        context_blocks=[(1, "[1] pages=1-1\nA decision tree recursively splits data into regions.")],
        response_mode="research",
    )

    assert "Query-specific answer plan" in prompt
    assert "Task: concept_explanation" in prompt
    assert "Subject: a decision tree" in prompt
    assert "do not paste index entries or unrelated fragments" in prompt
    assert "Depth: brief" in prompt


def test_factual_retrieval_projects_away_presentation_instructions() -> None:
    focused = QueryService._retrieval_query(
        "Explain CNNs in detail. Provide image references too.",
        "research",
        {"questions": [], "diagrams": []},
        QueryIntent("factual_lookup", 0.68, "default_grounded_retrieval"),
    )

    assert focused == "explain CNNs"
    assert "image references" not in focused.lower()


def test_clean_factual_question_is_not_rewritten() -> None:
    query = "What is regularization in the context of reducing overfitting?"
    focused = QueryService._retrieval_query(
        query,
        "research",
        {"questions": [], "diagrams": []},
        QueryIntent("factual_lookup", 0.68, "default_grounded_retrieval"),
    )

    assert focused == query
