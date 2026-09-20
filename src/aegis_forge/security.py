from __future__ import annotations

import re
from dataclasses import dataclass

INJECTION_PATTERNS = (
    r"ignore (all|any|previous|prior) instructions",
    r"system prompt",
    r"reveal (your|the) (prompt|secrets?)",
    r"exfiltrat",
)


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    sanitized: str
    reasons: list[str]


def inspect_input(text: str) -> GuardResult:
    reasons = ["prompt_injection_signal" for pattern in INJECTION_PATTERNS if re.search(pattern, text, re.IGNORECASE)]
    if reasons:
        return GuardResult(False, "", reasons)
    sanitized = text.strip()[:12000]
    if not sanitized:
        return GuardResult(False, "", ["empty_request"])
    return GuardResult(True, sanitized, [])


def redact(text: str) -> str:
    text = re.sub(r"(?i)(api[_ -]?key|token|password)\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
    text = re.sub(r"\b(?:[A-Za-z]+\d{8,}[A-Za-z0-9]*|\d{12,})\b", "[REDACTED_NUMBER]", text)
    return text


def validate_output(text: str, maximum: int = 12000) -> str:
    """Bound model output and prevent obvious secret leakage at the egress boundary."""
    bounded = text.strip()[:maximum]
    if not bounded:
        return "No model response was available; use the evidence and runbook recommendations."
    return redact(bounded)
