from __future__ import annotations

import argparse
import json

from aegis_forge.agent import IncidentAgent
from aegis_forge.config import settings
from aegis_forge.evaluation import evaluate_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Aegis Forge: local-first incident orchestration")
    parser.add_argument("incident", nargs="?", help="Operational incident text to investigate")
    parser.add_argument("--namespace", default="default", help="Isolation namespace for memory and traces")
    parser.add_argument("--eval", action="store_true", help="Run the built-in evaluation suite")
    args = parser.parse_args()

    if args.eval:
        result = evaluate_suite()
        print(json.dumps(result, indent=2))
        return

    if not args.incident:
        parser.error("An incident description is required unless --eval is used.")

    agent = IncidentAgent(storage_path=settings.db_path)
    result = agent.investigate(args.incident, namespace=args.namespace)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
