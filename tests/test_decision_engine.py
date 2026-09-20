import tempfile
from pathlib import Path

from aegis_forge.agent import IncidentAgent
from aegis_forge.decision import DecisionEngine


def test_decision_graph_contains_citations_and_reversible_actions():
    result = IncidentAgent(storage_path=str(Path(tempfile.mkdtemp()) / "decision.db")).investigate(
        "Database connections are exhausted and retries are increasing in payments API",
        namespace="decision-test",
    )
    graph = result["decision_graph"]
    assert graph["primary_hypothesis"]["confidence"] in {"low", "medium", "high"}
    assert graph["primary_hypothesis"]["evidence_ids"]
    assert graph["actions"]
    assert all(action["reversible"] for action in graph["actions"])
    assert graph["counterfactuals"]
    assert graph["blast_radius"]["service"]


def test_decision_engine_never_recommends_unapproved_mutation():
    graph = DecisionEngine().build(
        "A credential was exposed in a log",
        evidence=[],
        tools=[],
    )
    assert all(action["risk"] in {"read-only", "approval-required"} for action in graph["actions"])
    assert all("delete" not in action["title"].lower() for action in graph["actions"])
