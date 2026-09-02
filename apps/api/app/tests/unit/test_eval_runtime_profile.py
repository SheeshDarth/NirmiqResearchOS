from scripts.eval_retrieval import (
    assess_performance_budgets,
    summarize_sample_latency,
)


def test_sample_latency_summary_profiles_query_stages() -> None:
    summary = summarize_sample_latency(
        [
            {
                "sample_id": "sample-a",
                "category": "definition",
                "seconds": 2.0,
                "stages_ms": {
                    "retrieval": 1000.0,
                    "synthesis": 500.0,
                    "total": 2000.0,
                },
            },
            {
                "sample_id": "sample-b",
                "category": "mechanism",
                "seconds": 3.0,
                "stages_ms": {
                    "retrieval": 2000.0,
                    "synthesis": 600.0,
                    "total": 3000.0,
                },
            },
        ],
        slowest_limit=1,
    )

    assert summary["slowest_samples"][0]["sample_id"] == "sample-b"
    stages = summary["query_stage_metrics_ms"]
    assert stages["retrieval"]["avg"] == 1500.0
    assert stages["retrieval"]["share_of_total"] == 0.6
    assert stages["synthesis"]["max"] == 600.0


def test_performance_budgets_warn_without_failing_quality_gate() -> None:
    assessment = assess_performance_budgets(
        total_seconds=700.0,
        source_resolution_seconds=170.0,
        results={"bm25": {"latency_metrics": {"p95_seconds": 26.0}}},
        total_budget_seconds=660.0,
        source_resolution_budget_seconds=180.0,
        p95_sample_budget_seconds=25.0,
    )

    assert assessment["advisory"] is True
    assert assessment["status"] == "warning"
    assert assessment["warning_count"] == 2
    assert {
        warning["metric"] for warning in assessment["warnings"]
    } == {"total_seconds", "p95_sample_seconds"}


def test_performance_budgets_report_when_not_configured() -> None:
    assessment = assess_performance_budgets(
        total_seconds=1.0,
        source_resolution_seconds=0.2,
        results={},
    )

    assert assessment["status"] == "not_configured"
    assert assessment["warnings"] == []
