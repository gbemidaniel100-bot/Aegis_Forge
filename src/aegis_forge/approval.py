from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from aegis_forge.db import Store


@dataclass
class ApprovalWorkflow:
    store: Store

    def propose(self, run_id: str, action: dict[str, Any]) -> dict[str, Any]:
        approval_id = str(uuid.uuid4())
        proposal = {"approval_id": approval_id, "run_id": run_id, "action": action, "status": "proposed"}
        self.store.trace(run_id, "approval_proposed", proposal)
        return proposal

    def approve(self, run_id: str, approval_id: str) -> dict[str, Any]:
        events = self.store.trace_for(run_id)
        proposal = next((event["payload"] for event in events if event["event"] == "approval_proposed" and event["payload"].get("approval_id") == approval_id), None)
        if proposal is None:
            raise ValueError("approval proposal not found")
        approved = {**proposal, "status": "approved"}
        self.store.trace(run_id, "approval_granted", approved)
        return approved

    def execute(self, run_id: str, approval_id: str) -> dict[str, Any]:
        events = self.store.trace_for(run_id)
        approved = next((event["payload"] for event in events if event["event"] == "approval_granted" and event["payload"].get("approval_id") == approval_id), None)
        if approved is None:
            raise ValueError("action requires explicit approval")
        result = {"approval_id": approval_id, "run_id": run_id, "status": "simulated-execution", "action": approved["action"]}
        self.store.trace(run_id, "action_executed", result)
        return result
