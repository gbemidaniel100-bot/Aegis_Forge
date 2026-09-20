# ADR 001: Local-first model routing

- Status: Accepted
- Date: 2026-09-20

## Decision

Aegis Forge routes through ordered local Ollama candidates. Each candidate has a bounded retry budget, timeout, and circuit breaker. If all candidates fail, the system returns a deterministic offline response and records the provider attempts.

## Why

Operational investigation must remain useful during model-server outages. Keeping the routing contract inside the service also makes model comparison measurable without coupling the incident workflow to one vendor.

## Consequences

The offline response is intentionally conservative and evidence-bound. Production deployments can add authenticated providers behind the same `ModelCandidate` interface without changing tools, memory, or approval policy.
