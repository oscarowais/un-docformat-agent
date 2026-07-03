"""Render findings as terminal text or JSON (consumed by CLI, UI, and later
the model layer / change-log generator)."""

from __future__ import annotations

import json

from app.document import DocumentModel
from app.rules.base import Finding
from app.rules.engine import summarize

_SEV_MARK = {"error": "[ERROR]", "warning": "[WARN ]", "info": "[info ]"}
_SEV_ORDER = {"error": 0, "warning": 1, "info": 2}


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (_SEV_ORDER[f.severity.value],
                                           f.rule_id,
                                           f.paragraph_index or 0))


def to_json(doc: DocumentModel, findings: list[Finding]) -> str:
    payload = {
        "source": doc.source_path or "(pasted text)",
        "format": doc.source_format,
        "word_count": doc.word_count(),
        "summary": summarize(findings),
        "findings": [f.to_dict() for f in sort_findings(findings)],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def to_text(doc: DocumentModel, findings: list[Finding]) -> str:
    s = summarize(findings)
    lines = [
        "UN DocFormat Agent — compliance report",
        f"Source: {doc.source_path or '(pasted text)'}  "
        f"[{doc.source_format}, {doc.word_count():,} words]",
        f"Result: {s['errors']} error(s), {s['warnings']} warning(s), "
        f"{s['info']} info",
        "-" * 72,
    ]
    for f in sort_findings(findings):
        loc = f" (para {f.paragraph_index + 1})" if f.paragraph_index is not None else ""
        lines.append(f"{_SEV_MARK[f.severity.value]} {f.rule_id} "
                     f"{f.rule_name}{loc}")
        lines.append(f"        {f.message}")
        if f.suggestion:
            lines.append(f"        Fix: {f.suggestion}")
        if f.snippet:
            snippet = f.snippet.replace("\n", " ")
            lines.append(f"        Text: {snippet}")
    lines.append("-" * 72)
    lines.append("COMPLIANT" if s["compliant"]
                 else "NOT COMPLIANT — see findings above")
    return "\n".join(lines)
