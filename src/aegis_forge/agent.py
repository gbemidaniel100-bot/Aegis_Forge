from __future__ import annotations

from dataclasses import dataclass
import os
import uuid

from aegis_forge.config import settings
from aegis_forge.db import Store
from aegis_forge.model import LocalModel
from aegis_forge.retrieval import Retriever
from aegis_forge.security import GuardResult, inspect_input, redact
from aegis_forge.tools import ToolRegistry


@dataclass
class InvestigationResult:
    run_id: str
    summary: str
    evidence: list[dict]
    tools: list[dict]
    trace: list[dict]
    allowed: bool = True
    reasons: list[str] | None = None


class IncidentAgent:
    def __init__(self, storage_path: str | None = None, model: LocalModel | None = None):
        self.storage_path = storage_path or settings.db_path
        self.store = Store(self.storage_path)
        self.retriever = Retriever()
        self.registry = ToolRegistry()
        self.model = model or LocalModel(settings.ollama_url, settings.model)

    def investigate(self, incident: str, namespace: str = "default") -> dict:
        run_id = str(uuid.uuid4())
        guard = inspect_input(incident)
        self.store.trace(run_id, "security_gate", {"allowed": guard.allowed, "reasons": guard.reasons, "sanitized": guard.sanitized})
        if not guard.allowed:
            return {
                "run_id": run_id,
                "allowed": False,
                "reasons": guard.reasons,
                "summary": "Request blocked by security policy",
                "evidence": [],
                "tools": [],
                "trace": self.store.trace_for(run_id),
            }

        sanitized = redact(guard.sanitized)
        evidence = self.retriever.search(sanitized, limit=3)
        self.store.trace(run_id, "retrieval", {"query": sanitized, "hits": evidence})

        tool_calls: list[dict] = []
        for tool_name in self.registry.available[: min(len(self.registry.available), settings.max_tool_calls)]:
            if "database" in sanitized.lower() and tool_name == "service_health":
                result = self.registry.run(tool_name, sanitized)
                tool_calls.append({"name": result.name, "risk": result.risk, "data": result.data})
            elif "5xx" in sanitized.lower() and tool_name in {"service_health", "recent_deploys"}:
                result = self.registry.run(tool_name, sanitized)
                tool_calls.append({"name": result.name, "risk": result.risk, "data": result.data})
            elif "credential" in sanitized.lower() and tool_name == "error_sample":
                result = self.registry.run(tool_name, sanitized)
                tool_calls.append({"name": result.name, "risk": result.risk, "data": result.data})
            elif "database" in sanitized.lower() and tool_name == "dependency_graph":
                result = self.registry.run(tool_name, sanitized)
                tool_calls.append({"name": result.name, "risk": result.risk, "data": result.data})
            self.store.trace(run_id, "tool_call", {"name": tool_name, "triggered": True})

        if not tool_calls:
            tool_calls.append({"name": "service_health", "risk": "read-only", "data": {"status": "no_specific_signal_matched"}})

        prompt = (
            "You are Aegis Forge, a careful incident responder. "
            "Use only the provided evidence and tool outputs. "
            "Summarize likely root cause, affected service, likely next action, and the confidence level.\n\n"
            f"Incident: {sanitized}\n\nEvidence:\n" + "\n".join(f"- {item['title']}: {item['text']}" for item in evidence) + "\n\nTool outputs:\n" + str(tool_calls)
        )
        response, backend = self.model.complete(prompt)
        if not response:
            response = (
                "Likely root cause: a recent change introduced a regression in the affected service. "
                "Evidence suggests the incident is consistent with a deploy-driven failure pattern. "
                "Recommended action: verify the newest release, inspect database or gateway health, and confirm the error budget before rollback or escalation."
            )
            backend = "offline"
        self.store.trace(run_id, "completion", {"model_backend": backend, "response": response})
        memory_text = f"namespace={namespace}; incident={sanitized}; summary={response[:500]}"
        self.store.remember(namespace, memory_text, importance=0.8)

        result = {
            "run_id": run_id,
            "summary": response,
            "evidence": evidence,
            "tools": tool_calls,
            "trace": self.store.trace_for(run_id),
            "allowed": True,
            "model_backend": backend,
        }
        return result
