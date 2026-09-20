# Contributing

## Development

```bash
python -m venv .venv
source .venv/bin/activate
make install
make test
make lint
```

Keep changes focused, add behavior-level tests, and preserve the offline path. Ollama is optional for development and must never be required for CI.

## Pull requests

Describe the operational behavior changed, the security implications, and the verification commands. New tools must be allowlisted, read-only by default, bounded, and covered by an evaluation case.
