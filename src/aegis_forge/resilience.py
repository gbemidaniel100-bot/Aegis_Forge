from __future__ import annotations

from dataclasses import dataclass
from time import monotonic


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_seconds: float = 30.0
    failures: int = 0
    opened_at: float | None = None

    @property
    def open(self) -> bool:
        if self.opened_at is None:
            return False
        if monotonic() - self.opened_at >= self.recovery_seconds:
            self.opened_at = None
            self.failures = 0
            return False
        return True

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = monotonic()


@dataclass(frozen=True)
class Budget:
    max_attempts: int = 2
    timeout_seconds: float = 8.0

    def allow_attempt(self, attempt: int) -> bool:
        return attempt < self.max_attempts
