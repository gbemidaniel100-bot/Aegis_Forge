from __future__ import annotations

from typing import Any

from aegis_forge.db import Store
from aegis_forge.retrieval import Retriever


def _incident_cases() -> list[dict[str, str]]:
    return [
        {
            "name": "database_exhaustion",
            "incident": "Database connections are exhausted and retries are increasing in payments API",
            "expected": "database connection pool",
            "risk": "database",
        },
        {
            "name": "gateway_regression",
            "incident": "Gateway is returning elevated 5xx errors after the latest deploy",
            "expected": "error budget and rollback",
            "risk": "deploy",
        },
        {
            "name": "credential_exposure",
            "incident": "A token was exposed in a log line and needs immediate rotation",
            "expected": "rotate secrets and revoke credential",
            "risk": "credential",
        },
    ]


def _score_case(case: dict[str, str]) -> tuple[float, str]:
    hits = Retriever().search(case["incident"], limit=3)
    expected = case["expected"].lower().split()
    keywords = [token for token in expected if len(token) > 3]
    found = sum(1 for keyword in keywords if any(keyword in item["text"].lower() or keyword in item["title"].lower() for item in hits))
    score = found / max(len(keywords), 1)
    return score, f"retrieval matched {found}/{len(keywords)} expected signals for {case['risk']}"


def evaluate_case(case: dict[str, str], store: Store | None = None) -> dict[str, Any]:
    score, detail = _score_case(case)
    record = {"name": case["name"], "incident": case["incident"], "score": round(score, 4), "detail": detail, "risk": case["risk"]}
    if store is not None:
        store.add_eval(case["name"], "retrieval_recall", score, detail)
    return record


def evaluate_suite(store: Store | None = None) -> dict[str, Any]:
    cases = [_evaluate_case(case, store) for case in _incident_cases()]
    overall = sum(item["score"] for item in cases) / max(len(cases), 1)
    summary = {
        "overall": round(overall, 4),
        "cases": cases,
        "quality": "retrieval and evidence coverage" if overall >= 0.6 else "needs improvement",
    }
    if store is not None:
        store.add_eval("suite", "overall_recall", overall, "aggregate retrieval recall")
    return summary


def _evaluate_case(case: dict[str, str], store: Store | None = None) -> dict[str, Any]:
    record = evaluate_case(case, store)
    return {"name": record["name"], "score": record["score"], "detail": record["detail"], "risk": record["risk"]}
