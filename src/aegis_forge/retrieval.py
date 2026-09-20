from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    text: str
    source: str = "runbook"
    version: str = "1"
    confidence: float = 1.0
    trusted: bool = True


class SemanticEncoder(Protocol):
    def encode(self, text: str) -> list[float]: ...


DEFAULT_CORPUS = [
    Document("rb-001", "Elevated 5xx responses", "Check deploys and error budget. Compare gateway and application logs. Roll back the newest release only after confirming the regression. Escalate to service owner if errors persist for 10 minutes."),
    Document("rb-002", "Database connection exhaustion", "Inspect connection pool saturation and database CPU. Reduce retry storms before increasing pool size. Fail closed for destructive operations. Capture a query sample and page the database owner."),
    Document("rb-003", "Credential exposure", "Revoke the exposed credential immediately, preserve evidence, rotate dependent secrets, and notify security. Never paste credentials into tickets, chat, or model prompts."),
    Document("arch-001", "Aegis architecture", "Aegis uses policy checks, evidence retrieval, bounded read-only tools, local model reasoning, durable memory, and an append-only trace for every run."),
]


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", text.lower())}


class Retriever:
    def __init__(self, documents: list[Document] | None = None, encoder: SemanticEncoder | None = None):
        self.documents = documents or DEFAULT_CORPUS
        self.encoder = encoder

    def search(self, query: str, limit: int = 3) -> list[dict]:
        return self.search_hybrid(query, limit=limit)

    def search_hybrid(self, query: str, limit: int = 3, lexical_weight: float = 0.7) -> list[dict]:
        query_tokens = _tokens(query)
        query_vector = self.encoder.encode(query) if self.encoder else None
        scored = []
        for document in self.documents:
            if not document.trusted or re.search(r"ignore .*instructions|reveal .*secret|system prompt", document.text, re.IGNORECASE):
                continue
            doc_tokens = _tokens(document.title + " " + document.text)
            overlap = len(query_tokens & doc_tokens)
            lexical = overlap / math.sqrt(max(len(query_tokens) * len(doc_tokens), 1))
            title_boost = 0.15 if query_tokens & _tokens(document.title) else 0.0
            semantic = _cosine(query_vector, self.encoder.encode(document.text)) if query_vector and self.encoder else 0.0
            score = lexical_weight * (lexical + title_boost) + (1.0 - lexical_weight) * semantic
            if overlap:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [{"id": doc.doc_id, "title": doc.title, "text": doc.text, "source": doc.source, "version": doc.version, "confidence": doc.confidence, "score": round(score, 4), "retrieval_mode": "hybrid" if self.encoder else "lexical", "citation": f"{doc.source}:{doc.doc_id}@{doc.version}"} for score, doc in scored[:limit]]


def _cosine(left: list[float] | None, right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0
