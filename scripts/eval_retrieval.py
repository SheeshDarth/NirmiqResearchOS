import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = WORKSPACE_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.config import get_settings
from app.core.deps import AppContainer
from app.api.schemas.query import QueryRequest


@dataclass(slots=True)
class EvalSample:
    query: str
    expected_document_ids: list[str]
    expected_chunk_ids: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval metrics for NIRMIQ.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=WORKSPACE_ROOT / "data" / "processed" / "eval" / "qa_labels.jsonl",
        help="Path to JSONL dataset with query + expected ids.",
    )
    parser.add_argument(
        "--k",
        type=int,
        nargs="+",
        default=[3, 5, 8],
        help="K values for Recall@K.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write metrics JSON.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["hybrid", "bm25", "vector"],
        help="Retrieval modes to evaluate: hybrid bm25 vector",
    )
    parser.add_argument(
        "--full-query",
        action="store_true",
        help="Run the full query pipeline and include grounding/synthesis metrics.",
    )
    return parser.parse_args()


def load_samples(path: Path) -> list[EvalSample]:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Create labels under data/processed/eval/qa_labels.jsonl."
        )
    samples: list[EvalSample] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        payload = json.loads(raw)
        query = str(payload.get("query", "")).strip()
        expected_doc_ids = [str(value) for value in payload.get("expected_document_ids", [])]
        expected_chunk_ids = [str(value) for value in payload.get("expected_chunk_ids", [])]
        if not query:
            raise ValueError(f"Line {line_no} missing query.")
        if not expected_doc_ids and not expected_chunk_ids:
            raise ValueError(
                f"Line {line_no} must include expected_document_ids or expected_chunk_ids."
            )
        samples.append(
            EvalSample(
                query=query,
                expected_document_ids=expected_doc_ids,
                expected_chunk_ids=expected_chunk_ids,
            )
        )
    return samples


def reciprocal_rank(retrieved: list[str], expected: set[str]) -> float:
    for rank, item in enumerate(retrieved, start=1):
        if item in expected:
            return 1.0 / rank
    return 0.0


def has_hit_at_k(retrieved: list[str], expected: set[str], k: int) -> bool:
    return any(item in expected for item in retrieved[:k])


async def run_eval_for_mode(
    samples: list[EvalSample], ks: list[int], mode: str, container: AppContainer, full_query: bool
) -> dict[str, Any]:
    recall_hits = {k: 0 for k in ks}
    mrr_sum = 0.0
    citation_presence_hits = 0
    citation_expected_hits = 0
    level_counts = {"chunk": 0, "document": 0}
    grounding_state_counts = {"strong": 0, "moderate": 0, "weak": 0, "unknown": 0}
    grounding_score_sum = 0.0
    citation_count_sum = 0
    citation_anchor_hits = 0
    grounded_response_hits = 0
    generation_backend_counts: dict[str, int] = {}
    total = len(samples)

    for index, sample in enumerate(samples):
        if full_query:
            response = await container.query_service.preview(
                QueryRequest(
                    session_id=f"eval-{mode}-{index}",
                    query=sample.query,
                    retrieval_mode=mode,  # type: ignore[arg-type]
                    debug=True,
                )
            )
            answer = response.answer
            citations = response.citations
            retrieval_meta = response.retrieval_meta or {}
            grounded_response_hits += 1 if response.grounded else 0
            grounding_state = str(retrieval_meta.get("grounding_state", "unknown"))
            grounding_state_counts[grounding_state] = grounding_state_counts.get(grounding_state, 0) + 1
            grounding_score_sum += float(retrieval_meta.get("grounding_score", 0.0) or 0.0)
            citation_count_sum += int(retrieval_meta.get("citation_count", len(citations)) or len(citations))
            citation_anchor_hits += 1 if contains_citation_anchor(answer) else 0
            backend = str(retrieval_meta.get("generation_backend", "unknown"))
            generation_backend_counts[backend] = generation_backend_counts.get(backend, 0) + 1
            retrieved_chunk_ids = [citation.chunk_id for citation in citations]
            retrieved_doc_ids = [citation.document_id for citation in citations]
            citation_presence_hits += 1 if citations else 0
        else:
            bundle = await container.retrieval_service.retrieve_with_mode(sample.query, mode=mode)
            retrieved_chunk_ids = [chunk.chunk_id for chunk in bundle.chunks]
            retrieved_doc_ids = [chunk.document_id for chunk in bundle.chunks]
            citation_presence_hits += 1 if bundle.chunks else 0

        if sample.expected_chunk_ids:
            expected = set(sample.expected_chunk_ids)
            retrieved = retrieved_chunk_ids
            level_counts["chunk"] += 1
        else:
            expected = set(sample.expected_document_ids)
            retrieved = retrieved_doc_ids
            level_counts["document"] += 1

        mrr_sum += reciprocal_rank(retrieved, expected)
        for k in ks:
            if has_hit_at_k(retrieved, expected, k):
                recall_hits[k] += 1
        if any(item in expected for item in retrieved):
            citation_expected_hits += 1

    target_level = "mixed"
    if level_counts["chunk"] and not level_counts["document"]:
        target_level = "chunk"
    if level_counts["document"] and not level_counts["chunk"]:
        target_level = "document"

    recall_at_k = {f"recall@{k}": (recall_hits[k] / total if total else 0.0) for k in ks}
    metrics = {
        "mode": mode,
        "samples": total,
        "target_level": target_level if total else "unknown",
        "mrr": (mrr_sum / total if total else 0.0),
        **recall_at_k,
        "citation_presence_rate": (citation_presence_hits / total if total else 0.0),
        "citation_expected_coverage": (citation_expected_hits / total if total else 0.0),
    }
    if full_query:
        metrics["grounding_metrics"] = {
            "grounded_response_rate": (grounded_response_hits / total if total else 0.0),
            "abstention_rate": 1.0 - (grounded_response_hits / total if total else 0.0),
            "citation_anchor_rate": (citation_anchor_hits / total if total else 0.0),
            "avg_grounding_score": (grounding_score_sum / total if total else 0.0),
            "avg_citation_count": (citation_count_sum / total if total else 0.0),
            "grounding_state_rates": {
                state: (count / total if total else 0.0) for state, count in grounding_state_counts.items()
            },
            "generation_backend_rates": {
                backend: (count / total if total else 0.0) for backend, count in generation_backend_counts.items()
            },
        }
    return metrics


def contains_citation_anchor(text: str) -> bool:
    return bool(re.search(r"\[\d+\]", text))


async def main_async() -> int:
    args = parse_args()
    ks = sorted(set(int(k) for k in args.k if int(k) > 0))
    if not ks:
        raise ValueError("At least one positive K value is required.")

    modes = [mode.strip().lower() for mode in args.modes if mode.strip()]
    valid_modes = [mode for mode in modes if mode in {"hybrid", "bm25", "vector"}]
    if not valid_modes:
        raise ValueError("At least one valid mode is required: hybrid bm25 vector.")

    samples = load_samples(args.dataset)
    settings = get_settings()
    container = AppContainer.from_settings(settings)
    container.sqlite_repo.init_db()

    per_mode: dict[str, Any] = {}
    for mode in valid_modes:
        per_mode[mode] = await run_eval_for_mode(
            samples=samples,
            ks=ks,
            mode=mode,
            container=container,
            full_query=bool(args.full_query),
        )
    output_payload: dict[str, Any] = {
        "dataset": str(args.dataset),
        "evaluation_mode": "full_query" if args.full_query else "retrieval",
        "modes": valid_modes,
        "results": per_mode,
    }
    output = json.dumps(output_payload, indent=2)
    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    return 0


def main() -> int:
    try:
        return asyncio.run(main_async())
    except Exception as exc:
        print(f"retrieval_eval_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
