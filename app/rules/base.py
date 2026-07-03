"""Finding/severity primitives for the rules engine.

A Finding is deliberately model-friendly: on Day 3 the LLM fix step will
receive `to_dict()` output as structured context, so keep fields stable.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"        # violates a hard UN rule (e.g. word limit)
    WARNING = "warning"    # very likely a violation, minor heuristic risk
    INFO = "info"          # advisory / cannot be fully verified from source


@dataclass
class Finding:
    rule_id: str           # stable id, e.g. "UN-WORDCOUNT-001"
    rule_name: str         # human-readable rule name
    severity: Severity
    message: str           # what is wrong
    suggestion: str = ""   # how to fix it
    paragraph_index: int | None = None   # 0-based, None = document-level
    snippet: str = ""      # offending text excerpt for display/model context

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


def snippet_of(text: str, start: int, end: int, radius: int = 40) -> str:
    """Return a short excerpt around [start, end) for display."""
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    prefix = "…" if lo > 0 else ""
    suffix = "…" if hi < len(text) else ""
    return f"{prefix}{text[lo:hi]}{suffix}"
