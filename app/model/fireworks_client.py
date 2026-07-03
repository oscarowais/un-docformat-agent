"""Fireworks AI client — STUB until hackathon credits land (Day 2, Jul 7).

DO NOT wire real calls here yet. Per the milestone plan, model integration
waits for (a) Fireworks credits to be live and (b) the launch-day model list.

Planned Day 3 use: `rewrite_to_comply(text, findings)` sends the raw text
plus the rules engine's structured findings and asks the model to return a
corrected draft + change log. The interface below is stable so the rest of
the app can already code against it.
"""

from __future__ import annotations

import os


class ModelNotConfigured(RuntimeError):
    """Raised when Fireworks credentials/model are not configured yet."""


class FireworksClient:
    """Thin wrapper around the Fireworks chat-completions API.

    Reads FIREWORKS_API_KEY and FIREWORKS_MODEL from the environment
    (populate via .env — see .env.example).
    """

    def __init__(self) -> None:
        self.api_key = os.environ.get("FIREWORKS_API_KEY", "")
        self.model = os.environ.get("FIREWORKS_MODEL", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def rewrite_to_comply(self, text: str, findings: list[dict]) -> dict:
        """Return {"rewritten": str, "change_log": list[str]}.

        TODO(Day 3): implement with the Fireworks SDK once credits are live.
        Prompt plan: system prompt = condensed Section 5 rule set; user turn =
        original text + JSON findings; require the model to fix ONLY flagged
        issues and emit a change-log entry per fix.
        """
        if not self.is_configured:
            raise ModelNotConfigured(
                "Fireworks is not configured yet. Set FIREWORKS_API_KEY and "
                "FIREWORKS_MODEL in .env (hackathon credits land Day 2).")
        raise NotImplementedError("Model call lands on Day 3 — see TODO above.")

    def answer_question(self, question: str, context: str) -> str:
        """RAG-style Q&A over the compiled document. TODO(Day 4)."""
        if not self.is_configured:
            raise ModelNotConfigured(
                "Fireworks is not configured yet — see .env.example.")
        raise NotImplementedError("Q&A lands on Day 4.")
