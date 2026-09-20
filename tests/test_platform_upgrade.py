import tempfile
from pathlib import Path

import pytest

from aegis_forge.approval import ApprovalWorkflow
from aegis_forge.benchmark import task_matrix
from aegis_forge.db import Store
from aegis_forge.resilience import CircuitBreaker
from aegis_forge.routing import validate_model_url


def test_benchmark_has_sixty_tasks():
    assert len(task_matrix()) == 60


def test_ssrf_guard_blocks_metadata_endpoints():
    with pytest.raises(ValueError):
        validate_model_url("http://169.254.169.254/latest/meta-data")
    assert validate_model_url("http://localhost:11434") == "http://localhost:11434"


def test_circuit_breaker_opens_after_failures():
    breaker = CircuitBreaker(failure_threshold=2)
    breaker.failure()
    assert not breaker.open
    breaker.failure()
    assert breaker.open


def test_approval_requires_propose_and_approve():
    with tempfile.TemporaryDirectory() as directory:
        workflow = ApprovalWorkflow(Store(str(Path(directory) / "approval.db")))
        with pytest.raises(ValueError):
            workflow.execute("run-1", "missing")
        proposal = workflow.propose("run-1", {"title": "prepare rollback", "risk": "approval-required"})
        with pytest.raises(ValueError):
            workflow.execute("run-1", proposal["approval_id"])
        workflow.approve("run-1", proposal["approval_id"])
        result = workflow.execute("run-1", proposal["approval_id"])
        assert result["status"] == "simulated-execution"
