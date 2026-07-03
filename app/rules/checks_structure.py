"""Structure & numbering rules.

UN rules covered here:
- Main headings/subheadings in bold, sentence case (initial capital on the
  first word and normally-capitalized words only — no Title Case/ALL CAPS).
- Body paragraphs numbered consecutively (1., 2., ...); paragraph numbers,
  not page numbers, are what get cited.
- Sub-listings use (a), (b)...; nested sub-listings use (i), (ii)..., indented.
"""

from __future__ import annotations

import re

from app.document import DocumentModel, Paragraph
from app.rules.base import Finding, Severity

# Words allowed to keep a capital inside a sentence-case heading:
# roman numerals, acronyms/all-caps, numbers, and common UN proper nouns.
_CAP_OK = re.compile(
    r"^(?:[IVXLC]+|[A-Z]{2,}s?|\d.*|United|Nations|General|Assembly|Security"
    r"|Council|Secretary-General|Secretariat|Member|States?|Charter"
    r"|Organization|Africa|Asia|Europe|America[s]?)[,:;.]?$"
)

_PARA_NUM = re.compile(r"^(\d{1,3})\.\s+\S")          # "12. Text..."
_SUB_ITEM_BAD = re.compile(r"^\s*(?:([a-z])\)|(\d{1,2})\))\s+\S")  # "a) ..." or "1) ..."
_SUB_ITEM_GOOD = re.compile(r"^\s*\(([a-z])\)\s+\S")   # "(a) ..."
_ROMAN_ITEM = re.compile(r"^\s*\((i{1,3}|iv|v|vi{0,3}|ix|x)\)\s+\S")

_HEADING_HINT = re.compile(r"^(?:[IVXLC]+\.|[A-Z]\.)\s+\S")  # "II. ..." / "A. ..."


def _looks_like_heading(p: Paragraph) -> bool:
    """Heuristic for plain-text sources; docx loader sets p.is_heading."""
    if p.is_heading:
        return True
    t = p.text.strip()
    if not t or len(t.split()) > 12 or t.endswith((".", ":", ";")):
        return False
    return bool(_HEADING_HINT.match(t))


def _heading_text(t: str) -> str:
    """Strip 'II.' / 'A.' prefix from a heading line."""
    return re.sub(r"^(?:[IVXLC]+\.|[A-Z]\.)\s+", "", t.strip())


def check_headings(doc: DocumentModel) -> list[Finding]:
    findings: list[Finding] = []
    for p in doc.paragraphs:
        if not _looks_like_heading(p):
            continue
        body = _heading_text(p.text)
        words = body.split()
        if not words:
            continue

        # ALL CAPS headings — block capitals are not permitted.
        letters = [c for c in body if c.isalpha()]
        if letters and all(c.isupper() for c in letters) and len(letters) > 3:
            findings.append(Finding(
                rule_id="UN-HDG-001",
                rule_name="Heading capitalization",
                severity=Severity.WARNING,
                message="Heading is in block capitals; UN headings use "
                        "sentence case (initial capital on first word only).",
                suggestion=f"Rewrite as: \"{body.capitalize()}\"",
                paragraph_index=p.index,
                snippet=p.text.strip(),
            ))
            continue

        # Title Case detection: 2+ capitalized non-first words that aren't
        # proper-noun-ish per _CAP_OK.
        suspicious = [w for w in words[1:]
                      if w[:1].isupper() and not _CAP_OK.match(w)]
        if len(suspicious) >= 2:
            fixed = words[0] + " " + " ".join(
                w if _CAP_OK.match(w) else w.lower() for w in words[1:])
            findings.append(Finding(
                rule_id="UN-HDG-002",
                rule_name="Heading capitalization",
                severity=Severity.WARNING,
                message="Heading appears to use Title Case; UN headings use "
                        "sentence case (capitals only for the first word and "
                        "normally-capitalized words).",
                suggestion=f"Rewrite as: \"{fixed}\"",
                paragraph_index=p.index,
                snippet=p.text.strip(),
            ))

        # Bold requirement — only verifiable in .docx sources.
        if doc.source_format == "docx" and not p.is_bold:
            findings.append(Finding(
                rule_id="UN-HDG-003",
                rule_name="Headings in bold",
                severity=Severity.WARNING,
                message="Main headings and subheadings must be in bold print.",
                suggestion="Apply bold formatting to this heading.",
                paragraph_index=p.index,
                snippet=p.text.strip(),
            ))
    return findings


def check_paragraph_numbering(doc: DocumentModel) -> list[Finding]:
    """Body paragraphs of a Secretariat report are numbered 1., 2., 3., ...
    consecutively; references cite paragraph numbers, not pages."""
    findings: list[Finding] = []
    numbered: list[tuple[int, int]] = []  # (paragraph_index, number)
    body_paras = 0

    for p in doc.paragraphs:
        t = p.text.strip()
        if not t or _looks_like_heading(p):
            continue
        m = _PARA_NUM.match(t)
        if m:
            numbered.append((p.index, int(m.group(1))))
        elif len(t.split()) >= 20 and not _SUB_ITEM_GOOD.match(t) \
                and not _SUB_ITEM_BAD.match(t) and not _ROMAN_ITEM.match(t):
            body_paras += 1

    if not numbered and body_paras >= 3:
        findings.append(Finding(
            rule_id="UN-NUM-001",
            rule_name="Paragraph numbering",
            severity=Severity.ERROR,
            message=f"No numbered body paragraphs found ({body_paras} "
                    "unnumbered body paragraphs detected). Secretariat report "
                    "paragraphs must be numbered consecutively — references "
                    "cite paragraph numbers, not page numbers.",
            suggestion="Number body paragraphs sequentially: 1., 2., 3., ...",
        ))
        return findings

    # Check the numbered sequence is consecutive starting at 1.
    expected = 1
    for idx, n in numbered:
        if n != expected:
            findings.append(Finding(
                rule_id="UN-NUM-002",
                rule_name="Paragraph numbering sequence",
                severity=Severity.ERROR,
                message=f"Paragraph number {n} found where {expected} was "
                        "expected — numbering must be consecutive.",
                suggestion=f"Renumber this paragraph to {expected} and shift "
                           "subsequent paragraphs accordingly.",
                paragraph_index=idx,
                snippet=doc.paragraphs[idx].text.strip()[:80],
            ))
            expected = n + 1  # resync so one gap doesn't cascade
        else:
            expected += 1

    # Unnumbered body paragraphs mixed in with numbered ones.
    if numbered and body_paras:
        findings.append(Finding(
            rule_id="UN-NUM-003",
            rule_name="Paragraph numbering coverage",
            severity=Severity.WARNING,
            message=f"{body_paras} body paragraph(s) lack numbers while "
                    "others are numbered — numbering must cover all body "
                    "paragraphs.",
            suggestion="Number every body paragraph consecutively.",
        ))
    return findings


def check_sublistings(doc: DocumentModel) -> list[Finding]:
    """Sub-listings use (a), (b)...; nested items use (i), (ii)..., indented."""
    findings: list[Finding] = []
    for p in doc.paragraphs:
        t = p.text
        m = _SUB_ITEM_BAD.match(t)
        if m:
            wrong = (m.group(1) or m.group(2)) + ")"
            right = f"({m.group(1)})" if m.group(1) else "(a)/(b) letters"
            findings.append(Finding(
                rule_id="UN-SUB-001",
                rule_name="Sub-listing format",
                severity=Severity.WARNING,
                message=f"Sub-listing marker \"{wrong}\" is non-standard; UN "
                        "sub-listings use parenthesized lowercase letters, "
                        "with (i), (ii) for the nested level.",
                suggestion=f"Use \"{right}\" style: (a), (b), ... and (i), "
                           "(ii), ... indented for nested items.",
                paragraph_index=p.index,
                snippet=t.strip()[:80],
            ))

        # Nested roman items should be indented relative to (a)-level.
        rm = _ROMAN_ITEM.match(t)
        if rm and not t.startswith((" ", "\t")):
            findings.append(Finding(
                rule_id="UN-SUB-002",
                rule_name="Nested sub-listing indentation",
                severity=Severity.INFO,
                message="(i)/(ii) sub-listing is not indented; nested items "
                        "should be indented under their (a)-level parent.",
                suggestion="Indent (i), (ii), ... items.",
                paragraph_index=p.index,
                snippet=t.strip()[:80],
            ))
    return findings
