# Evidence-to-Decision Graph

Aegis Forge does not treat a model paragraph as the end product. Every allowed investigation builds a machine-readable decision graph.

## Graph contract

- `primary_hypothesis`: the leading explanation, confidence, cited runbook IDs, and tool names.
- `alternatives`: competing explanations that keep the operator from anchoring too early.
- `actions`: concrete next steps with owner, risk, and reversibility.
- `counterfactuals`: checks that would falsify the leading hypothesis or make an action unsafe.
- `blast_radius`: a deliberately conservative service and dependency view.
- `policy`: explicit proof that no mutation was executed and approval is required.

## Why this matters

This creates a clean boundary between model synthesis and operational action. A model may help interpret evidence, but it cannot silently turn interpretation into remediation. Operators can inspect the citations, challenge the hypothesis, and hand the graph to an approval workflow.

The graph is stored as a trace event and is also available through:

```text
GET /api/runs/{run_id}/decision
```

A future production adapter can replace the deterministic decision rules with a calibrated classifier or structured model output while preserving the contract and safety policy.
