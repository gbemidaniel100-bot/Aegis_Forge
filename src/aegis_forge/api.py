from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from aegis_forge.agent import IncidentAgent
from aegis_forge.config import settings
from aegis_forge.db import Store
from aegis_forge.evaluation import evaluate_suite

app = FastAPI(title="Aegis Forge", version="0.1.0")


class InvestigationRequest(BaseModel):
    incident: str = Field(..., min_length=1, max_length=12000)
    namespace: str = "default"


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "aegis-forge", "model": settings.model}


@app.post("/api/investigate")
def investigate(request: InvestigationRequest) -> dict[str, Any]:
    agent = IncidentAgent(storage_path=settings.db_path)
    result = agent.investigate(request.incident, namespace=request.namespace)
    if not result.get("allowed", True):
        raise HTTPException(status_code=400, detail={"message": "Prompt rejected by security guard", "reasons": result.get("reasons", [])})
    return result


@app.get("/api/runs/{run_id}/trace")
def trace_for_run(run_id: str) -> dict[str, Any]:
    store = Store(settings.db_path)
    events = store.trace_for(run_id)
    if not events:
        raise HTTPException(status_code=404, detail="run not found")
    return {"run_id": run_id, "trace": events}


@app.post("/api/evaluate")
def evaluate() -> dict[str, Any]:
    return evaluate_suite()
