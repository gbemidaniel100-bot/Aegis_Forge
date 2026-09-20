# Changelog

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
