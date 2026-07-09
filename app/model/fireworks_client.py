"""Fireworks AI client — OpenAI-compatible chat completions on AMD Instinct.

Implemented mock-first: the HTTP transport is injectable, so the whole
pipeline is testable without credentials or network access. When the
hackathon/ADP credits land, set FIREWORKS_API_KEY and FIREWORKS_MODEL in
.env and the same code path goes live — no changes needed.

Uses stdlib urllib (no extra dependency) against the OpenAI-compatible
endpoint: POST https://api.fireworks.ai/inference/v1/chat/completions
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

# Base URL is configurable so the same client can hit any OpenAI-compatible
# endpoint (e.g. local Ollama at http://localhost:11434/v1 for dev testing).
# Production/demo target remains Fireworks AI on AMD Instinct.
DEFAULT_BASE_URL = "https://api.fireworks.ai/inference/v1"


def _api_url() -> str:
    base = os.environ.get("FIREWORKS_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    return f"{base}/chat/completions"

# Condensed Section 5 rule set — the model's editorial ground truth.
UN_RULES_SUMMARY = """\
UN DGACM formatting rules for Secretariat reports:
- Max 8,500 words including footnotes and headings.
- Headings: bold, sentence case (capital only on first word and proper nouns).
- Body paragraphs numbered consecutively (1., 2., 3., ...); citations use
  paragraph numbers, never page numbers.
- Sub-listings: (a), (b), ...; nested items (i), (ii), ... indented.
- Abbreviations spelled out in full on first occurrence, short form after.
- Never abbreviate: United Nations, General Assembly, Security Council,
  Secretary-General, Member States, document titles.
- Country names per UNTERM (e.g. "Viet Nam", "Republic of Korea",
  "Russian Federation", "Syrian Arab Republic").
- Spelling: Concise Oxford first-listed form ("programme", "judgement");
  -ize preferred over -ise.
- Quotations in double quotation marks. Footnotes only, never endnotes.
- Numbers under 10 in words; ordinals first-ninety-ninth in words.
- Currency symbols ($, €, SwF); country prefix for non-US dollars (Can$50).
"""

_REWRITE_SYSTEM = f"""You are a senior editor at the United Nations enforcing
DGACM formatting rules for Secretariat reports.

{UN_RULES_SUMMARY}

You will receive a draft document and a JSON list of remaining rule
violations that deterministic checks could not fix automatically.

Requirements:
1. Fix ONLY the listed violations. Do not rewrite, shorten, embellish or
   otherwise alter content that is not flagged.
2. Preserve the meaning, facts, figures and citations of the original.
3. Return STRICT JSON, nothing else, in exactly this shape:
   {{"rewritten": "<full corrected document text>",
     "change_log": ["<one entry per fix, format: 'Rule: what changed'>"]}}
"""

_QA_SYSTEM = """You answer questions about a compiled UN-style document.
Answer only from the provided document content. If the answer is not in the
document, say so. Cite paragraph numbers where possible. Be concise."""


class ModelNotConfigured(RuntimeError):
    """Raised when Fireworks credentials/model are not configured yet."""


class FireworksClient:
    """Thin client for Fireworks chat completions.

    `transport` is a callable(payload: dict) -> dict (the parsed JSON
    response). Defaults to a real HTTPS call; tests inject a fake.
    """

    def __init__(self, transport=None) -> None:
        self.api_key = os.environ.get("FIREWORKS_API_KEY", "")
        self.model = os.environ.get("FIREWORKS_MODEL", "")
        self._transport = transport or self._http_transport

    @property
    def is_configured(self) -> bool:
        # A custom transport (mock) counts as configured for pipeline tests.
        return bool(self.api_key and self.model) or \
            self._transport != self._http_transport

    # ------------------------------------------------------------------ API

    def rewrite_to_comply(self, text: str, findings: list[dict]) -> dict:
        """Ask the model to fix the listed violations only.

        Returns {"rewritten": str, "change_log": list[str]}.
        Raises ModelNotConfigured / ValueError on unusable responses.
        """
        self._require_configured()
        user = (f"DRAFT DOCUMENT:\n---\n{text}\n---\n\n"
                f"REMAINING VIOLATIONS (JSON):\n"
                f"{json.dumps(findings, ensure_ascii=False, indent=1)}")
        content = self._chat([
            {"role": "system", "content": _REWRITE_SYSTEM},
            {"role": "user", "content": user},
        ], temperature=0.1)

        data = _extract_json(content)
        if not isinstance(data, dict) or "rewritten" not in data:
            raise ValueError(f"Model returned unusable response: {content[:200]}")
        data.setdefault("change_log", [])
        return {"rewritten": str(data["rewritten"]),
                "change_log": [str(e) for e in data["change_log"]]}

    def answer_question(self, question: str, context: str) -> str:
        """Q&A over the compiled document (context stuffing — the docs this
        agent targets fit comfortably in a modern context window)."""
        self._require_configured()
        user = f"DOCUMENT:\n---\n{context}\n---\n\nQUESTION: {question}"
        return self._chat([
            {"role": "system", "content": _QA_SYSTEM},
            {"role": "user", "content": user},
        ], temperature=0.2).strip()

    # ------------------------------------------------------------ internals

    def _require_configured(self) -> None:
        if not self.is_configured:
            raise ModelNotConfigured(
                "Fireworks is not configured. Set FIREWORKS_API_KEY and "
                "FIREWORKS_MODEL in .env (see .env.example).")

    def _chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        payload = {
            "model": self.model or "mock-model",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8192,
        }
        response = self._transport(payload)
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Unexpected API response shape: {e}") from e

    def _http_transport(self, payload: dict) -> dict:
        req = urllib.request.Request(
            _api_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            # Surface the API's own error body — it names the real cause
            # (bad model id, wrong endpoint, quota, ...), not just the code.
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            raise OSError(f"HTTP {e.code} from {_api_url()}: {body}") from e


def _extract_json(content: str):
    """Parse model output into JSON, tolerating code fences and prose."""
    content = content.strip()
    # Strip markdown code fences if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, re.DOTALL)
    if fence:
        content = fence.group(1)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost {...} span.
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None
