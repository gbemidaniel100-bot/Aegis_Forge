from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    text: str
    source: str = "runbook"


DEFAULT_CORPUS = [
    Document("rb-001", "Elevated 5xx responses", "Check deploys and error budget. Compare gateway and application logs. Roll back the newest release only after confirming the regression. Escalate to service owner if errors persist for 10 minutes."),
    Document("rb-002", "Database connection exhaustion", "Inspect connection pool saturation and database CPU. Reduce retry storms before increasing pool size. Fail closed for destructive operations. Capture a query sample and page the database owner."),
    Document("rb-003", "Credential exposure", "Revoke the exposed credential immediately, preserve evidence, rotate dependent secrets, and notify security. Never paste credentials into tickets, chat, or model prompts."),
    Document("arch-001", "Aegis architecture", "Aegis uses policy checks, evidence retrieval, bounded read-only tools, local model reasoning, durable memory, and an append-only trace for every run."),
]


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", text.lower())}


class Retriever:
    def __init__(self, documents: list[Document] | None = None):
        self.documents = documents or DEFAULT_CORPUS

    def search(self, query: str, limit: int = 3) -> list[dict]:
        query_tokens = _tokens(query)
        scored = []
        for document in self.documents:
            doc_tokens = _tokens(document.title + " " + document.text)
            overlap = len(query_tokens & doc_tokens)
            score = overlap / math.sqrt(max(len(query_tokens) * len(doc_tokens), 1))
            if overlap:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [{"id": doc.doc_id, "title": doc.title, "text": doc.text, "source": doc.source, "score": round(score, 4)} for score, doc in scored[:limit]]
