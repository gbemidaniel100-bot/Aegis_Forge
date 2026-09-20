from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from aegis_forge.agent import IncidentAgent
from aegis_forge.approval import ApprovalWorkflow
from aegis_forge.config import Settings, settings
from aegis_forge.model import LocalModel
from aegis_forge.observability import Metrics, RateLimiter
from aegis_forge.routing import ModelCandidate, ModelRouter, validate_model_url


@dataclass
class ServiceContainer:
    settings: Settings
    agent: IncidentAgent
    metrics: Metrics
    approvals: ApprovalWorkflow
    limiter: RateLimiter

    @classmethod
    def create(cls, configured: Settings = settings) -> ServiceContainer:
        configured.ensure_data_dir()
        candidates = [ModelCandidate(configured.model, LocalModel(validate_model_url(configured.ollama_url), configured.model), 0)]
        if configured.model_fallback:
            candidates.append(ModelCandidate(configured.model_fallback, LocalModel(configured.ollama_url, configured.model_fallback), 1))
        agent = IncidentAgent(storage_path=configured.db_path, model=ModelRouter(candidates))
        return cls(configured, agent, Metrics(), ApprovalWorkflow(agent.store), RateLimiter())

    def readiness(self) -> dict[str, object]:
        try:
            self.agent.store.connection.execute("SELECT 1").fetchone()
            return {"status": "ready", "database": "ok", "model": self.settings.model}
        except sqlite3.Error as exc:
            return {"status": "not_ready", "database": "error", "detail": type(exc).__name__}
