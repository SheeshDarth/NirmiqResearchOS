from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def request_json(url: str, payload: dict[str, Any] | None = None) -> tuple[dict[str, Any], float]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method="POST" if body else "GET",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result, (time.perf_counter() - started) * 1000


def summarize(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    p95_index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1))
    return {
        "count": len(samples),
        "min_ms": round(ordered[0], 2),
        "median_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(ordered[p95_index], 2),
        "max_ms": round(ordered[-1], 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the local NIRMIQ runtime without cloud calls.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--query")
    parser.add_argument("--document-id")
    parser.add_argument("--retrieval-mode", choices=("hybrid", "bm25", "vector"), default="bm25")
    parser.add_argument("--output", default="temp/runtime/runtime-benchmark.json")
    args = parser.parse_args()

    iterations = max(1, min(args.iterations, 25))
    result: dict[str, Any] = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "logical_cpus": os.cpu_count(),
        "api_base": args.api_base,
    }
    try:
        readiness_samples: list[float] = []
        readiness: dict[str, Any] = {}
        for _ in range(iterations):
            readiness, elapsed = request_json(f"{args.api_base.rstrip('/')}/health/readiness")
            readiness_samples.append(elapsed)
        result["runtime"] = {
            "profile": readiness.get("runtime_profile"),
            "low_memory_mode": readiness.get("low_memory_mode"),
            "ollama_available": readiness.get("ollama_available"),
            "vector_store_available": readiness.get("vector_store_available"),
            "cloud_api_required": readiness.get("cloud_api_required"),
        }
        result["readiness_latency"] = summarize(readiness_samples)
        if len(readiness_samples) > 1:
            result["readiness_latency"]["first_ms"] = round(readiness_samples[0], 2)
            result["readiness_warm_latency"] = summarize(readiness_samples[1:])

        if args.query:
            query_samples: list[float] = []
            last_response: dict[str, Any] = {}
            payload = {
                "session_id": "runtime-benchmark",
                "query": args.query,
                "document_id": args.document_id,
                "mode": "research",
                "retrieval_profile": "balanced",
                "retrieval_mode": args.retrieval_mode,
                "debug": True,
            }
            for _ in range(iterations):
                last_response, elapsed = request_json(
                    f"{args.api_base.rstrip('/')}/query",
                    payload,
                )
                query_samples.append(elapsed)
            meta = last_response.get("retrieval_meta") or {}
            result["query_latency"] = summarize(query_samples)
            result["query_result"] = {
                "grounded": last_response.get("grounded"),
                "citation_count": len(last_response.get("citations") or []),
                "generation_backend": meta.get("generation_backend"),
                "generation_model_requested": meta.get("generation_model_requested"),
                "generation_model_used": meta.get("generation_model_used"),
                "generation_model_fallback": meta.get("generation_model_fallback"),
                "effective_retrieval_mode": meta.get("effective_retrieval_mode"),
                "answer_characters": len(last_response.get("answer") or ""),
            }
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        result["error"] = str(exc)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
