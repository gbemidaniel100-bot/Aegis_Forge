from __future__ import annotations

import uuid
from dataclasses import dataclass

from aegis_forge.config import settings
from aegis_forge.db import Store
from aegis_forge.model import LocalModel
from aegis_forge.retrieval import Retriever
from aegis_forge.security import inspect_input, redact
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

    def _remembered_context(self, namespace: str, limit: int = 5) -> str:
        items = self.store.memories(namespace, limit=limit)
        if not items:
            return "No prior memory for this namespace."
        return "\n".join(f"- {item['content']}" for item in items)

    def _infer_confidence(self, evidence: list[dict], tool_calls: list[dict]) -> str:
        score = 0.35 + min(len(evidence) * 0.2, 0.4) + min(len(tool_calls) * 0.1, 0.25)
        if score >= 0.8:
            return "high"
        if score >= 0.6:
            return "medium"
        return "low"

    def _recommendations(self, incident: str, evidence: list[dict]) -> list[str]:
        lower = incident.lower()
        recs: list[str] = []
        if "database" in lower or "connection" in lower:
            recs.append("Check the database pool saturation and recent connection churn before changing the pool size.")
        if "5xx" in lower or "deploy" in lower:
            recs.append("Compare the newest deploy against the error budget and roll back only after validating the regression source.")
        if "credential" in lower or "token" in lower:
            recs.append("Immediately revoke and rotate the exposed secret and preserve forensic evidence for the audit trail.")
        if not recs:
            recs.append("Validate the top incident signal against source telemetry and confirm the affected owner before taking action.")
        if evidence:
            recs.append(f"Use the retrieved runbook guidance from {', '.join(item['title'] for item in evidence[:2])} as the anchor for the response.")
        return recs

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
                "confidence": "none",
                "recommendations": [],
                "observability": {"security_gate": "blocked"},
            }

        sanitized = redact(guard.sanitized)
        evidence = self.retriever.search(sanitized, limit=3)
        self.store.trace(run_id, "retrieval", {"query": sanitized, "hits": evidence})

        tool_calls: list[dict] = []
        for tool_name in self.registry.available[: min(len(self.registry.available), settings.max_tool_calls)]:
            signal = sanitized.lower()
            if "database" in signal and tool_name == "service_health" or "5xx" in signal and tool_name in {"service_health", "recent_deploys"} or "credential" in signal and tool_name == "error_sample" or "database" in signal and tool_name == "dependency_graph":
                result = self.registry.run(tool_name, sanitized)
                tool_calls.append({"name": result.name, "risk": result.risk, "data": result.data})
            self.store.trace(run_id, "tool_call", {"name": tool_name, "triggered": tool_name in {item['name'] for item in tool_calls}})

        if not tool_calls:
            tool_calls.append({"name": "service_health", "risk": "read-only", "data": {"status": "no_specific_signal_matched"}})

        prior_context = self._remembered_context(namespace)
        prompt = (
            "You are Aegis Forge, a careful incident responder. "
            "Use only the provided evidence, prior memory, and tool outputs. "
            "Do not speculate beyond the evidence. "
            "Return a concise, operational summary with root cause, affected service, recommended next step, and confidence.\n\n"
            f"Incident: {sanitized}\n\nPrior memory:\n{prior_context}\n\nEvidence:\n"
            + "\n".join(f"- {item['title']}: {item['text']}" for item in evidence)
            + "\n\nTool outputs:\n"
            + str(tool_calls)
        )
        response, backend = self.model.complete(prompt)
        if not response:
            response = (
                "Likely root cause: a recent change introduced a regression in the affected service. "
                "Evidence suggests the issue is consistent with a deploy-driven failure pattern. "
                "Recommended action: verify the newest release, inspect database or gateway health, and confirm the error budget before rollback or escalation."
            )
            backend = "offline"
        self.store.trace(run_id, "completion", {"model_backend": backend, "response": response})

        memory_text = f"namespace={namespace}; incident={sanitized}; summary={response[:500]}"
        self.store.remember(namespace, memory_text, importance=0.8)

        recommendations = self._recommendations(sanitized, evidence)
        confidence = self._infer_confidence(evidence, tool_calls)
        observability = {
            "security_gate": "passed",
            "retrieval_hits": len(evidence),
            "tool_count": len(tool_calls),
            "namespace": namespace,
            "model_backend": backend,
            "memory_count": len(self.store.memories(namespace, limit=10)),
        }

        result = {
            "run_id": run_id,
            "summary": response,
            "evidence": evidence,
            "tools": tool_calls,
            "trace": self.store.trace_for(run_id),
            "allowed": True,
            "model_backend": backend,
            "confidence": confidence,
            "recommendations": recommendations,
            "observability": observability,
        }
        return result
