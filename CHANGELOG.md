# Changelog

## 0.3.0 - 2026-09-20

### Added

- OpenTelemetry HTTP spans with trace IDs, live SSE event streams, and model attempt telemetry.
- Priority model routing with retry budgets, timeouts, circuit breakers, fallback providers, and SSRF host validation.
- 60-task evaluation benchmark with accuracy, hallucination, success, category, and p50/p95 latency reporting.
- Authenticated propose/approve/execute workflow for human-in-the-loop action control.
- Cloud VM deployment guide and local-first routing ADR.
- Deterministic replay, checkpointable trace stages, decaying and deduplicated memory, citation-bearing retrieval, and poisoned-document filtering.
- Structured facts, inferences, unknowns, counterfactuals, and blast-radius fields in decision graphs.
- Rate limiting, output egress redaction, private-network SSRF checks, and internal agent-stage telemetry.

## 0.2.0 - 2026-09-20

### Added

- Production service container with readiness and Prometheus-compatible metrics.
- Operator dashboard with guarded investigation workflow.
- SQLite WAL mode, busy timeout, and synchronized persistence for concurrent requests.
- Docker and Compose deployment with an optional Ollama model service.
- CI across supported Python versions, package wheel builds, security policy, and contributor guide.
- Evidence-to-decision graph with ranked hypotheses, citations, blast radius, counterfactuals, reversible actions, and human approval policy.
- Dedicated decision graph API resource at `/api/runs/{run_id}/decision`.
- Concurrent stress tests and API contract tests.

### Safety

- Unknown incidents now remain low-confidence when retrieval returns no supporting evidence, even if a fallback health probe runs.
- Mutating actions remain approval-required and are never executed by the default runtime.
