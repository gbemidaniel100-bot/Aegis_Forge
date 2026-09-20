from __future__ import annotations

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


def task_matrix(repetitions: int = 20) -> list[BenchmarkTask]:
    tasks: list[BenchmarkTask] = []
    for case in _incident_cases():
        for index in range(repetitions):
            tasks.append(BenchmarkTask(f"{case['name']}-{index + 1:02d}", case["incident"], tuple(case["expected"].split()), case["risk"]))
    return tasks


def run_benchmark(agent: IncidentAgent | None = None, repetitions: int = 20) -> dict[str, Any]:
    runner = agent or IncidentAgent()
    rows: list[dict[str, Any]] = []
    for task in task_matrix(repetitions):
        started = perf_counter()
        result = runner.investigate(task.incident, namespace="benchmark")
        elapsed_ms = (perf_counter() - started) * 1000
        evidence = " ".join(f"{item['title']} {item['text']}" for item in result["evidence"]).lower()
        retrieval = sum(term.lower() in evidence for term in task.expected_terms) / len(task.expected_terms)
        hallucination = 0.0 if result["decision_graph"]["policy"]["evidence_bound"] else 1.0
        rows.append({"task_id": task.task_id, "category": task.category, "retrieval": round(retrieval, 3), "hallucination": hallucination, "latency_ms": round(elapsed_ms, 2), "success": result["allowed"]})
    count = len(rows)
    return {
        "tasks": count,
        "accuracy": round(sum(row["retrieval"] for row in rows) / count, 4),
        "hallucination_rate": round(sum(row["hallucination"] for row in rows) / count, 4),
        "success_rate": round(sum(row["success"] for row in rows) / count, 4),
        "latency_ms": {"p50": _percentile([row["latency_ms"] for row in rows], 0.5), "p95": _percentile([row["latency_ms"] for row in rows], 0.95), "p99": _percentile([row["latency_ms"] for row in rows], 0.99)},
        "by_category": {category: _aggregate([row for row in rows if row["category"] == category]) for category in sorted({row["category"] for row in rows})},
    }


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * quantile))], 2)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {"accuracy": round(sum(row["retrieval"] for row in rows) / len(rows), 4), "latency_p95_ms": _percentile([row["latency_ms"] for row in rows], 0.95)}
