from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from aegis_forge.benchmark import run_benchmark
from aegis_forge.evaluation import evaluate_suite
from aegis_forge.replay import replay_run
from aegis_forge.service import ServiceContainer
from aegis_forge.telemetry import tracer
from aegis_forge.web import dashboard


class InvestigationRequest(BaseModel):
    incident: str = Field(..., min_length=1, max_length=12000)
    namespace: str = Field(default="default", min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")

    @field_validator("incident")
    @classmethod
    def normalize_incident(cls, value: str) -> str:
        return " ".join(value.split())


class ApprovalRequest(BaseModel):
    run_id: str
    action: dict[str, Any]
    actor: str = "operator"
    reason: str = "incident response"


class ApprovalDecision(BaseModel):
    run_id: str
    approval_id: str
    actor: str = "operator"


def _authorize(service: ServiceContainer, token: str | None) -> None:
    if service.settings.api_token and token != service.settings.api_token:
        raise HTTPException(status_code=401, detail="invalid API token")


def create_app(container: ServiceContainer | None = None) -> FastAPI:
    service = container or ServiceContainer.create()
    app = FastAPI(title="Aegis Forge", version="0.5.0", description="Guarded local AI incident operations")
    app.state.service = service

    @app.middleware("http")
    async def observe_requests(request: Request, call_next):
        identity = request.client.host if request.client else "unknown"
        if not service.limiter.allow(identity):
            return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
        with tracer.start_as_current_span(f"HTTP {request.method} {request.url.path}") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.route", request.url.path)
            with service.metrics.observe(request.url.path):
                response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "generated")
        response.headers["X-Trace-ID"] = format(span.get_span_context().trace_id, "032x")
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
    def investigate(request: InvestigationRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        _authorize(service, authorization.removeprefix("Bearer ").strip() if authorization else None)
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

    @app.get("/api/runs/{run_id}/decision")
    def decision_for_run(run_id: str) -> dict[str, Any]:
        events = service.agent.store.trace_for(run_id)
        decision = next((event["payload"] for event in events if event["event"] == "decision_graph"), None)
        if decision is None:
            raise HTTPException(status_code=404, detail="decision graph not found")
        return {"run_id": run_id, "decision_graph": decision}

    @app.post("/api/runs/{run_id}/replay")
    def replay(run_id: str) -> dict[str, Any]:
        try:
            return replay_run(service.agent.store, run_id, service.agent)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: str):
        async def stream():
            sent = 0
            for _ in range(80):
                events = service.agent.store.trace_for(run_id)
                for event in events[sent:]:
                    yield f"event: {event['event']}\ndata: {json.dumps(event)}\n\n"
                sent = len(events)
                if sent and any(event["event"] in {"completion", "approval_proposed", "decision_graph"} for event in events):
                    break
                await asyncio.sleep(0.1)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.post("/api/approvals/propose")
    def propose_approval(request: ApprovalRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        _authorize(service, authorization.removeprefix("Bearer ").strip() if authorization else None)
        return service.approvals.propose(request.run_id, request.action, request.actor, request.reason)

    @app.post("/api/approvals/approve")
    def approve(request: ApprovalDecision, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        _authorize(service, authorization.removeprefix("Bearer ").strip() if authorization else None)
        return service.approvals.approve(request.run_id, request.approval_id, request.actor)

    @app.post("/api/approvals/execute")
    def execute(request: ApprovalDecision, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        _authorize(service, authorization.removeprefix("Bearer ").strip() if authorization else None)
        try:
            return service.approvals.execute(request.run_id, request.approval_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/evaluate")
    def evaluate() -> dict[str, Any]:
        return evaluate_suite(service.agent.store)

    @app.post("/api/benchmark")
    def benchmark() -> dict[str, Any]:
        return run_benchmark(service.agent, repetitions=20)

    return app


app = create_app()
