import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from aegis_forge.agent import IncidentAgent


def test_concurrent_investigations_keep_distinct_traces():
    with tempfile.TemporaryDirectory() as directory:
        agent = IncidentAgent(storage_path=str(Path(directory) / "stress.db"))
        incidents = [
            "Database connections are exhausted and retries are increasing",
            "Gateway has elevated 5xx errors after the latest deploy",
            "A token was exposed and needs immediate rotation",
        ] * 4
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda incident: agent.investigate(incident, namespace="stress"), incidents))

        run_ids = {result["run_id"] for result in results}
        assert len(run_ids) == len(incidents)
        assert all(result["allowed"] for result in results)
        assert all(result["trace"] for result in results)
        memories = agent.store.memories("stress", limit=len(incidents))
        assert len(memories) == 3
        content = " ".join(memory["content"].lower() for memory in memories)
        assert all(signal in content for signal in ("database", "gateway", "token"))
