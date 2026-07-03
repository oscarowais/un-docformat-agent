"""Terminology & abbreviation rules.

UN rules covered here:
- Acronyms spelled out in full on first occurrence, short form thereafter.
- "United Nations", "General Assembly", etc. never abbreviated in running text.
- Country/geographical names per UNTERM (e.g. "Viet Nam", "Republic of Korea").
"""

from __future__ import annotations

import re

from app.document import DocumentModel
from app.rules.base import Finding, Severity, snippet_of
from app.rules.vocab import (ACRONYM_IGNORE, KNOWN_ACRONYMS, NEVER_ABBREVIATE,
                             UNTERM_COUNTRIES)

_ACRONYM = re.compile(r"\b([A-Z]{2,6}s?)\b")


def _first_defined_before(full_text_lower: str, acro: str, pos: int) -> bool:
    """True if the acronym's full form appears before position `pos`, or the
    'Full Name (ACRO)' definition pattern appears before/at first use."""
    full = KNOWN_ACRONYMS.get(acro)
    if full and full.lower() in full_text_lower[:pos]:
        return True
    # Generic definition pattern anywhere before this use: "... (ACRO)"
    if re.search(r"\([^)]*\b" + re.escape(acro) + r"\b[^)]*\)",
                 full_text_lower[:pos + len(acro) + 2], re.IGNORECASE):
        return True
    return False


def check_abbreviations(doc: DocumentModel) -> list[Finding]:
    findings: list[Finding] = []
    text = doc.full_text
    text_lower = text.lower()
    seen: set[str] = set()

    for m in _ACRONYM.finditer(text):
        raw = m.group(1)
        acro = raw.rstrip("s") if raw.endswith("s") and raw[:-1].isupper() else raw

        if acro in ACRONYM_IGNORE or acro in seen:
            continue

        # Never-abbreviate terms: flag every first occurrence hard.
        if acro in NEVER_ABBREVIATE:
            # Skip if it's inside a parenthetical definition like "(UN)".
            seen.add(acro)
            findings.append(Finding(
                rule_id="UN-ABB-001",
                rule_name="Never-abbreviated terms",
                severity=Severity.ERROR,
                message=f"\"{acro}\" must not be abbreviated in running text "
                        f"of formal documents.",
                suggestion=f"Spell out as \"{NEVER_ABBREVIATE[acro]}\" "
                           "throughout.",
                snippet=snippet_of(text, m.start(), m.end()),
            ))
            continue

        seen.add(acro)
        if acro in KNOWN_ACRONYMS or raw in KNOWN_ACRONYMS:
            full = KNOWN_ACRONYMS.get(acro) or KNOWN_ACRONYMS.get(raw, "")
            if not _first_defined_before(text_lower, acro, m.start()):
                findings.append(Finding(
                    rule_id="UN-ABB-002",
                    rule_name="Abbreviation expanded on first use",
                    severity=Severity.WARNING,
                    message=f"\"{acro}\" is used before being spelled out in "
                            "full; abbreviations must be given in full on "
                            "first occurrence.",
                    suggestion=f"First occurrence should read: \"{full} "
                               f"({acro})\", then \"{acro}\" thereafter.",
                    snippet=snippet_of(text, m.start(), m.end()),
                ))
        elif len(acro) >= 3:
            # Unknown acronym — we can't verify its expansion, so advise.
            if not _first_defined_before(text_lower, acro, m.start()):
                findings.append(Finding(
                    rule_id="UN-ABB-003",
                    rule_name="Unrecognized abbreviation",
                    severity=Severity.INFO,
                    message=f"\"{acro}\" appears without a spelled-out first "
                            "use; verify it is expanded on first occurrence.",
                    suggestion=f"Ensure first use reads \"Full Name ({acro})\".",
                    snippet=snippet_of(text, m.start(), m.end()),
                ))
    return findings


def check_country_names(doc: DocumentModel) -> list[Finding]:
    findings: list[Finding] = []
    text = doc.full_text
    for wrong, right in UNTERM_COUNTRIES.items():
        for m in re.finditer(r"\b" + re.escape(wrong) + r"\b", text):
            # Skip if the match is actually part of the correct form
            # (e.g. "Viet Nam" won't match "Vietnam"; but "Korea" inside
            # "Republic of Korea" would — guard with a lookbehind check).
            ctx = text[max(0, m.start() - 30):m.end() + 30]
            if right in ctx:
                continue
            findings.append(Finding(
                rule_id="UN-TERM-001",
                rule_name="UNTERM country name",
                severity=Severity.ERROR,
                message=f"\"{wrong}\" is not the UN-approved name.",
                suggestion=f"Use \"{right}\" (UNTERM).",
                snippet=snippet_of(text, m.start(), m.end()),
            ))
    return findings
