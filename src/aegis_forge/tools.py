from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class ToolResult:
    name: str
    data: dict
    risk: str = "read-only"


class ToolRegistry:
    """Simulated production adapters; every operation is read-only and deterministic per incident."""

    def __init__(self):
        self.available = ("service_health", "recent_deploys", "error_sample", "dependency_graph")

    def run(self, name: str, incident: str) -> ToolResult:
        if name not in self.available:
            raise ValueError(f"Tool is not allowlisted: {name}")
        seed = int(hashlib.sha256(incident.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        if name == "service_health":
            data = {"status": "degraded", "error_rate": round(0.08 + rng.random() * 0.08, 3), "latency_ms": 420 + rng.randrange(180), "checked_at": datetime.now(UTC).isoformat()}
        elif name == "recent_deploys":
            data = {"latest": "payments-api@2026.09.20.3", "minutes_ago": 12, "changed": ["connection retry policy", "gateway timeout"]}
        elif name == "error_sample":
            data = {"top": "upstream timeout", "count_5m": 1842, "trace_ids": ["trc_7a91", "trc_82bc", "trc_0d11"]}
        else:
            data = {"critical_path": ["edge", "payments-api", "ledger-db"], "ledger_db": "warning", "owner": "payments-platform"}
        return ToolResult(name, data)
