from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from aegis_forge.evaluation import evaluate_suite
from aegis_forge.service import ServiceContainer
from aegis_forge.web import dashboard


class InvestigationRequest(BaseModel):
    incident: str = Field(..., min_length=1, max_length=12000)
    namespace: str = Field(default="default", min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")

    @field_validator("incident")
    @classmethod
    def normalize_incident(cls, value: str) -> str:
        return " ".join(value.split())


def create_app(container: ServiceContainer | None = None) -> FastAPI:
    service = container or ServiceContainer.create()
    app = FastAPI(title="Aegis Forge", version="0.2.0", description="Guarded local AI incident operations")
    app.state.service = service

    @app.middleware("http")
    async def observe_requests(request: Request, call_next):
        with service.metrics.observe(request.url.path):
            response = await call_next(request)
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "generated")
        return response

    @app.get("/", include_in_schema=False)
    def home():
        return dashboard()

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "aegis-forge", "model": service.settings.model}

    @app.get("/ready")
    def ready() -> dict[str, object]:
        status = service.readiness()
        if status["status"] != "ready":
            raise HTTPException(status_code=503, detail=status)
        return status

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        return service.metrics.prometheus()

    @app.get("/metrics/json")
    def metrics_json() -> dict[str, object]:
        return service.metrics.snapshot()

    @app.post("/api/investigate")
    def investigate(request: InvestigationRequest) -> dict[str, Any]:
        result = service.agent.investigate(request.incident, namespace=request.namespace)
        if not result.get("allowed", True):
            raise HTTPException(status_code=400, detail={"message": "Prompt rejected by security guard", "reasons": result.get("reasons", [])})
        return result

    @app.get("/api/runs/{run_id}/trace")
    def trace_for_run(run_id: str) -> dict[str, Any]:
        events = service.agent.store.trace_for(run_id)
        if not events:
            raise HTTPException(status_code=404, detail="run not found")
        return {"run_id": run_id, "trace": events}

    @app.post("/api/evaluate")
    def evaluate() -> dict[str, Any]:
        return evaluate_suite(service.agent.store)

    return app


app = create_app()
