from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aegis_forge.agent import IncidentAgent
from aegis_forge.db import Store
from aegis_forge.decision import DecisionEngine


@dataclass(frozen=True)
class ReplayResult:
    run_id: str
    source_events: int
    deterministic: bool
    stages: list[str]
    differences: list[str]


def replay_run(store: Store, run_id: str, agent: IncidentAgent) -> dict[str, Any]:
    events = store.trace_for(run_id)
    request = next((event["payload"].get("sanitized") for event in events if event["event"] == "security_gate"), None)
    if not request:
        raise ValueError("run has no replayable sanitized request")
    original = next((event["payload"] for event in events if event["event"] == "decision_graph"), None)
    if original:
        original = {key: value for key, value in original.items() if key != "decision_backend"}
    retrieval = next((event["payload"] for event in events if event["event"] == "retrieval"), {})
    tools = [event["payload"]["result"] for event in events if event["event"] == "tool_call" and event["payload"].get("result")]
    current = DecisionEngine().build(request, retrieval.get("hits", []), tools)
    replayed = agent.investigate(request, namespace="replay")
    differences = [] if original == current else ["decision_graph differs; external time or model output changed"]
    return {
        "run_id": run_id,
        "source_events": len(events),
        "replay_run_id": replayed["run_id"],
        "recorded_evidence": len(retrieval.get("hits", [])),
        "recorded_tools": len(tools),
        "deterministic": not differences,
        "stages": [event["event"] for event in events],
        "differences": differences,
    }
