# Architecture

Aegis Forge is organized around explicit boundaries rather than a single prompt function.

```mermaid
flowchart LR
  HTTP[FastAPI / CLI] --> Guard[Security gate]
  Guard --> Retrieve[Runbook retriever]
  Retrieve --> Plan[Bounded tool planner]
  Plan --> Tools[Read-only tool registry]
  Retrieve --> Model[Ollama or offline synthesizer]
  Tools --> Model
  Memory[(SQLite memory)] --> Model
  Model --> Trace[(Append-only trace)]
  Trace --> Metrics[Metrics and dashboard]
```

## Runtime guarantees

- Inputs are normalized, bounded, namespace-validated, and inspected for injection signals.
- Tools are selected from a fixed allowlist and return deterministic simulated evidence.
- The model is advisory; destructive actions are not exposed by the runtime.
- Ollama failure degrades to a deterministic offline response.
- SQLite uses WAL mode and a busy timeout for concurrent local API requests.
- Every request and investigation produces observable counters and a run trace.
