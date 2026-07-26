from app.domain.answer_intelligence import (
    answer_evidence_cue_score,
    answer_subject_anchor_terms,
    build_answer_plan,
    evidence_obligation_score,
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


def test_image_as_a_topic_does_not_imply_a_visual_reference_request() -> None:
    plan = build_answer_plan(
        "How do image generation systems turn prompts into concept art?",
        "research",
    )

    assert "diagram references" not in plan.requested_elements


def test_concept_evidence_cues_reward_definitions_and_components() -> None:
    assert answer_evidence_cue_score("concept_explanation", "This is called transfer learning.") > 0
    assert answer_evidence_cue_score("concept_explanation", "Pooling is a building block of CNNs.") > 0


def test_mechanism_query_does_not_force_unrequested_sections() -> None:
    plan = build_answer_plan("How does gradient descent update a model?", "research")

    assert plan.answer_type == "mechanism_explanation"
    assert plan.sections == ("Direct answer", "How it works", "Why it matters")
    assert "Limitations" not in plan.sections
    assert "Applications" not in plan.sections


def test_should_action_queries_use_recommendation_or_limitation_contracts() -> None:
    first_screen = build_answer_plan(
        "What should the first screen of an academic product website communicate?",
        "research",
    )
    low_end = build_answer_plan(
        "Which animation choices should a low-end laptop avoid?",
        "research",
    )

    assert first_screen.answer_type == "recommendation"
    assert first_screen.subject == "the first screen"
    assert low_end.answer_type == "limitations"
    assert low_end.subject == "animation choices"

    evidence_boundary = build_answer_plan(
        "What must prompt engineering not override in document-grounded work?",
        "research",
    )
    assert evidence_boundary.answer_type == "limitations"


def test_mechanism_cues_cover_causal_and_pattern_language() -> None:
    text = "A chat-first layout works well because students follow a familiar pattern."

    assert answer_evidence_cue_score("mechanism_explanation", text) >= 0.6


def test_comparison_and_procedure_queries_get_different_contracts() -> None:
    comparison = build_answer_plan("Compare supervised and unsupervised learning", "research")
    procedure = build_answer_plan("How to evaluate a classifier step by step", "research")

    assert comparison.answer_type == "comparison"
    assert comparison.sections[0] == "Direct comparison"
    assert procedure.answer_type == "procedure"
    assert procedure.sections[:2] == ("Goal", "Steps")


def test_natural_comparison_wording_is_routed_to_comparison() -> None:
    plan = build_answer_plan(
        "How does Claude Code differ from Antigravity in the guide?",
        "research",
    )

    assert plan.answer_type == "comparison"
    assert plan.subject == "claude code and antigravity"


def test_how_can_question_keeps_the_requested_action_in_focus() -> None:
    plan = build_answer_plan(
        "How can a prompt give direction to an AI model?",
        "research",
    )

    assert plan.answer_type == "mechanism_explanation"
    assert "prompt" in plan.subject
    assert "direction" in plan.subject


def test_limitation_of_wording_extracts_the_limited_topic() -> None:
    plan = build_answer_plan(
        "What is a limitation of providing too many examples?",
        "research",
    )

    assert plan.answer_type == "limitations"
    assert plan.subject == "providing too many examples"


def test_deployment_guidance_is_routed_to_a_recommendation_contract() -> None:
    plan = build_answer_plan(
        "What deployment guidance does the guide give?",
        "research",
    )

    assert plan.answer_type == "recommendation"
    assert plan.subject == "deployment"


def test_document_workflow_question_gets_placement_obligations() -> None:
    plan = build_answer_plan(
        "How does the book place validation in the training workflow?",
        "research",
    )

    assert plan.answer_type == "workflow_placement"
    assert [item.key for item in plan.evidence_obligations] == [
        "placement",
        "workflow_action",
    ]


def test_document_description_of_workflow_gets_placement_obligations() -> None:
    plan = build_answer_plan(
        "How does the book describe cross-validation in the machine learning workflow?",
        "research",
    )

    assert plan.answer_type == "workflow_placement"


def test_overview_reference_is_enumeration_not_document_summary() -> None:
    plan = build_answer_plan(
        "Which common methods are listed in the early overview?",
        "research",
    )

    assert plan.answer_type == "enumeration"
    assert plan.subject == "common methods"
    assert plan.evidence_obligations[0].key == "items"


def test_topic_scope_query_extracts_the_document_part_as_subject() -> None:
    plan = build_answer_plan(
        "Which topics does Part I of Example Systems cover?",
        "research",
    )

    assert plan.subject == "Part I of Example Systems"


def test_mechanism_obligations_score_different_source_facets() -> None:
    plan = build_answer_plan(
        "How does a generator create an output from an input?",
        "research",
    )
    scores = {
        item.key: evidence_obligation_score(
            item,
            "It starts with an input, transforms it repeatedly, and produces the output.",
        )
        for item in plan.evidence_obligations
    }

    assert scores["initial_state"] > 0
    assert scores["operation"] > 0
    assert scores["result"] > 0


def test_coordinated_outcome_obligations_require_the_named_target() -> None:
    plan = build_answer_plan(
        "How does the method identify clusters and anomalies?",
        "research",
    )
    obligations = {item.key: item for item in plan.evidence_obligations}

    cluster_sentence = "Neighboring core instances form one cluster."
    anomaly_sentence = "An isolated instance is considered an anomaly."

    assert evidence_obligation_score(obligations["result_target_1"], cluster_sentence) > 0
    assert evidence_obligation_score(obligations["result_target_1"], anomaly_sentence) == 0
    assert evidence_obligation_score(obligations["result_target_2"], anomaly_sentence) > 0
    assert evidence_obligation_score(
        obligations["decision_condition"],
        "If a neighborhood has at least five points, then it is a core region.",
    ) > 0


def test_date_question_gets_factual_lookup_contract() -> None:
    plan = build_answer_plan("When was the third edition released?", "research")

    assert plan.answer_type == "factual_lookup"
    assert plan.sections == ("Direct answer", "Supporting detail")


def test_focus_phrase_extracts_subject_after_reason_or_reported_context() -> None:
    concept = build_answer_plan("What is the central idea behind PCA?", "research")
    factual = build_answer_plan(
        "What hardware and training duration are reported for the base Transformer model?",
        "research",
    )

    assert concept.subject == "PCA"
    assert factual.answer_type == "factual_lookup"
    assert factual.subject == "base Transformer model"
    assert factual.evidence_obligations[0].key == "requested_facts"
    assert factual.evidence_obligations[0].required is False


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

    assert plan.subject == "warmup"
    assert answer_subject_anchor_terms(query, plan) == {"warmup"}


def test_use_question_focuses_on_the_technique_not_the_document_actor() -> None:
    query = "Why does the paper use multi-head attention?"
    plan = build_answer_plan(query, "research")

    assert plan.subject == "multi-head attention"
    assert answer_subject_anchor_terms(query, plan) == {"multi-head", "attention"}
    assert plan.evidence_obligations[0].key == "rationale"
    assert plan.evidence_obligations[1].required is False


def test_representation_question_focuses_on_the_represented_object() -> None:
    query = "How does the Transformer represent token positions?"
    plan = build_answer_plan(query, "research")

    assert plan.subject == "token positions"
    assert answer_subject_anchor_terms(query, plan) == {"token", "positions"}


def test_benefit_and_limitation_query_builds_two_evidence_obligations() -> None:
    plan = build_answer_plan(
        "What benefit and runtime limitation does batch normalization have?",
        "research",
    )

    assert plan.subject == "batch normalization"
    assert [item.key for item in plan.evidence_obligations] == ["benefit", "limitation"]


def test_mechanism_plan_adds_query_derived_operation_focus() -> None:
    plan = build_answer_plan(
        "How does scaled dot-product attention compute attention outputs?",
        "research",
    )
    focus = next(item for item in plan.evidence_obligations if item.key == "operation_focus")

    assert evidence_obligation_score(
        focus,
        "We compute the dot products and apply softmax to obtain the output.",
    ) > 0
    assert evidence_obligation_score(
        focus,
        "The decoder masks illegal connections before softmax.",
    ) == 0


def test_mechanism_plan_preserves_operation_noun_phrase() -> None:
    plan = build_answer_plan(
        "How does softmax regression perform multiclass classification?",
        "research",
    )
    focus = next(item for item in plan.evidence_obligations if item.key == "operation_focus")

    assert "multiclass" in focus.retrieval_terms
    assert "classification" in focus.retrieval_terms
    assert any(item.key == "result" for item in plan.evidence_obligations)


def test_comparison_plan_requires_evidence_for_both_named_sides() -> None:
    plan = build_answer_plan(
        "Compare precision and recall for a binary classifier.",
        "research",
    )

    assert [item.key for item in plan.evidence_obligations[:2]] == [
        "comparison_side_1",
        "comparison_side_2",
    ]
    assert plan.evidence_obligations[0].retrieval_terms == ("precision",)
    assert plan.evidence_obligations[1].retrieval_terms == ("recall",)


def test_comparison_plan_uses_distinguishing_terms_for_each_side() -> None:
    plan = build_answer_plan(
        "Compare a high and low learning rate.",
        "research",
    )

    assert plan.evidence_obligations[0].retrieval_terms == ("high",)
    assert plan.evidence_obligations[1].retrieval_terms == ("low",)


def test_comparison_evidence_cues_must_describe_the_named_side_locally() -> None:
    plan = build_answer_plan(
        "Compare precision and recall for a classifier.",
        "research",
    )
    precision, recall = plan.evidence_obligations[:2]

    precision_definition = (
        "The accuracy of positive predictions is called the precision of the classifier."
    )
    recall_definition = (
        "Precision is used with recall, also called sensitivity; recall is the ratio of "
        "positive instances correctly detected by the classifier."
    )

    assert evidence_obligation_score(precision, precision_definition) >= 0.32
    assert evidence_obligation_score(precision, recall_definition) < 0.32
    assert evidence_obligation_score(recall, recall_definition) >= 0.32
    unrelated_label = (
        "It is convenient to combine precision and recall into a metric called the F score."
    )
    assert evidence_obligation_score(precision, unrelated_label) < 0.32
    assert evidence_obligation_score(recall, unrelated_label) < 0.32
    tradeoff_label = "This is called the precision/recall trade-off."
    assert evidence_obligation_score(precision, tradeoff_label) < 0.32
    assert evidence_obligation_score(recall, tradeoff_label) < 0.32
    framework_heading = (
        "Precision and Recall Scikit-Learn provides functions to compute classifier metrics."
    )
    assert evidence_obligation_score(recall, framework_heading) < 0.32
    unrelated_long_heading = (
        "The Precision/Recall Trade-off explains how the classifier makes its decisions."
    )
    assert evidence_obligation_score(recall, unrelated_long_heading) < 0.32
    figure_caption = (
        "The chosen ratio is at 90% precision and 48% recall; once again there is a trade-off."
    )
    assert evidence_obligation_score(precision, figure_caption) < 0.32
    assert evidence_obligation_score(recall, figure_caption) < 0.32


def test_comparison_behavior_cues_support_high_and_low_variants() -> None:
    plan = build_answer_plan("Compare a high and low learning rate.", "research")
    high, low = plan.evidence_obligations[:2]

    assert evidence_obligation_score(
        high,
        "A high learning rate lets the model rapidly adapt to changing data.",
    ) >= 0.32
    assert evidence_obligation_score(
        low,
        "A low learning rate has more inertia and the model learns more slowly.",
    ) >= 0.32


def test_explicit_mechanism_verb_becomes_the_required_operation() -> None:
    plan = build_answer_plan(
        "How does the Transformer represent token positions?",
        "research",
    )

    assert plan.evidence_obligations[0].key == "operation_focus"
    assert plan.evidence_obligations[0].required is True
    assert "representation" in plan.evidence_obligations[0].retrieval_terms
    operation = next(item for item in plan.evidence_obligations if item.key == "operation")
    assert operation.required is False


def test_passive_calculation_query_preserves_subject_and_formula_contract() -> None:
    plan = build_answer_plan("How is the stability margin calculated?", "research")

    assert plan.answer_type == "mechanism_explanation"
    assert plan.subject == "the stability margin"
    assert "equations" in plan.requested_elements
    focus = next(item for item in plan.evidence_obligations if item.key == "operation_focus")
    assert "calculated" in focus.retrieval_terms
    assert evidence_obligation_score(
        focus,
        "The stability margin is calculated as M = (target - measured) / denominator.",
    ) >= 0.32


def test_comparison_action_wrapper_resolves_to_named_sides_and_table_rows() -> None:
    plan = build_answer_plan(
        "Compare the actions for low drift and high drift.",
        "research",
    )

    assert plan.subject == "low drift and high drift"
    low, high = plan.evidence_obligations[:2]
    assert low.retrieval_terms == ("low",)
    assert high.retrieval_terms == ("high",)
    assert evidence_obligation_score(
        low,
        "Low drift | below the warning threshold | monitor normally.",
    ) >= 0.32
    assert evidence_obligation_score(
        high,
        "High drift | above the warning threshold | recalibrate immediately.",
    ) >= 0.32


def test_interpretation_query_uses_meaning_and_value_obligations() -> None:
    plan = build_answer_plan(
        "How should the silhouette coefficient be interpreted?",
        "research",
    )

    assert [item.key for item in plan.evidence_obligations] == [
        "value_mapping",
        "interpretive_relation",
    ]
    assert plan.evidence_obligations[0].required is False
    assert plan.evidence_obligations[1].required is True


def test_numbered_component_question_is_an_enumeration() -> None:
    plan = build_answer_plan(
        "What are the two sublayers in each Transformer encoder layer?",
        "research",
    )

    assert plan.answer_type == "enumeration"


def test_document_recommendation_subject_omits_the_document_actor() -> None:
    plan = build_answer_plan(
        "What does the GenAI module recommend for fact-checking and verification?",
        "research",
    )

    assert plan.subject == "fact-checking and verification"
    assert plan.evidence_obligations[0].key == "recommended_action"


def test_document_mention_question_focuses_on_the_mentioned_concept() -> None:
    query = "Why does the book mention reducing dimensionality of training data?"
    plan = build_answer_plan(query, "research")

    assert plan.subject == "reducing dimensionality of training data"
    assert answer_subject_anchor_terms(query, plan) == {
        "reducing",
        "dimensionality",
        "training",
        "data",
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
