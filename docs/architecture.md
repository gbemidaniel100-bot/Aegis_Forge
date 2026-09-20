# Architecture

Aegis Forge is organized around explicit boundaries rather than a single prompt function.

```mermaid
flowchart LR
  HTTP[FastAPI / CLI] --> Guard[Security gate]
  Guard --> Retrieve[Runbook retriever]
  Retrieve --> Dense[Optional local embeddings]
  Retrieve --> Sparse[Lexical retrieval]
  Dense --> Fuse[Hybrid fusion + rerank]
  Sparse --> Fuse
  Fuse --> Plan[Bounded tool planner]
  Plan --> Tools[Read-only tool registry]
  Retrieve --> Model[Ollama or offline synthesizer]
  Tools --> Model[Structured model router]
  Memory[(SQLite memory)] --> Model
  Model --> Decision[Evidence-to-decision graph]
  Decision --> Trace[(Append-only trace)]
  Trace --> Metrics[Metrics and dashboard]
```

## Runtime guarantees

- Inputs are normalized, bounded, namespace-validated, and inspected for injection signals.
- Tools are selected from a fixed allowlist and return deterministic simulated evidence.
- The model is advisory; destructive actions are not exposed by the runtime.
- Ollama failure degrades to a deterministic offline response.
- SQLite uses WAL mode and a busy timeout for concurrent local API requests.
- Every request and investigation produces observable counters and a run trace.
- Every investigation produces a decision artifact with citations, alternatives, counterfactuals, reversible actions, and an explicit approval boundary.
