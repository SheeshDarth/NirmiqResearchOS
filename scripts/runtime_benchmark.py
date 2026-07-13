from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
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


def gpu_snapshot() -> list[dict[str, int | str]] | None:
    """Read bounded GPU telemetry when nvidia-smi is available."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    snapshots: list[dict[str, int | str]] = []
    for line in completed.stdout.splitlines():
        columns = [value.strip() for value in line.split(",")]
        if len(columns) != 4:
            continue
        try:
            snapshots.append(
                {
                    "name": columns[0],
                    "memory_total_mib": int(columns[1]),
                    "memory_used_mib": int(columns[2]),
                    "utilization_percent": int(columns[3]),
                }
            )
        except ValueError:
            continue
    return snapshots or None


def process_rss_bytes(process_id: int | None) -> int | None:
    """Return process RSS without adding a runtime dependency."""
    if not process_id or process_id <= 0:
        return None
    if os.name != "nt":
        try:
            for line in Path(f"/proc/{process_id}/status").read_text(encoding="utf-8").splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            return None
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("page_fault_count", ctypes.c_ulong),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
            ("quota_non_paged_pool_usage", ctypes.c_size_t),
            ("pagefile_usage", ctypes.c_size_t),
            ("peak_pagefile_usage", ctypes.c_size_t),
        ]

    process_query_information = 0x0400
    process_vm_read = 0x0010
    handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
        process_query_information | process_vm_read,
        False,
        process_id,
    )
    if not handle:
        return None
    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(  # type: ignore[attr-defined]
            handle,
            ctypes.byref(counters),
            counters.cb,
        ):
            return None
        return int(counters.working_set_size)
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]


def assess_runtime_budgets(result: dict[str, Any]) -> dict[str, Any]:
    """Evaluate measured values without making hardware variance a hard failure."""
    runtime = result.get("runtime") or {}
    profile = str(runtime.get("profile") or "balanced")
    low_resource = profile in {"low_memory", "cpu_offline"}
    checks: list[dict[str, Any]] = []

    def add_check(name: str, actual: float | int | None, maximum: float | int, unit: str) -> None:
        if actual is None:
            return
        checks.append(
            {
                "name": name,
                "actual": round(float(actual), 2),
                "maximum": maximum,
                "unit": unit,
                "passed": float(actual) <= float(maximum),
            }
        )

    readiness = result.get("readiness_warm_latency") or result.get("readiness_latency") or {}
    add_check(
        "warm_readiness_p95",
        readiness.get("p95_ms"),
        750 if low_resource else 500,
        "ms",
    )

    query = result.get("query_warm_latency") or result.get("query_latency") or {}
    add_check(
        "warm_generated_query_median",
        query.get("median_ms"),
        45_000 if low_resource else 25_000,
        "ms",
    )

    rss_bytes = result.get("api_rss_after_bytes")
    add_check(
        "api_rss",
        rss_bytes / (1024**2) if isinstance(rss_bytes, int) else None,
        1024 if low_resource else 1536,
        "MiB",
    )

    gpu_after = result.get("gpu_after") or []
    if not low_resource and gpu_after:
        used_values = [gpu.get("memory_used_mib") for gpu in gpu_after if isinstance(gpu, dict)]
        numeric_used = [value for value in used_values if isinstance(value, (int, float))]
        add_check("gpu_memory_used", max(numeric_used) if numeric_used else None, 5632, "MiB")

    return {
        "profile": profile,
        "status": "pass" if checks and all(check["passed"] for check in checks) else (
            "warn" if checks else "not_measured"
        ),
        "enforcement": "advisory",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the local NIRMIQ runtime without cloud calls.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--query")
    parser.add_argument("--document-id")
    parser.add_argument("--api-pid", type=int, help="Optional API process id for RSS sampling.")
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
        "gpu_before": gpu_snapshot(),
        "api_rss_before_bytes": process_rss_bytes(args.api_pid),
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
            result["query_latency"]["first_ms"] = round(query_samples[0], 2)
            if len(query_samples) > 1:
                result["query_warm_latency"] = summarize(query_samples[1:])
            result["query_samples_ms"] = [round(sample, 2) for sample in query_samples]
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

    result["gpu_after"] = gpu_snapshot()
    result["api_rss_after_bytes"] = process_rss_bytes(args.api_pid)
    result["budget_assessment"] = assess_runtime_budgets(result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
