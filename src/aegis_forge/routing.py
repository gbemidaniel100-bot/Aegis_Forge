from __future__ import annotations

import ipaddress
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlparse

from aegis_forge.model import LocalModel
from aegis_forge.resilience import Budget, CircuitBreaker


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    model: LocalModel
    priority: int
    context_limit: int = 12000
    max_complexity: int = 3
    expected_latency_ms: float = 1000.0


class ModelRouter:
    """Selects a local model by policy and fails over without hiding provider state."""

    def __init__(self, candidates: list[ModelCandidate], budget: Budget | None = None):
        self.candidates = sorted(candidates, key=lambda item: item.priority)
        self.budget = budget or Budget()
        self.breakers = {candidate.name: CircuitBreaker() for candidate in self.candidates}
        self.history: dict[str, dict[str, float]] = defaultdict(lambda: {"successes": 0.0, "failures": 0.0, "latency_ms": 0.0})

    @staticmethod
    def classify(prompt: str) -> dict[str, object]:
        words = len(prompt.split())
        signals = sum(term in prompt.lower() for term in ("compare", "counterfactual", "blast radius", "timeline", "multiple", "root cause"))
        complexity = min(3, 1 + int(words > 120) + int(signals >= 2))
        return {"level": complexity, "tokens_estimate": words, "signals": signals}

    def _rank(self, prompt: str) -> tuple[list[ModelCandidate], dict[str, object]]:
        task = self.classify(prompt)
        eligible = [candidate for candidate in self.candidates if task["level"] <= candidate.max_complexity and task["tokens_estimate"] * 5 <= candidate.context_limit]
        eligible = eligible or self.candidates
        def score(candidate: ModelCandidate) -> tuple[float, int]:
            stats = self.history[candidate.name]
            failures = stats["failures"]
            latency = stats["latency_ms"] or candidate.expected_latency_ms
            return (failures * 1000 + latency, candidate.priority)
        ranked = sorted(eligible, key=score)
        return ranked, {"complexity": task, "eligible": [candidate.name for candidate in eligible], "selected": ranked[0].name if ranked else "offline"}

    def complete(self, prompt: str) -> tuple[str, str, dict[str, object]]:
        started = time.perf_counter()
        attempts: list[dict[str, object]] = []
        candidates, selection = self._rank(prompt)
        for candidate in candidates:
            breaker = self.breakers[candidate.name]
            if breaker.open:
                attempts.append({"model": candidate.name, "status": "circuit-open"})
                continue
            for attempt in range(self.budget.max_attempts):
                if not self.budget.allow_attempt(attempt):
                    break
                try:
                    response, backend = candidate.model.complete(prompt, timeout=self.budget.timeout_seconds)
                    if response:
                        elapsed_ms = (time.perf_counter() - started) * 1000
                        breaker.success()
                        stats = self.history[candidate.name]
                        stats["successes"] += 1
                        stats["latency_ms"] = elapsed_ms
                        attempts.append({"model": candidate.name, "status": "success", "attempt": attempt + 1})
                        return response, backend, {"attempts": attempts, "latency_ms": round(elapsed_ms, 2), "selection": selection, "selected_reason": f"complexity={selection['complexity']['level']}; lowest observed failure/latency score"}
                    raise RuntimeError("empty model response")
                except (OSError, ValueError, RuntimeError) as exc:
                    breaker.failure()
                    self.history[candidate.name]["failures"] += 1
                    attempts.append({"model": candidate.name, "status": "failed", "attempt": attempt + 1, "error": type(exc).__name__})
        return "", "offline", {"attempts": attempts, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "selection": selection, "selected_reason": "all eligible providers failed or were circuit-open"}

    def complete_json(self, prompt: str, timeout: float = 8.0) -> tuple[dict, str]:
        candidates, _ = self._rank(prompt)
        for candidate in candidates:
            method = getattr(candidate.model, "complete_json", None)
            if method is None:
                continue
            payload, backend = method(prompt, timeout=timeout)
            if isinstance(payload, dict):
                return payload, backend
        text, backend, _ = self.complete(prompt)
        try:
            return json.loads(text), backend
        except (json.JSONDecodeError, TypeError):
            return {}, "offline"


def validate_model_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("model URL must use http(s) and include a host")
    blocked_hosts = {"127.0.0.1.nip.io", "169.254.169.254", "metadata.google.internal"}
    if parsed.hostname in blocked_hosts:
        raise ValueError("model URL targets a blocked metadata host")
    try:
        address = ipaddress.ip_address(parsed.hostname)
        if address.is_private and not address.is_loopback:
            raise ValueError("model URL targets a private network address")
    except ValueError as exc:
        if "private network" in str(exc):
            raise
    return url.rstrip("/")
