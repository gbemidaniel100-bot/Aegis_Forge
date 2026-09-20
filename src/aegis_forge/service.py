from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from aegis_forge.agent import IncidentAgent
from aegis_forge.config import Settings, settings
from aegis_forge.observability import Metrics


@dataclass
class ServiceContainer:
    settings: Settings
    agent: IncidentAgent
    metrics: Metrics

    @classmethod
    def create(cls, configured: Settings = settings) -> ServiceContainer:
        configured.ensure_data_dir()
        return cls(configured, IncidentAgent(storage_path=configured.db_path), Metrics())

    def readiness(self) -> dict[str, object]:
        try:
            self.agent.store.connection.execute("SELECT 1").fetchone()
            return {"status": "ready", "database": "ok", "model": self.settings.model}
        except sqlite3.Error as exc:
            return {"status": "not_ready", "database": "error", "detail": type(exc).__name__}
