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
from app.api.schemas.ingest import IngestRequest
from app.api.schemas.query import QueryRequest
from app.domain.text_normalization import normalize_token_text


@dataclass(slots=True)
class EvalSample:
    sample_id: str
    query: str
    expected_document_ids: list[str]
    expected_chunk_ids: list[str]
    expected_phrases: list[str]
    source_file: str | None = None
    document_id: str | None = None
    category: str | None = None
    expected_answer: str | None = None


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
    parser.add_argument(
        "--auto-ingest-sources",
        action="store_true",
        help="Index source_file entries before evaluation and scope each query to that document.",
    )
    parser.add_argument(
        "--failures-output",
        type=Path,
        default=None,
        help="Optional JSONL path for per-sample misses and weak retrieval hits.",
    )
    return parser.parse_args()


def load_samples(path: Path) -> list[EvalSample]:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Create labels under data/processed/eval/qa_labels.jsonl."
        )
    samples: list[EvalSample] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not raw.strip():
            continue
        payload = json.loads(raw)
        query = str(payload.get("query", "")).strip()
        expected_doc_ids = [str(value) for value in payload.get("expected_document_ids", [])]
        expected_chunk_ids = [str(value) for value in payload.get("expected_chunk_ids", [])]
        expected_phrases = [
            normalize_eval_text(str(value))
            for value in payload.get("expected_phrases", [])
            if str(value).strip()
        ]
        source_file = str(payload.get("source_file") or "").strip() or None
        sample_id = str(payload.get("id") or f"line-{line_no}").strip()
        category = str(payload.get("category") or "").strip() or None
        expected_answer = str(payload.get("expected_answer") or "").strip() or None
        if not query:
            raise ValueError(f"Line {line_no} missing query.")
        if not expected_doc_ids and not expected_chunk_ids and not expected_phrases and not source_file:
            raise ValueError(
                f"Line {line_no} must include source_file, expected_document_ids, expected_chunk_ids, or expected_phrases."
            )
        samples.append(
            EvalSample(
                sample_id=sample_id,
                query=query,
                expected_document_ids=expected_doc_ids,
                expected_chunk_ids=expected_chunk_ids,
                expected_phrases=expected_phrases,
                source_file=source_file,
                category=category,
                expected_answer=expected_answer,
            )
        )
    return samples


async def resolve_sample_sources(
    samples: list[EvalSample],
    container: AppContainer,
    *,
    auto_ingest_sources: bool,
) -> None:
    for sample in samples:
        if not sample.source_file:
            continue
        source_path = Path(sample.source_file)
        if not source_path.is_absolute():
            source_path = (WORKSPACE_ROOT / source_path).resolve()
        else:
            source_path = source_path.resolve()
        row = container.sqlite_repo.get_document_by_source_path(str(source_path))
        if not row and auto_ingest_sources:
            response = await container.ingestion_service.ingest(
                IngestRequest(
                    source_path=str(source_path),
                    title=source_path.stem.replace("-", " ").replace("_", " ")[:120],
                    force_reindex=False,
                )
            )
            row = container.sqlite_repo.get_document_by_id(response.document_id)
        if row:
            sample.document_id = str(row["id"])
            if not sample.expected_document_ids:
                sample.expected_document_ids = [sample.document_id]


def reciprocal_rank(retrieved: list[str], expected: set[str]) -> float:
    for rank, item in enumerate(retrieved, start=1):
        if item in expected:
            return 1.0 / rank
    return 0.0


def has_hit_at_k(retrieved: list[str], expected: set[str], k: int) -> bool:
    return any(item in expected for item in retrieved[:k])


def phrase_hit(text: str, expected_phrases: list[str]) -> bool:
    normalized = normalize_eval_text(text)
    return any(phrase in normalized for phrase in expected_phrases)


def phrase_reciprocal_rank(retrieved_texts: list[str], expected_phrases: list[str]) -> float:
    for rank, text in enumerate(retrieved_texts, start=1):
        if phrase_hit(text, expected_phrases):
            return 1.0 / rank
    return 0.0


def phrase_hit_at_k(retrieved_texts: list[str], expected_phrases: list[str], k: int) -> bool:
    return any(phrase_hit(text, expected_phrases) for text in retrieved_texts[:k])


def binary_ndcg_at_k(retrieved: list[str], expected: set[str], k: int) -> float:
    dcg = 0.0
    matched: set[str] = set()
    for rank, item in enumerate(retrieved[:k], start=1):
        if item in expected and item not in matched:
            matched.add(item)
            dcg += 1.0 / math_log2(rank + 1)
    ideal_hits = min(len(expected), k)
    idcg = sum(1.0 / math_log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def phrase_ndcg_at_k(retrieved_texts: list[str], expected_phrases: list[str], k: int) -> float:
    dcg = 0.0
    matched: set[str] = set()
    for rank, text in enumerate(retrieved_texts[:k], start=1):
        lowered = normalize_eval_text(text)
        hit = next((phrase for phrase in expected_phrases if phrase in lowered and phrase not in matched), None)
        if hit:
            matched.add(hit)
            dcg += 1.0 / math_log2(rank + 1)
    ideal_hits = min(len(set(expected_phrases)), k)
    idcg = sum(1.0 / math_log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def math_log2(value: int) -> float:
    import math

    return math.log2(value)


async def run_eval_for_mode(
    samples: list[EvalSample],
    ks: list[int],
    mode: str,
    container: AppContainer,
    full_query: bool,
    failure_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    recall_hits = {k: 0 for k in ks}
    ndcg_sums = {k: 0.0 for k in ks}
    mrr_sum = 0.0
    citation_presence_hits = 0
    citation_expected_hits = 0
    level_counts = {"chunk": 0, "document": 0, "phrase": 0}
    grounding_state_counts = {"strong": 0, "moderate": 0, "weak": 0, "unknown": 0}
    grounding_score_sum = 0.0
    citation_count_sum = 0
    citation_anchor_hits = 0
    grounded_response_hits = 0
    generation_backend_counts: dict[str, int] = {}
    total = len(samples)
    max_k = max(ks) if ks else 0
    review_rank_threshold = min(ks) if ks else 3

    for index, sample in enumerate(samples):
        if full_query:
            response = await container.query_service.preview(
                QueryRequest(
                    session_id=f"eval-{mode}-{index}",
                    query=sample.query,
                    document_id=sample.document_id,
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
            raw_cited_chunk_ids = retrieval_meta.get("cited_context_chunk_ids")
            if isinstance(raw_cited_chunk_ids, list) and raw_cited_chunk_ids:
                retrieved_chunk_ids = [str(chunk_id) for chunk_id in raw_cited_chunk_ids if str(chunk_id).strip()]
            else:
                retrieved_chunk_ids = [citation.chunk_id for citation in citations]
            cited_rows = container.sqlite_repo.get_chunks_by_ids(retrieved_chunk_ids)
            retrieved_doc_ids = [
                str(cited_rows[chunk_id]["document_id"])
                for chunk_id in retrieved_chunk_ids
                if chunk_id in cited_rows
            ] or [citation.document_id for citation in citations]
            retrieved_texts = [
                str(cited_rows[chunk_id]["text"])
                for chunk_id in retrieved_chunk_ids
                if chunk_id in cited_rows
            ] or [str(citation.excerpt or "") for citation in citations]
            citation_presence_hits += 1 if citations else 0
        else:
            bundle = await container.retrieval_service.retrieve_with_mode(
                sample.query,
                mode=mode,
                document_id=sample.document_id,
            )
            retrieved_chunk_ids = [chunk.chunk_id for chunk in bundle.chunks]
            retrieved_doc_ids = [chunk.document_id for chunk in bundle.chunks]
            retrieved_texts = [chunk.text for chunk in bundle.chunks]
            citation_presence_hits += 1 if bundle.chunks else 0

        if sample.expected_chunk_ids:
            expected = set(sample.expected_chunk_ids)
            retrieved = retrieved_chunk_ids
            level_counts["chunk"] += 1
            first_rank = first_id_rank(retrieved, expected)
            mrr_sum += reciprocal_rank(retrieved, expected)
            for k in ks:
                if has_hit_at_k(retrieved, expected, k):
                    recall_hits[k] += 1
                ndcg_sums[k] += binary_ndcg_at_k(retrieved, expected, k)
            if any(item in expected for item in retrieved):
                citation_expected_hits += 1
            maybe_record_failure(
                failure_records,
                sample=sample,
                mode=mode,
                target_level="chunk",
                first_rank=first_rank,
                max_k=max_k,
                review_rank_threshold=review_rank_threshold,
                retrieved_chunk_ids=retrieved_chunk_ids,
                retrieved_doc_ids=retrieved_doc_ids,
                retrieved_texts=retrieved_texts,
            )
        elif sample.expected_phrases:
            level_counts["phrase"] += 1
            first_rank = first_phrase_rank(retrieved_texts, sample.expected_phrases)
            mrr_sum += phrase_reciprocal_rank(retrieved_texts, sample.expected_phrases)
            for k in ks:
                if phrase_hit_at_k(retrieved_texts, sample.expected_phrases, k):
                    recall_hits[k] += 1
                ndcg_sums[k] += phrase_ndcg_at_k(retrieved_texts, sample.expected_phrases, k)
            if any(phrase_hit(text, sample.expected_phrases) for text in retrieved_texts):
                citation_expected_hits += 1
            maybe_record_failure(
                failure_records,
                sample=sample,
                mode=mode,
                target_level="phrase",
                first_rank=first_rank,
                max_k=max_k,
                review_rank_threshold=review_rank_threshold,
                retrieved_chunk_ids=retrieved_chunk_ids,
                retrieved_doc_ids=retrieved_doc_ids,
                retrieved_texts=retrieved_texts,
            )
        elif sample.expected_document_ids:
            expected = set(sample.expected_document_ids)
            retrieved = retrieved_doc_ids
            level_counts["document"] += 1
            first_rank = first_id_rank(retrieved, expected)
            mrr_sum += reciprocal_rank(retrieved, expected)
            for k in ks:
                if has_hit_at_k(retrieved, expected, k):
                    recall_hits[k] += 1
                ndcg_sums[k] += binary_ndcg_at_k(retrieved, expected, k)
            if any(item in expected for item in retrieved):
                citation_expected_hits += 1
            maybe_record_failure(
                failure_records,
                sample=sample,
                mode=mode,
                target_level="document",
                first_rank=first_rank,
                max_k=max_k,
                review_rank_threshold=review_rank_threshold,
                retrieved_chunk_ids=retrieved_chunk_ids,
                retrieved_doc_ids=retrieved_doc_ids,
                retrieved_texts=retrieved_texts,
            )
        else:
            raise ValueError(f"Eval sample missing expectation target: {sample.query}")

    target_level = "mixed"
    if level_counts["chunk"] and not level_counts["document"]:
        target_level = "chunk"
    if level_counts["document"] and not level_counts["chunk"]:
        target_level = "document"
    if level_counts["phrase"] and not level_counts["chunk"] and not level_counts["document"]:
        target_level = "phrase"

    recall_at_k = {f"recall@{k}": (recall_hits[k] / total if total else 0.0) for k in ks}
    ndcg_at_k = {f"ndcg@{k}": (ndcg_sums[k] / total if total else 0.0) for k in ks}
    metrics = {
        "mode": mode,
        "samples": total,
        "target_level": target_level if total else "unknown",
        "mrr": (mrr_sum / total if total else 0.0),
        **recall_at_k,
        **ndcg_at_k,
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


def normalize_eval_text(text: str) -> str:
    return normalize_token_text(text)


def first_id_rank(retrieved: list[str], expected: set[str]) -> int:
    for rank, item in enumerate(retrieved, start=1):
        if item in expected:
            return rank
    return 0


def first_phrase_rank(retrieved_texts: list[str], expected_phrases: list[str]) -> int:
    for rank, text in enumerate(retrieved_texts, start=1):
        if phrase_hit(text, expected_phrases):
            return rank
    return 0


def maybe_record_failure(
    failure_records: list[dict[str, Any]] | None,
    *,
    sample: EvalSample,
    mode: str,
    target_level: str,
    first_rank: int,
    max_k: int,
    review_rank_threshold: int,
    retrieved_chunk_ids: list[str],
    retrieved_doc_ids: list[str],
    retrieved_texts: list[str],
) -> None:
    if failure_records is None:
        return
    if first_rank and first_rank <= review_rank_threshold:
        return

    if first_rank == 0:
        status = f"missed@{max_k}"
    elif first_rank > max_k:
        status = f"missed@{max_k}"
    else:
        status = f"late_hit_rank_{first_rank}"

    failure_records.append(
        {
            "sample_id": sample.sample_id,
            "category": sample.category,
            "mode": mode,
            "status": status,
            "target_level": target_level,
            "first_expected_rank": first_rank,
            "query": sample.query,
            "source_file": sample.source_file,
            "document_id": sample.document_id,
            "expected_answer": sample.expected_answer,
            "expected_phrases": sample.expected_phrases,
            "top_chunks": [
                {
                    "rank": rank,
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "excerpt": compact_excerpt(text),
                }
                for rank, (chunk_id, document_id, text) in enumerate(
                    zip(retrieved_chunk_ids[:max_k], retrieved_doc_ids[:max_k], retrieved_texts[:max_k]),
                    start=1,
                )
            ],
        }
    )


def compact_excerpt(text: str, limit: int = 260) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


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
    await resolve_sample_sources(
        samples=samples,
        container=container,
        auto_ingest_sources=bool(args.auto_ingest_sources),
    )

    per_mode: dict[str, Any] = {}
    failure_records: list[dict[str, Any]] = []
    for mode in valid_modes:
        per_mode[mode] = await run_eval_for_mode(
            samples=samples,
            ks=ks,
            mode=mode,
            container=container,
            full_query=bool(args.full_query),
            failure_records=failure_records if args.failures_output else None,
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
    if args.failures_output:
        args.failures_output.parent.mkdir(parents=True, exist_ok=True)
        args.failures_output.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in failure_records) + "\n",
            encoding="utf-8",
        )
    return 0


def main() -> int:
    try:
        return asyncio.run(main_async())
    except Exception as exc:
        print(f"retrieval_eval_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
