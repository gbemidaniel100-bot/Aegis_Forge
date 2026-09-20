from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionEngine:
    """Turn observed signals into an explainable, policy-bounded decision graph."""

    def _hypothesis(self, incident: str, evidence: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        signal = incident.lower()
        if "credential" in signal or "token" in signal or "secret" in signal:
            title = "Credential exposure is the dominant failure mode"
            rationale = "The incident contains a credential exposure signal and the response must prioritize containment and rotation."
        elif "database" in signal or "connection" in signal or "retry" in signal:
            title = "Connection saturation or retry amplification is the dominant failure mode"
            rationale = "The incident contains resource exhaustion signals that are consistent with pool saturation and retry storms."
        elif "5xx" in signal or "deploy" in signal or "release" in signal:
            title = "A recent release is the dominant regression candidate"
            rationale = "The incident connects elevated server errors to a recent change, making deploy comparison the highest-value next check."
        else:
            title = "The primary cause is not yet discriminated"
            rationale = "The available signal is insufficient to rank a specific failure mode without more telemetry."
        confidence = "high" if len(evidence) >= 2 and tools else "medium" if evidence else "low"
        return {
            "title": title,
            "rationale": rationale,
            "confidence": confidence,
            "evidence_ids": [item["id"] for item in evidence],
            "tool_names": [item["name"] for item in tools],
        }

    def _actions(self, incident: str) -> list[dict[str, Any]]:
        signal = incident.lower()
        actions: list[dict[str, Any]] = []
        if "credential" in signal or "token" in signal or "secret" in signal:
            actions.append({"title": "Revoke the exposed credential", "risk": "approval-required", "reversible": True, "owner": "security"})
            actions.append({"title": "Rotate dependent secrets", "risk": "approval-required", "reversible": True, "owner": "service-owner"})
            actions.append({"title": "Preserve logs and access evidence", "risk": "read-only", "reversible": True, "owner": "security"})
        elif "database" in signal or "connection" in signal:
            actions.append({"title": "Inspect pool saturation and retry rate", "risk": "read-only", "reversible": True, "owner": "database-owner"})
            actions.append({"title": "Reduce retry amplification before resizing the pool", "risk": "approval-required", "reversible": True, "owner": "service-owner"})
            actions.append({"title": "Capture a bounded query sample", "risk": "read-only", "reversible": True, "owner": "database-owner"})
        elif "5xx" in signal or "deploy" in signal:
            actions.append({"title": "Compare the newest release with the error budget", "risk": "read-only", "reversible": True, "owner": "release-owner"})
            actions.append({"title": "Prepare rollback for human approval", "risk": "approval-required", "reversible": True, "owner": "release-owner"})
        else:
            actions.append({"title": "Collect owner-confirmed telemetry", "risk": "read-only", "reversible": True, "owner": "on-call"})
        return actions

    def _counterfactuals(self, incident: str) -> list[dict[str, str]]:
        signal = incident.lower()
        if "database" in signal or "connection" in signal:
            return [
                {"question": "What would falsify pool saturation?", "check": "Healthy pool utilization with failures isolated to one dependency."},
                {"question": "What would make resizing unsafe?", "check": "Database CPU or lock wait saturation is already elevated."},
            ]
        if "credential" in signal or "token" in signal:
            return [{"question": "What would lower exposure confidence?", "check": "The value is a non-secret fixture and access logs show no external reads."}]
        return [{"question": "What would falsify a release regression?", "check": "The same error signature predates the release or appears in an unchanged version."}]

    def build(self, incident: str, evidence: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        signal = incident.lower()
        service = "payments-api" if "payment" in signal else "unknown-service"
        if "database" in signal or "connection" in signal:
            dependency = "ledger-db"
        elif "credential" in signal or "token" in signal:
            dependency = "identity-and-secrets"
        else:
            dependency = "gateway-and-application"
        hypothesis = self._hypothesis(incident, evidence, tools)
        return {
            "facts": [{"statement": f"Observed incident signal: {incident}", "source": "request"}],
            "inferences": [hypothesis["rationale"]],
            "unknowns": ["Blast radius is unconfirmed until live telemetry is checked."],
            "primary_hypothesis": hypothesis,
            "alternatives": [
                "Upstream dependency degradation",
                "Configuration or capacity mismatch",
                "Operator or deploy-induced regression",
            ],
            "actions": self._actions(incident),
            "counterfactuals": self._counterfactuals(incident),
            "blast_radius": {
                "service": service,
                "dependency": dependency,
                "scope": "unconfirmed; validate against telemetry before broad remediation",
            },
            "policy": {
                "mutations_executed": False,
                "human_approval_required": True,
                "evidence_bound": True,
            },
        }
