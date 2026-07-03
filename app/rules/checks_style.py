"""Style rules: spelling, -ize suffix, quotation marks, numbers, currency.

UN rules covered here:
- Concise Oxford spelling, first-listed form ("programme", "judgement").
- "-ize" preferred over "-ise".
- Quotations in double quotation marks.
- Numbers under 10 in words; ordinals first–ninety-ninth in words.
- Currency symbols ($, €, SwF; country prefix for non-US dollars, e.g. Can$50).
"""

from __future__ import annotations

import re

from app.document import DocumentModel
from app.rules.base import Finding, Severity, snippet_of
from app.rules.vocab import (ISE_EXCEPTIONS, NUMBER_WORDS, ORDINAL_WORDS,
                             UN_SPELLING)

_WORD = re.compile(r"[A-Za-z]+")
_ISE = re.compile(r"\b([A-Za-z]{3,})(ise|ised|ising|isation|isations)\b")
# Single-quoted span of reasonable length (avoid apostrophes/contractions).
_SINGLE_QUOTE = re.compile(r"(?<![A-Za-z])'([^'\n]{2,120})'(?![A-Za-z])")
# Standalone small digits: not part of larger numbers, decimals, refs, dates,
# percentages, currency, paragraph citations, or list numbering.
_SMALL_DIGIT = re.compile(r"(?<![\d.,/($€£-])\b([1-9])\b(?![\d.,:%/)-])")
_CITE_BEFORE = re.compile(
    r"(paragraph|paragraphs|para\.|sect\.|section|chapter|article|resolution"
    r"|annex|table|figure|page|item|goal|rule|decision|part)\s*$",
    re.IGNORECASE)
_ORDINAL_NUM = re.compile(r"\b([1-9]\d?)(st|nd|rd|th)\b")
_CURRENCY_CODE = re.compile(r"\b(USD|EUR|CHF)\s?([\d,.]+)\b")
_DOLLARS_WORD = re.compile(r"\b([\d,.]+)\s+(?:US\s+)?dollars\b", re.IGNORECASE)


def check_spelling(doc: DocumentModel) -> list[Finding]:
    findings: list[Finding] = []
    text = doc.full_text
    flagged: set[str] = set()

    for m in _WORD.finditer(text):
        w = m.group(0)
        wl = w.lower()
        if wl in UN_SPELLING and wl not in flagged:
            flagged.add(wl)
            right = UN_SPELLING[wl]
            if w[0].isupper():
                right = right.capitalize()
            note = ""
            if wl.startswith("program"):
                note = (" (Exception: keep \"program\" only for computer "
                        "programs.)")
            findings.append(Finding(
                rule_id="UN-SPL-001",
                rule_name="Oxford/UN spelling",
                severity=Severity.WARNING,
                message=f"\"{w}\" is not the UN-preferred spelling.{note}",
                suggestion=f"Use \"{right}\" (Concise Oxford, first-listed "
                           "form). Apply to all occurrences.",
                snippet=snippet_of(text, m.start(), m.end()),
            ))

    # -ise → -ize preference.
    for m in _ISE.finditer(text):
        base = (m.group(1) + "ise").lower()
        if base in ISE_EXCEPTIONS or base.rstrip("d") in ISE_EXCEPTIONS:
            continue
        whole = m.group(0)
        if whole.lower() in flagged:
            continue
        flagged.add(whole.lower())
        fixed = whole.replace("is", "iz", 1) if "is" not in m.group(1).lower() \
            else m.group(1) + m.group(2).replace("is", "iz", 1)
        findings.append(Finding(
            rule_id="UN-SPL-002",
            rule_name="-ize suffix preference",
            severity=Severity.WARNING,
            message=f"\"{whole}\" uses the -ise form; UN style prefers -ize.",
            suggestion=f"Use \"{fixed}\". Apply to all occurrences.",
            snippet=snippet_of(text, m.start(), m.end()),
        ))
    return findings


def check_quotations(doc: DocumentModel) -> list[Finding]:
    findings: list[Finding] = []
    text = doc.full_text
    for m in _SINGLE_QUOTE.finditer(text):
        inner = m.group(1)
        # Skip likely possessives/contractions caught despite the guards.
        if re.match(r"^[a-z]{1,2}$", inner):
            continue
        findings.append(Finding(
            rule_id="UN-QUO-001",
            rule_name="Double quotation marks",
            severity=Severity.WARNING,
            message="Quotation uses single quotation marks; UN style requires "
                    "double quotation marks.",
            suggestion=f"Change to: \"{inner}\"",
            snippet=snippet_of(text, m.start(), m.end()),
        ))
    return findings


def check_numbers(doc: DocumentModel) -> list[Finding]:
    findings: list[Finding] = []
    for p in doc.paragraphs:
        t = p.text
        # Strip a leading paragraph number ("12. ") so it isn't flagged.
        body = re.sub(r"^\s*\d{1,3}\.\s+", "", t)
        offset = len(t) - len(body)

        for m in _SMALL_DIGIT.finditer(body):
            # Skip citations like "paragraph 5", "table 3", "resolution 2".
            if _CITE_BEFORE.search(body[:m.start()]):
                continue
            n = int(m.group(1))
            findings.append(Finding(
                rule_id="UN-NUMW-001",
                rule_name="Numbers under 10 in words",
                severity=Severity.WARNING,
                message=f"Numeral \"{n}\" should be spelled out (numbers "
                        "under 10 are written in words).",
                suggestion=f"Use \"{NUMBER_WORDS[n]}\".",
                paragraph_index=p.index,
                snippet=snippet_of(t, m.start() + offset, m.end() + offset),
            ))

        for m in _ORDINAL_NUM.finditer(body):
            n = int(m.group(1))
            word = ORDINAL_WORDS.get(n, f"{n}th in words")
            findings.append(Finding(
                rule_id="UN-NUMW-002",
                rule_name="Ordinals in words",
                severity=Severity.WARNING,
                message=f"Ordinal \"{m.group(0)}\" should be spelled out "
                        "(first through ninety-ninth are written in words).",
                suggestion=f"Use \"{word}\".",
                paragraph_index=p.index,
                snippet=snippet_of(t, m.start() + offset, m.end() + offset),
            ))
    return findings


def check_currency(doc: DocumentModel) -> list[Finding]:
    findings: list[Finding] = []
    text = doc.full_text
    symbol = {"USD": "$", "EUR": "€", "CHF": "SwF"}

    for m in _CURRENCY_CODE.finditer(text):
        code, amount = m.group(1), m.group(2)
        findings.append(Finding(
            rule_id="UN-CUR-001",
            rule_name="Currency symbols",
            severity=Severity.WARNING,
            message=f"Currency written as \"{m.group(0)}\"; UN style uses "
                    "symbols, not ISO codes.",
            suggestion=f"Use \"{symbol[code]}{amount}\" (non-US dollar "
                       "currencies take a country prefix, e.g. Can$50).",
            snippet=snippet_of(text, m.start(), m.end()),
        ))

    for m in _DOLLARS_WORD.finditer(text):
        findings.append(Finding(
            rule_id="UN-CUR-002",
            rule_name="Currency symbols",
            severity=Severity.INFO,
            message=f"Amount written as \"{m.group(0)}\"; consider the "
                    "symbol form.",
            suggestion=f"Use \"${m.group(1)}\".",
            snippet=snippet_of(text, m.start(), m.end()),
        ))
    return findings
