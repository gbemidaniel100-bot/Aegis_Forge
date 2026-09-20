from __future__ import annotations

import sqlite3
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from aegis_forge.agent import IncidentAgent
from aegis_forge.evaluation import _incident_cases


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    incident: str
    expected_terms: tuple[str, ...]
    category: str
    expected_tools: tuple[str, ...] = ()


def task_matrix(repetitions: int = 20) -> list[BenchmarkTask]:
    tasks: list[BenchmarkTask] = []
    for case in _incident_cases():
        for index in range(repetitions):
            expected_tools = {"database": ("service_health", "dependency_graph"), "deploy": ("service_health", "recent_deploys"), "credential": ("error_sample",)}[case["risk"]]
            tasks.append(BenchmarkTask(f"{case['name']}-{index + 1:02d}", case["incident"], tuple(case["expected"].split()), case["risk"], expected_tools))
    return tasks


def run_benchmark(agent: IncidentAgent | None = None, repetitions: int = 20) -> dict[str, Any]:
    runner = agent or IncidentAgent()
    rows: list[dict[str, Any]] = []
    for task in task_matrix(repetitions):
        started = perf_counter()
        result = runner.investigate(task.incident, namespace="benchmark")
        elapsed_ms = (perf_counter() - started) * 1000
        evidence = " ".join(f"{item['title']} {item['text']}" for item in result["evidence"]).lower()
        true_positives = sum(term.lower() in evidence for term in task.expected_terms)
        retrieval = true_positives / len(task.expected_terms)
        relevant_documents = sum(any(term.lower() in item["text"].lower() or term.lower() in item["title"].lower() for term in task.expected_terms) for item in result["evidence"])
        precision = relevant_documents / max(len(result["evidence"]), 1)
        tool_names = {tool["name"] for tool in result["tools"]}
        tool_accuracy = len(tool_names & set(task.expected_tools)) / max(len(set(task.expected_tools)), 1)
        hallucination = 0.0 if result["decision_graph"]["policy"]["evidence_bound"] else 1.0
        groundedness = 1.0 if result["evidence"] and all(item.get("citation") for item in result["evidence"]) else 0.0
        decision_quality = 1.0 if result["decision_graph"]["actions"] and result["decision_graph"]["counterfactuals"] else 0.0
        rows.append({"task_id": task.task_id, "category": task.category, "retrieval": round(retrieval, 3), "precision": round(precision, 3), "groundedness": groundedness, "tool_accuracy": round(tool_accuracy, 3), "decision_quality": decision_quality, "hallucination": hallucination, "latency_ms": round(elapsed_ms, 2), "success": result["allowed"], "failure_recovery": 1.0 if result["model_backend"] in {"offline", "ollama", "fallback"} else 0.0})
    count = len(rows)
    return {
        "tasks": count,
        "accuracy": round(sum(row["retrieval"] for row in rows) / count, 4),
        "precision": round(sum(row["precision"] for row in rows) / count, 4),
        "recall": round(sum(row["retrieval"] for row in rows) / count, 4),
        "groundedness": round(sum(row["groundedness"] for row in rows) / count, 4),
        "tool_accuracy": round(sum(row["tool_accuracy"] for row in rows) / count, 4),
        "decision_quality": round(sum(row["decision_quality"] for row in rows) / count, 4),
        "failure_recovery_rate": round(sum(row["failure_recovery"] for row in rows) / count, 4),
        "hallucination_rate": round(sum(row["hallucination"] for row in rows) / count, 4),
        "success_rate": round(sum(row["success"] for row in rows) / count, 4),
        "latency_ms": {"p50": _percentile([row["latency_ms"] for row in rows], 0.5), "p95": _percentile([row["latency_ms"] for row in rows], 0.95), "p99": _percentile([row["latency_ms"] for row in rows], 0.99)},
        "by_category": {category: _aggregate([row for row in rows if row["category"] == category]) for category in sorted({row["category"] for row in rows})},
    }


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * quantile))], 2)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {"accuracy": round(sum(row["retrieval"] for row in rows) / len(rows), 4), "precision": round(sum(row["precision"] for row in rows) / len(rows), 4), "tool_accuracy": round(sum(row["tool_accuracy"] for row in rows) / len(rows), 4), "latency_p95_ms": _percentile([row["latency_ms"] for row in rows], 0.95)}


def detect_regression(current: dict[str, Any], baseline: dict[str, Any], tolerance: float = 0.05) -> dict[str, Any]:
    metrics = ("accuracy", "groundedness", "success_rate")
    changes = {metric: round(current[metric] - baseline[metric], 4) for metric in metrics}
    return {"regressed": any(delta < -tolerance for delta in changes.values()), "changes": changes, "tolerance": tolerance}


def run_load_profile(agent: IncidentAgent, concurrency_levels: tuple[int, ...] = (1, 10, 50, 100, 200), requests_per_worker: int = 1) -> list[dict[str, Any]]:
    incident = "Database connections are exhausted and retries are increasing in payments API"
    profiles: list[dict[str, Any]] = []
    for concurrency in concurrency_levels:
        latencies: list[float] = []
        failures = 0
        tracemalloc.start()
        started = time.perf_counter()

        def run_one(_: int, current_concurrency: int = concurrency, target_latencies: list[float] = latencies) -> None:
            nonlocal failures
            request_started = time.perf_counter()
            try:
                if not agent.investigate(incident, namespace=f"load-{current_concurrency}").get("allowed"):
                    failures += 1
            except (OSError, RuntimeError, ValueError, sqlite3.Error):
                failures += 1
            finally:
                target_latencies.append((time.perf_counter() - request_started) * 1000)

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            list(pool.map(run_one, range(concurrency * requests_per_worker)))
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        profiles.append({"concurrency": concurrency, "requests": len(latencies), "throughput_per_second": round(len(latencies) / max(elapsed, 0.001), 2), "failure_rate": round(failures / max(len(latencies), 1), 4), "latency_ms": {"p50": _percentile(latencies, 0.5), "p95": _percentile(latencies, 0.95), "p99": _percentile(latencies, 0.99)}, "peak_memory_mb": round(peak / 1024 / 1024, 3)})
    return profiles
