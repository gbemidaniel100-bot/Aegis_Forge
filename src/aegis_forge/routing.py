from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

from aegis_forge.model import LocalModel
from aegis_forge.resilience import Budget, CircuitBreaker


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    model: LocalModel
    priority: int


class ModelRouter:
    """Selects a local model by policy and fails over without hiding provider state."""

    def __init__(self, candidates: list[ModelCandidate], budget: Budget | None = None):
        self.candidates = sorted(candidates, key=lambda item: item.priority)
        self.budget = budget or Budget()
        self.breakers = {candidate.name: CircuitBreaker() for candidate in self.candidates}

    def complete(self, prompt: str) -> tuple[str, str, dict[str, object]]:
        started = time.perf_counter()
        attempts: list[dict[str, object]] = []
        for candidate in self.candidates:
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
                        breaker.success()
                        attempts.append({"model": candidate.name, "status": "success", "attempt": attempt + 1})
                        return response, backend, {"attempts": attempts, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
                    raise RuntimeError("empty model response")
                except (OSError, ValueError, RuntimeError) as exc:
                    breaker.failure()
                    attempts.append({"model": candidate.name, "status": "failed", "attempt": attempt + 1, "error": type(exc).__name__})
        return "", "offline", {"attempts": attempts, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}


def validate_model_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("model URL must use http(s) and include a host")
    blocked_hosts = {"127.0.0.1.nip.io", "169.254.169.254", "metadata.google.internal"}
    if parsed.hostname in blocked_hosts:
        raise ValueError("model URL targets a blocked metadata host")
    return url.rstrip("/")
