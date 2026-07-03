"""Rules engine entry point — runs every registered check over a document.

Adding a rule = write a `check_*(doc) -> list[Finding]` function in a
checks_* module and register it in ALL_CHECKS. Order here is display order.
"""

from __future__ import annotations

from collections.abc import Callable

from app.document import DocumentModel
from app.rules.base import Finding, Severity
from app.rules import (checks_docx, checks_length, checks_structure,
                       checks_style, checks_terminology)

Check = Callable[[DocumentModel], list[Finding]]

ALL_CHECKS: list[Check] = [
    checks_length.check_word_count,
    checks_docx.check_font,
    checks_docx.check_page_setup,
    checks_docx.check_notes,
    checks_structure.check_headings,
    checks_structure.check_paragraph_numbering,
    checks_structure.check_sublistings,
    checks_terminology.check_abbreviations,
    checks_terminology.check_country_names,
    checks_style.check_spelling,
    checks_style.check_quotations,
    checks_style.check_numbers,
    checks_style.check_currency,
]


def run_checks(doc: DocumentModel,
               checks: list[Check] | None = None) -> list[Finding]:
    """Run all (or a subset of) checks and return combined findings."""
    findings: list[Finding] = []
    for check in (checks or ALL_CHECKS):
        findings.extend(check(doc))
    return findings


def summarize(findings: list[Finding]) -> dict:
    """Counts by severity + a simple compliance verdict for UI/JSON output."""
    counts = {s.value: 0 for s in Severity}
    for f in findings:
        counts[f.severity.value] += 1
    return {
        "errors": counts["error"],
        "warnings": counts["warning"],
        "info": counts["info"],
        "compliant": counts["error"] == 0 and counts["warning"] == 0,
    }
