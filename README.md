# Aegis Forge

**A local-first AI systems engineering portfolio project for incident operations.**

Aegis Forge is an auditable incident command workbench, not a chat wrapper. Give it an operational signal and it coordinates a guarded investigation: it retrieves runbook evidence, plans bounded read-only tool calls, uses an Ollama model when available, falls back to a deterministic offline analyst, persists useful memory, and returns a trace showing what happened.

![Aegis Forge dashboard](docs/dashboard.svg)

## Why this is interesting

- **Agent orchestration:** a stateful investigation loop with explicit policy, retrieval, planning, tools, synthesis, memory, and evaluation stages.
- **Model orchestration:** Ollama is the local reasoning provider, with a tested offline path so the demo never depends on a cloud API or a running model.
- **RAG:** a tiny inspectable runbook corpus with token-scored retrieval and source IDs in every result. The retriever is intentionally replaceable with embeddings later.
- **Tool use:** an allowlisted registry of deterministic adapters. Every adapter is read-only, risk-labelled, bounded by `AEGIS_MAX_TOOL_CALLS`, and recorded.
- **Memory:** SQLite stores namespace-scoped incident learnings with importance ordering.
- **Observability:** every run emits append-only events for security, retrieval, tool calls, and completion; traces are available from the API.
- **Evaluation:** three repeatable incident cases measure keyword task quality and grounding, with scores stored in SQLite.
- **Security:** input length limits, namespace validation, prompt-injection checks, secret/number redaction, no arbitrary tool execution, and a human-approval boundary for destructive actions.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn aegis_forge.api:app --reload
```

Open `http://127.0.0.1:8000`. The dashboard works immediately in offline mode. For local model reasoning, install [Ollama](https://ollama.com), then run:

```bash
ollama pull llama3.2:3b
```

Configuration is environment-based:

```bash
cp .env.example .env
export AEGIS_MODEL=llama3.2:3b
```

The application does not load `.env` automatically; exporting variables keeps deployment behavior explicit.

## CLI and API

```bash
aegis "Payments API has elevated 5xx responses after the latest deploy"
aegis --eval
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/investigate \
	-H 'content-type: application/json' \
	-d '{"incident":"Database connections are exhausted and retries are increasing","namespace":"demo"}'
```

Important endpoints are `POST /api/investigate`, `GET /api/runs/{run_id}/trace`, and `POST /api/evaluate`.

## Architecture

```text
request
	-> security gate + redaction
	-> runbook retriever + namespace memory
	-> bounded tool planner
	-> read-only adapters
	-> Ollama / offline synthesizer
	-> durable memory + append-only trace
	-> typed API response + operator dashboard
```

The code is deliberately small enough to inspect in one sitting. `IncidentAgent` owns the workflow; `Retriever`, `ToolRegistry`, `LocalModel`, and `Store` are replaceable boundaries. A production adapter can implement the same tool contract without changing the agent policy.

## Verification

```bash
python -m unittest discover -s tests -v
python -m compileall -q src
pytest -q                 # after installing [dev]
ruff check .              # after installing [dev]
```

The tests verify injection blocking before tool execution, evidence retrieval, bounded tool fan-out, memory and trace persistence, relevance ranking, and redaction. The local model path is intentionally tested through a fake model, while the Ollama adapter degrades cleanly when the daemon is absent.

## Production hardening roadmap

1. Replace the in-memory corpus with a versioned vector index and document ACL filtering.
2. Add OIDC identity, per-tenant encryption keys, rate limits, and a real secrets manager.
3. Add OpenTelemetry spans and Prometheus counters around model latency, retrieval recall, and tool failures.
4. Put destructive remediation behind a separate approval service and signed action tokens.
5. Expand evals with golden evidence citations, injection suites, cost/latency budgets, and regression gates in CI.

## License

MIT
