"""Agent pipeline: rules check -> deterministic autofix -> model fix -> report.

This is the full processing loop the product runs:

    1. Deterministic autofix resolves every mechanical violation (no model).
    2. The rules engine re-checks; anything left needs editorial judgement.
    3. If a model is configured, Fireworks (Gemma on AMD Instinct) fixes
       ONLY the remaining violations and reports its own change log.
    4. A final rules pass verifies the result.

Every step is optional-degradable: with no model configured the pipeline
still produces the autofixed document — the demo works without credits.
"""

from __future__ import annotations

from app.autofix import autofix
from app.ingest import load_text
from app.model import FireworksClient, ModelNotConfigured
from app.report import sort_findings
from app.rules.engine import run_checks, summarize


def process(text: str, use_model: bool = True,
            client: FireworksClient | None = None) -> dict:
    """Run the full pipeline over raw text. Returns a JSON-friendly dict:

    {
      "text":          final document text,
      "autofix_log":   [str] deterministic fixes applied,
      "model_log":     [str] model fixes applied ([] if model unused),
      "model_used":    bool,
      "model_error":   str | None,
      "summary":       final rules summary (errors/warnings/info/compliant),
      "findings":      final findings (dicts, sorted),
    }
    """
    client = client or FireworksClient()

    # 1. deterministic pass
    fixed, autofix_log = autofix(text)

    # 2. what remains needs judgement
    remaining = [f for f in run_checks(load_text(fixed))
                 if f.severity.value != "info"]

    model_log: list[str] = []
    model_used = False
    model_error: str | None = None

    # 3. model pass — only if something remains and a model is available
    if use_model and remaining and client.is_configured:
        try:
            result = client.rewrite_to_comply(
                fixed, [f.to_dict() for f in remaining])
            candidate = result["rewritten"].strip()
            if candidate:
                fixed = candidate
                model_log = result["change_log"]
                model_used = True
        except (ModelNotConfigured, ValueError, OSError) as e:
            # Degrade gracefully: keep the autofixed text, surface the error.
            model_error = str(e)

    # 4. final verification pass
    final = run_checks(load_text(fixed))
    return {
        "text": fixed,
        "autofix_log": autofix_log,
        "model_log": model_log,
        "model_used": model_used,
        "model_error": model_error,
        "summary": summarize(final),
        "findings": [f.to_dict() for f in sort_findings(final)],
    }
