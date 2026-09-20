from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class Metrics:
    requests: Counter[str] = field(default_factory=Counter)
    durations: list[float] = field(default_factory=list)

    @contextmanager
    def observe(self, operation: str) -> Iterator[None]:
        started = perf_counter()
        self.requests[f"{operation}.started"] += 1
        try:
            yield
            self.requests[f"{operation}.succeeded"] += 1
        except Exception:
            self.requests[f"{operation}.failed"] += 1
            raise
        finally:
            self.durations.append(perf_counter() - started)

    def snapshot(self) -> dict[str, object]:
        durations = self.durations[-1000:]
        return {
            "counters": dict(self.requests),
            "duration_count": len(durations),
            "duration_avg_ms": round(sum(durations) / len(durations) * 1000, 2) if durations else 0.0,
            "duration_max_ms": round(max(durations) * 1000, 2) if durations else 0.0,
        }

    def prometheus(self) -> str:
        lines = [
            "# HELP aegis_requests_total Number of Aegis operation events.",
            "# TYPE aegis_requests_total counter",
        ]
        for name, value in sorted(self.requests.items()):
            lines.append(f'aegis_requests_total{{event="{name}"}} {value}')
        snapshot = self.snapshot()
        lines.extend([
            "# HELP aegis_operation_duration_ms_avg Average operation duration in milliseconds.",
            "# TYPE aegis_operation_duration_ms_avg gauge",
            f"aegis_operation_duration_ms_avg {snapshot['duration_avg_ms']}",
            "# HELP aegis_operation_duration_ms_max Maximum recent operation duration in milliseconds.",
            "# TYPE aegis_operation_duration_ms_max gauge",
            f"aegis_operation_duration_ms_max {snapshot['duration_max_ms']}",
        ])
        return "\n".join(lines) + "\n"
