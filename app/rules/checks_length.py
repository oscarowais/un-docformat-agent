"""Length-limit rules.

UN rule (DGACM): reports originating in the Secretariat max 8,500 words;
reports not originating in the Secretariat max 10,700 words — including
footnotes, headings and hidden text. Waiver required to exceed.
"""

from __future__ import annotations

from app.document import DocumentModel
from app.rules.base import Finding, Severity

SECRETARIAT_LIMIT = 8_500
NON_SECRETARIAT_LIMIT = 10_700


def check_word_count(doc: DocumentModel) -> list[Finding]:
    count = doc.word_count()
    # Demo targets a Secretariat report; the stricter limit applies.
    limit = SECRETARIAT_LIMIT
    findings: list[Finding] = []

    if count > limit:
        findings.append(Finding(
            rule_id="UN-LEN-001",
            rule_name="Word-count limit (Secretariat report)",
            severity=Severity.ERROR,
            message=(f"Document is {count:,} words; Secretariat reports are "
                     f"limited to {limit:,} words (incl. footnotes and "
                     f"headings). Exceeds limit by {count - limit:,} words."),
            suggestion=("Shorten the document or obtain a waiver. "
                        f"(Non-Secretariat reports allow {NON_SECRETARIAT_LIMIT:,}.)"),
        ))
    elif count > int(limit * 0.95):
        findings.append(Finding(
            rule_id="UN-LEN-002",
            rule_name="Word-count near limit",
            severity=Severity.WARNING,
            message=(f"Document is {count:,} words — within 5% of the "
                     f"{limit:,}-word Secretariat limit."),
            suggestion="Leave headroom: edits and footnotes count toward the limit.",
        ))
    else:
        findings.append(Finding(
            rule_id="UN-LEN-000",
            rule_name="Word-count limit (Secretariat report)",
            severity=Severity.INFO,
            message=f"Word count OK: {count:,} of {limit:,} allowed.",
        ))
    return findings
