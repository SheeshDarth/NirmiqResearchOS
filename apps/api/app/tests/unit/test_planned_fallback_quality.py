from app.domain.answer_intelligence import build_answer_plan
from app.services.synthesis_service import SynthesisService


def test_mechanism_fallback_prefers_process_over_related_description() -> None:
    query = "How does gradient descent update model parameters?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "Gradient descent is a common optimization algorithm used in machine learning.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=2-2\n"
                "Gradient descent computes the gradient of the cost function for the model parameters. "
                "It then updates the parameters in the opposite direction to reduce the cost.",
            ),
        ],
    )

    assert "computes the gradient" in answer
    assert "updates the parameters" in answer
    assert "How it works" in answer
    assert "[2]" in answer


def test_mechanism_fallback_prefers_complete_requested_operation() -> None:
    query = "How does scaled dot-product attention compute attention outputs?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=4-4\n"
                "Scaled dot-product attention computes query-key dot products, divides them by a "
                "scale factor, and applies softmax to obtain weights on the values.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=5-5\n"
                "Scaled dot-product attention masks illegal decoder connections before softmax.",
            ),
        ],
    )

    assert "query-key dot products" in answer
    assert "weights on the values" in answer
    assert "[1]" in answer


def test_mechanism_fallback_prefers_causal_chat_first_flow() -> None:
    query = "How does a chat-first layout reduce cognitive load?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "Good interface design reduces cognitive load. Primary actions should be visible, "
                "while advanced controls should stay hidden until the user asks for them.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=2-2\n"
                "A chat-first layout works well because students already understand the pattern: "
                "upload a source, type a question, read the answer, and open sources only when verification is needed.",
            ),
        ],
    )

    assert "chat-first layout works well because" in answer
    assert "upload a source" in answer
    assert "[2]" in answer


def test_limitation_fallback_collects_avoidance_constraints() -> None:
    query = "Which animation choices should a low-end laptop avoid?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "Smooth transitions should use lightweight CSS transforms rather than heavy scripts. "
                "The interface should avoid large animation libraries, oversized images, and constant background effects.",
            )
        ],
    )

    assert "heavy scripts" in answer
    assert "large animation libraries" in answer
    assert "oversized images" in answer
    assert "background effects" in answer
    assert "[1]" in answer


def test_recommendation_fallback_keeps_the_requested_subject_in_front() -> None:
    query = "What should the first screen of an academic product website communicate?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        additional_terms={
            "performance",
            "transitions",
            "lightweight",
            "scripts",
            "animation",
            "privacy",
        },
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "A useful academic product website should make the value proposition clear before showing complex controls. "
                "The first screen should explain what the product does, who it helps, and what action the user should take next. "
                "Smooth transitions should use lightweight CSS transforms rather than heavy scripts.",
            )
        ],
    )

    assert answer.startswith("Short answer\n\nThe first screen should explain")
    assert "Smooth transitions should use" not in answer.split("Recommendations from the source", 1)[0]


def test_comparison_fallback_selects_explicit_contrast() -> None:
    query = "Compare precision and recall"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=3-3\n"
                "Precision measures the fraction of positive predictions that are correct, whereas "
                "recall measures the fraction of actual positives that the model identifies.",
            )
        ],
    )

    assert "whereas recall" in answer
    assert "[1]" in answer


def test_comparison_fallback_requires_direct_evidence_for_each_side() -> None:
    query = "Compare precision and recall"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=3-3\n"
                "The accuracy of positive predictions is called precision.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=4-4\n"
                "Recall is the ratio of positive instances correctly detected by the classifier.",
            ),
            (
                3,
                "[3] doc=doc score=.8 source=bm25 pages=5-5\n"
                "It is convenient to combine precision and recall into a metric called the F score.",
            ),
        ],
    )

    assert answer.startswith("Direct comparison")
    assert "Precision: The accuracy of positive predictions" in answer
    assert "Recall: Recall is the ratio" in answer
    assert "metric called the F score" not in answer
    assert "[1]" in answer
    assert "[2]" in answer


def test_comparison_fallback_covers_high_and_low_behavior() -> None:
    query = "Compare a high and low learning rate in online learning."
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=42-42\n"
                "A high learning rate lets the system rapidly adapt to new data but quickly forget old data. "
                "Conversely, a low learning rate has more inertia; it learns more slowly and is less sensitive to noise.",
            )
        ],
    )

    assert answer.startswith("Direct comparison")
    assert "rapidly adapt" in answer
    assert "low learning rate has more inertia" in answer
    assert "less sensitive to noise" in answer


def test_comparison_fallback_reads_actions_from_labeled_table_rows() -> None:
    query = "Compare the actions for low drift and high drift."
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=3-3\n"
                "Low drift | below 0.5 percent per hour | monitor normally. "
                "High drift | above 2.0 percent per hour | recalibrate immediately.",
            ),
            (
                2,
                "[2] doc=doc score=.8 source=bm25 pages=1-1\n"
                "Rapid signals are sampled more often, while stable signals are sampled less often.",
            ),
        ],
    )

    assert answer.startswith("Direct comparison")
    assert "monitor normally" in answer
    assert "recalibrate immediately" in answer
    assert "sampled more often" not in answer


def test_mechanism_fallback_preserves_requested_formula() -> None:
    query = "How is the stability margin calculated?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=2-2\n"
                "The stability margin is calculated as M = (target - measured) / "
                "max(abs(target), epsilon). A positive margin means the measured value "
                "remains below the target.",
            )
        ],
    )

    assert "M = (target - measured)" in answer
    assert "max(abs(target), epsilon)" in answer
    assert "[1]" in answer


def test_interpretation_fallback_prefers_explicit_value_mapping() -> None:
    query = "How should the silhouette coefficient be interpreted?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=340-340\n"
                "A coefficient close to +1 means the instance is well inside its own cluster. "
                "A value close to 0 means it is near a cluster boundary, while a value close to -1 "
                "means it may be assigned to the wrong cluster.",
            ),
            (
                2,
                "[2] doc=doc score=.8 source=bm25 pages=183-183\n"
                "Analyzing the confusion matrix can improve a classifier.",
            ),
        ],
    )

    assert "close to +1" in answer
    assert "cluster boundary" in answer
    assert "confusion matrix" not in answer


def test_mechanism_fallback_prefers_full_requested_subject_evidence() -> None:
    query = "How does the Transformer represent token positions?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=2-2\n"
                "The Transformer computes hidden representations in parallel for output positions.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=6-6\n"
                "To represent token positions, positional encodings are added to the input embeddings.",
            ),
        ],
    )

    assert "positional encodings" in answer
    assert "hidden representations in parallel" not in answer


def test_limitation_fallback_does_not_return_only_a_definition() -> None:
    query = "What are the limitations of batch normalization?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=4-4\n"
                "Batch normalization normalizes each input feature. However, it adds computational "
                "overhead and can make each training step slower.",
            )
        ],
    )

    assert "computational overhead" in answer
    assert "slower" in answer
    assert "[1]" in answer


def test_factual_fallback_prefers_sentence_containing_release_date() -> None:
    query = "When was the third edition released?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "Hands-On Machine Learning, Third Edition. The third edition was published in 2022.",
            )
        ],
    )

    assert "published in 2022" in answer
    assert "[1]" in answer


def test_mechanism_fallback_rejects_subject_mentioned_only_in_roadmap() -> None:
    query = "How does dropout regularize a neural network?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "In this section we will examine L1 regularization, L2 regularization, dropout, and max-norm. "
                "L1 regularization adds a penalty based on the absolute value of each weight.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=2-2\n"
                "Dropout is a regularization technique. During training, it randomly drops some inputs "
                "by setting them to zero, which prevents neurons from relying on one another too much.",
            ),
        ],
    )

    assert "randomly drops" in answer
    assert "L1 regularization adds" not in answer
    assert "[2]" in answer


def test_mechanism_fallback_keeps_local_process_sentences() -> None:
    query = "How does DBSCAN identify clusters and anomalies?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=3-3\n"
                "DBSCAN defines clusters as continuous regions of high density. "
                "For each instance, it counts the neighboring instances within a small distance. "
                "Instances with enough neighbors are considered core instances. "
                "An instance that is not a core instance and has no core neighbor is identified as an anomaly.",
            ),
            (
                2,
                "[2] doc=doc score=.8 source=bm25 pages=4-4\n"
                "Gaussian mixture models represent clusters using Gaussian distributions.",
            ),
        ],
    )

    assert "counts the neighboring instances" in answer
    assert "identified as an anomaly" in answer
    assert "Gaussian mixture" not in answer


def test_factual_claim_verification_keeps_exact_edition_and_release_date() -> None:
    context = [
        (
            1,
            "[1] doc=doc score=1 source=bm25 pages=1-1\n"
            "Hands-On Machine Learning THIRD EDITION. 2022-10-03: First Release.",
        )
    ]
    answer = SynthesisService._fallback_factual_answer(
        query="Which edition and release date are shown?",
        context_chunks=context,
    )

    assert answer is not None
    assert SynthesisService._verify_cited_claims(answer, context)["state"] == "supported"


def test_factual_fallback_extracts_measurements_with_citations() -> None:
    answer = SynthesisService._fallback_factual_answer(
        query="What hardware and training duration are reported for the base Transformer model?",
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\nAbstract unrelated to the requested training setup.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=7-7\n"
                "Hardware and Schedule We trained our models on one machine with 8 NVIDIA P100 GPUs. "
                "We trained the base models for a total of 100,000 steps or 12 hours.",
            ),
        ],
    )

    assert answer is not None
    assert "NVIDIA P100" in answer
    assert "100,000" in answer
    assert "[2]" in answer


def test_mechanism_fallback_prefers_requested_focus_without_repeating_model_name() -> None:
    query = "How does the Transformer represent token positions?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=5-5\n"
                "The Transformer maps input tokens through learned embeddings before the softmax layer.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=6-6\n"
                "Since the model contains no recurrence, positional encodings are added to token "
                "embeddings so their positions in the sequence are represented.",
            ),
        ],
    )

    assert "positional encodings" in answer
    assert "positions in the sequence" in answer
    assert "softmax layer" not in answer
    assert "[2]" in answer


def test_recommendation_fallback_prefers_explicit_source_guidance() -> None:
    query = "What does the paper recommend for fact-checking and verification?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=26-26\n"
                "For fact-checking, responses should cross-check claims against trusted sources. "
                "When evidence is uncertain, the system should use retrieval-based verification "
                "or abstain rather than invent an answer.",
            ),
            (
                2,
                "[2] doc=doc score=.8 source=bm25 pages=12-12\n"
                "Human evaluation is commonly used to score generated text.",
            ),
        ],
    )

    assert "cross-check claims" in answer
    assert "retrieval-based verification" in answer
    assert "Human evaluation" not in answer
    assert "[1]" in answer


def test_document_workflow_question_may_use_explicit_roadmap_evidence() -> None:
    query = "How does the book place cross-validation in the machine-learning workflow?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=40-40\n"
                "The machine-learning project workflow evaluates shortlisted models with "
                "cross-validation after data preparation and before final model tuning.",
            )
        ],
    )

    assert "after data preparation" in answer
    assert "before final model tuning" in answer
    assert "[1]" in answer


def test_workflow_fallback_splits_a_dense_pdf_roadmap_clause() -> None:
    query = "How does the source place validation in the model-building workflow?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=8-9\n"
                "Roadmap This part covers the following topics: Framing the problem "
                "Preparing the data Selecting a model and tuning its settings using validation "
                "The challenges of underfitting and overfitting Reducing dimensionality to",
            )
        ],
    )

    assert "Selecting a model and tuning its settings using validation" in answer
    assert "Reducing dimensionality to" not in answer


def test_mechanism_fallback_keeps_operation_and_explicit_scope_together() -> None:
    query = "How does the position-wise block transform each position?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=5-5\n"
                "The position-wise block is applied to each position separately and identically. "
                "It consists of two linear transformations with an activation between them.",
            )
        ],
    )

    assert "two linear transformations" in answer
    assert "each position separately and identically" in answer


def test_mechanism_fallback_covers_evidence_across_multiple_passages() -> None:
    query = "How does a generator create an output from an input?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "The generator starts with an input signal.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=2-2\n"
                "It repeatedly transforms the signal using the supplied condition.",
            ),
            (
                3,
                "[3] doc=doc score=.8 source=bm25 pages=3-3\n"
                "The final transformation produces the requested output.",
            ),
        ],
    )

    assert "starts with an input" in answer
    assert "repeatedly transforms" in answer
    assert "produces the requested output" in answer
    assert "[1]" in answer and "[2]" in answer and "[3]" in answer


def test_reasoned_definition_covers_condition_and_rationale() -> None:
    query = "What is early stopping and why does it reduce overfitting?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "Early stopping is a regularization method that interrupts training early.",
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=2-2\n"
                "Training stops when validation error reaches its minimum, before it rises again. "
                "This prevents the model from continuing to overfit the training data.",
            ),
        ],
    )

    assert "interrupts training early" in answer
    assert "validation error reaches its minimum" in answer
    assert "prevents the model" in answer


def test_enumeration_fallback_splits_dense_source_list_into_cited_items() -> None:
    query = "Which common methods are listed in the overview?"
    plan = build_answer_plan(query, "research")
    answer = SynthesisService._fallback_enumeration_answer(
        query=query,
        answer_plan=plan,
        response_mode="research",
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=1-1\n"
                "The overview lists common methods: linear and polynomial regression, nearest neighbors, "
                "decision trees, and ensemble methods.",
            )
        ],
    )

    assert "linear regression" in answer
    assert "polynomial regression" in answer
    assert "nearest neighbors" in answer
    assert "decision trees" in answer
    assert "ensemble methods" in answer
    assert answer.count("[1]") >= 1


def test_enumeration_fallback_recovers_a_heading_only_final_item() -> None:
    query = "What are the five principles of prompting?"
    answer = SynthesisService._fallback_enumeration_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        response_mode="research",
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=ocr pages=5-5\n"
                "Source heading: Give Direction / Specify Format / Provide Examples / Evaluate Quality\n"
                "Give Direction Describe the desired style. Specify Format Define the required structure."
            ),
            (
                2,
                "[2] doc=doc score=.9 source=ocr pages=5-6\n"
                "Source heading: Divide Labor\n"
                "Divide Labor Split tasks into multiple steps. These principles are model-agnostic."
            ),
        ],
    )

    assert "Give Direction [1]" in answer
    assert "Evaluate Quality [1]" in answer
    assert "Divide Labor [2]" in answer
    assert answer.count("[1]") >= 4


def test_recommendation_fallback_prefers_direct_optimization_instructions() -> None:
    query = "How should the website assets and animations be optimized?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=bm25 pages=7-7\n"
                "Audit /public: convert all images to WebP, add lazy loading. "
                "Preload hero font."
            ),
            (
                2,
                "[2] doc=doc score=.9 source=bm25 pages=7-8\n"
                "Images: lazy loading and explicit width attributes. Animations: add @media "
                "(prefers-reduced-motion)."
            ),
        ],
        additional_terms={"assets", "animations", "optimize"},
    )

    assert "WebP" in answer
    assert "lazy loading" in answer
    assert "Preload hero font" in answer


def test_how_can_fallback_prefers_direct_action_evidence() -> None:
    query = "How can a prompt give direction to an AI model?"
    answer = SynthesisService._fallback_planned_answer(
        query=query,
        answer_plan=build_answer_plan(query, "research"),
        context_chunks=[
            (
                1,
                "[1] doc=doc score=1 source=ocr pages=5-5\n"
                "Source heading: Give Direction / Specify Format\n"
                "Give Direction Describe the desired style in detail, or reference a relevant persona."
            ),
            (
                2,
                "[2] doc=doc score=.8 source=ocr pages=1-1\n"
                "A prompt is the input you provide when interfacing with an AI model."
            ),
        ],
    )

    assert "desired style" in answer
    assert "relevant persona" in answer


def test_hyphenated_focus_term_does_not_match_only_its_first_word() -> None:
    assert SynthesisService._sentence_score(
        "Learning long-range dependencies is difficult.",
        {"learning-rate"},
    ) == 0
    assert SynthesisService._sentence_score(
        "The learning rate increases during warmup.",
        {"learning-rate"},
    ) == 1
