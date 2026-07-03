"""Docx-only page setup & notes rules — skipped for plain-text sources.

UN rules covered here:
- Microsoft Word format, 10-point Times New Roman.
- US letter page size (8.5" x 11"), standard 1" margins.
- Footnotes only, never endnotes.

The docx loader (app/ingest/loaders.py) populates doc.metadata with the
fonts, sizes, page geometry and notes flags these checks consume.
"""

from __future__ import annotations

from app.document import DocumentModel
from app.rules.base import Finding, Severity

REQUIRED_FONT = "Times New Roman"
REQUIRED_SIZE_PT = 10.0
LETTER_W_IN, LETTER_H_IN = 8.5, 11.0
MARGIN_IN = 1.0
_TOL = 0.06  # inches — absorb EMU rounding


def _docx_only(doc: DocumentModel) -> bool:
    return doc.source_format == "docx"


def check_font(doc: DocumentModel) -> list[Finding]:
    if not _docx_only(doc):
        return [Finding(
            rule_id="UN-FMT-000",
            rule_name="Font & page setup",
            severity=Severity.INFO,
            message="Source is plain text — font/page-setup rules (10 pt "
                    "Times New Roman, US letter, 1\" margins) will be "
                    "applied when generating the Word output.",
        )]
    findings: list[Finding] = []
    fonts = {f for f in doc.metadata.get("fonts", set()) if f}
    sizes = {s for s in doc.metadata.get("font_sizes", set()) if s}

    bad_fonts = fonts - {REQUIRED_FONT}
    if bad_fonts:
        findings.append(Finding(
            rule_id="UN-FMT-001",
            rule_name="Font family",
            severity=Severity.ERROR,
            message=f"Non-compliant font(s) found: {', '.join(sorted(bad_fonts))}. "
                    f"Documents must use {REQUIRED_FONT}.",
            suggestion=f"Set all text to {REQUIRED_FONT}.",
        ))
    bad_sizes = {s for s in sizes if abs(s - REQUIRED_SIZE_PT) > 0.1}
    if bad_sizes:
        findings.append(Finding(
            rule_id="UN-FMT-002",
            rule_name="Font size",
            severity=Severity.ERROR,
            message=f"Non-compliant font size(s): "
                    f"{', '.join(str(s) for s in sorted(bad_sizes))} pt. "
                    f"Body text must be {REQUIRED_SIZE_PT:g} pt.",
            suggestion=f"Set body text to {REQUIRED_SIZE_PT:g} pt.",
        ))
    return findings


def check_page_setup(doc: DocumentModel) -> list[Finding]:
    if not _docx_only(doc):
        return []
    findings: list[Finding] = []
    w = doc.metadata.get("page_width_in")
    h = doc.metadata.get("page_height_in")
    if w and h and (abs(w - LETTER_W_IN) > _TOL or abs(h - LETTER_H_IN) > _TOL):
        findings.append(Finding(
            rule_id="UN-PAGE-001",
            rule_name="Page size",
            severity=Severity.ERROR,
            message=f"Page size is {w:.2f}\" x {h:.2f}\"; required size is "
                    f"US letter ({LETTER_W_IN}\" x {LETTER_H_IN}\").",
            suggestion="Set page size to US letter.",
        ))
    margins = doc.metadata.get("margins_in", {})
    bad = {k: v for k, v in margins.items() if abs(v - MARGIN_IN) > _TOL}
    if bad:
        desc = ", ".join(f"{k} {v:.2f}\"" for k, v in bad.items())
        findings.append(Finding(
            rule_id="UN-PAGE-002",
            rule_name="Margins",
            severity=Severity.WARNING,
            message=f"Margins deviate from the standard 1\": {desc}.",
            suggestion="Set all margins to 1\".",
        ))
    return findings


def check_notes(doc: DocumentModel) -> list[Finding]:
    if not _docx_only(doc):
        return []
    if doc.metadata.get("has_endnotes"):
        return [Finding(
            rule_id="UN-NOTE-001",
            rule_name="Footnotes only",
            severity=Severity.ERROR,
            message="Document contains endnotes; UN documents use footnotes "
                    "only, never endnotes.",
            suggestion="Convert all endnotes to footnotes.",
        )]
    return []
