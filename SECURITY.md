# Security Policy

Aegis Forge is designed as a local-first incident assistant. It deliberately exposes only simulated, read-only tools and treats model output as advisory.

## Reporting

Please report suspected vulnerabilities privately through GitHub Security Advisories rather than opening a public issue with exploit details.

## Deployment boundaries

Before production use, deploy behind authentication and network policy, use a managed database, add tenant-level authorization, and put any mutating remediation behind human approval and signed action tokens. Never put credentials in incident text, logs, prompts, or evaluation fixtures.
