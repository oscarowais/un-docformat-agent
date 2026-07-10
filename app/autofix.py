"""Deterministic autofix — mechanical corrections the rules engine can make
without a model, each recorded in a change log.

Scope: only high-confidence, dictionary/regex-driven fixes (spelling, UNTERM
names, currency codes, quotation marks, number words, sub-list markers,
paragraph renumbering, heading case, never-abbreviate expansion). Judgment
calls (restructuring, shortening to the word limit, unknown acronyms) are
left to the model layer (Day 3) — the change log notes what remains.

Usage:
    fixed_text, change_log = autofix(raw_text)
"""

from __future__ import annotations

import re

from app.rules.checks_structure import (_CAP_OK, _HEADING_HINT, _PARA_NUM,
                                        _ROMAN_ITEM, _heading_text)
from app.rules.vocab import (ISE_EXCEPTIONS, KNOWN_ACRONYMS, NEVER_ABBREVIATE,
                             NUMBER_WORDS, ORDINAL_WORDS, UN_SPELLING,
                             UNTERM_COUNTRIES)

_ISE = re.compile(r"\b([A-Za-z]{3,})(ise|ised|ising|isation|isations)\b")
_SINGLE_QUOTE = re.compile(r"(?<![A-Za-z])'([^'\n]{2,120})'(?![A-Za-z])")
# guards: not adjacent to digits/currency, not before dashes (ranges),
# not before a following number token (product codes: "Ryzen 9 9950X"),
# not before an inch mark
_SMALL_DIGIT = re.compile(
    r"(?<![\d.,/($€£–—-])\b([1-9])\b(?![\d.,:%/)–—\"-])(?!\s+\d)")
_CITE_BEFORE = re.compile(
    r"(paragraph|paragraphs|para\.|sect\.|section|chapter|article|resolution"
    r"|annex|table|figure|page|item|goal|rule|decision|part|day|track|step"
    r"|phase|version|no\.|january|february|march|april|may|june|july|august"
    r"|september|october|november|december)\s*:?\s*$",
    re.IGNORECASE)
_ORDINAL_NUM = re.compile(r"\b([1-9])(st|nd|rd|th)\b")
# double-quoted spans are verbatim material — never edited
_DQ_SPAN = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”")
_CURRENCY_CODE = re.compile(r"\b(USD|EUR|CHF)\s?([\d,.]+)\b")
_SUB_MARKER = re.compile(r"(^|\n)(\s*)([a-z])\)\s", re.MULTILINE)
_CURRENCY_SYMBOL = {"USD": "$", "EUR": "€", "CHF": "SwF"}


def _match_case(replacement: str, original: str) -> str:
    return replacement.capitalize() if original[:1].isupper() else replacement


def _fix_spelling(text: str, log: list[str]) -> str:
    def sub(m: re.Match) -> str:
        w = m.group(0)
        right = _match_case(UN_SPELLING[w.lower()], w)
        log.append(f"Spelling: \"{w}\" -> \"{right}\" (Oxford/UN preferred form)")
        return right

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in UN_SPELLING) + r")\b",
        re.IGNORECASE)
    return pattern.sub(sub, text)


def _fix_ise(text: str, log: list[str]) -> str:
    def sub(m: re.Match) -> str:
        whole, stem, suffix = m.group(0), m.group(1), m.group(2)
        if (stem + "ise").lower() in ISE_EXCEPTIONS:
            return whole
        fixed = stem + suffix.replace("is", "iz", 1)
        log.append(f"Suffix: \"{whole}\" -> \"{fixed}\" (-ize preferred)")
        return fixed

    return _ISE.sub(sub, text)


def _fix_countries(text: str, log: list[str]) -> str:
    for wrong, right in UNTERM_COUNTRIES.items():
        pattern = re.compile(r"\b" + re.escape(wrong) + r"\b")
        def sub(m: re.Match, right=right, wrong=wrong) -> str:
            # Don't touch text that is already part of the correct form.
            log.append(f"Terminology: \"{wrong}\" -> \"{right}\" (UNTERM)")
            return right
        # Guard: skip if correct form already contains the wrong form and
        # is present around the match (e.g. "Korea" inside "Republic of Korea").
        out = []
        last = 0
        for m in pattern.finditer(text):
            ctx = text[max(0, m.start() - 30):m.end() + 30]
            if right in ctx:
                continue
            out.append(text[last:m.start()])
            out.append(sub(m))
            last = m.end()
        out.append(text[last:])
        text = "".join(out)
    return text


def _fix_never_abbreviate(text: str, log: list[str]) -> str:
    for abbr, full in NEVER_ABBREVIATE.items():
        pattern = re.compile(r"\b" + abbr + r"\b(?!['’])")
        n = len(pattern.findall(text))
        if n:
            text = pattern.sub(full, text)
            log.append(f"Abbreviation: \"{abbr}\" -> \"{full}\" "
                       f"({n} occurrence(s); never abbreviated)")
    return text


def _fix_first_use_acronyms(text: str, log: list[str]) -> str:
    """Expand the FIRST use of known acronyms to 'Full Name (ACRO)' unless
    the full form already appears earlier."""
    for acro, full in KNOWN_ACRONYMS.items():
        if acro.endswith("s") and acro[:-1] in KNOWN_ACRONYMS:
            continue  # plural handled by singular entry
        m = re.search(r"\b" + acro + r"\b", text)
        if not m:
            continue
        before = text[:m.start()].lower()
        if full.lower() in before:
            continue
        # Already a definition like "Full Name (ACRO)" at this position?
        if text[max(0, m.start() - 1):m.start()] == "(":
            continue
        text = text[:m.start()] + f"{full} ({acro})" + text[m.end():]
        log.append(f"Abbreviation: first use of \"{acro}\" expanded to "
                   f"\"{full} ({acro})\"")
    return text


def _fix_currency(text: str, log: list[str]) -> str:
    def sub(m: re.Match) -> str:
        fixed = f"{_CURRENCY_SYMBOL[m.group(1)]}{m.group(2)}"
        log.append(f"Currency: \"{m.group(0)}\" -> \"{fixed}\"")
        return fixed

    return _CURRENCY_CODE.sub(sub, text)


def _fix_quotes(text: str, log: list[str]) -> str:
    def sub(m: re.Match) -> str:
        log.append(f"Quotation: '{m.group(1)}' -> double quotation marks")
        return f"\"{m.group(1)}\""

    return _SINGLE_QUOTE.sub(sub, text)


def _fix_numbers(text: str, log: list[str]) -> str:
    def sub_digit(m: re.Match) -> str:
        if _CITE_BEFORE.search(text[:m.start()][-30:]):
            return m.group(0)
        word = NUMBER_WORDS[int(m.group(1))]
        log.append(f"Number: \"{m.group(1)}\" -> \"{word}\" (under 10 in words)")
        return word

    def sub_ordinal(m: re.Match) -> str:
        word = ORDINAL_WORDS[int(m.group(1))]
        log.append(f"Ordinal: \"{m.group(0)}\" -> \"{word}\"")
        return word

    text = _ORDINAL_NUM.sub(sub_ordinal, text)
    return _SMALL_DIGIT.sub(sub_digit, text)


def _fix_sub_markers(text: str, log: list[str]) -> str:
    def sub(m: re.Match) -> str:
        log.append(f"Sub-listing: \"{m.group(3)})\" -> \"({m.group(3)})\"")
        return f"{m.group(1)}{m.group(2)}({m.group(3)}) "

    return _SUB_MARKER.sub(sub, text)


def _fix_nested_indent(text: str, log: list[str]) -> str:
    """Indent (i)/(ii) items that sit flush left — nested sub-listings are
    indented under their (a)-level parent (Section 5). Runs after
    _fix_sub_markers so markers are already in (i) form."""
    out = []
    for line in text.splitlines():
        if _ROMAN_ITEM.match(line) and not line[:1] in (" ", "\t"):
            marker = line.split(")", 1)[0] + ")"
            log.append(f"Sub-listing: nested item \"{marker}\" indented "
                       "under its parent item")
            line = "    " + line
        out.append(line)
    return "\n".join(out)


def _fix_headings(lines: list[str], log: list[str]) -> list[str]:
    """Sentence-case block-caps / Title Case heading lines (in place)."""
    fixed = []
    for line in lines:
        stripped = line.strip()
        if stripped and _HEADING_HINT.match(stripped) \
                and len(stripped.split()) <= 12 \
                and not stripped.endswith((".", ":", ";")):
            prefix = stripped[:len(stripped) - len(_heading_text(stripped))]
            body = _heading_text(stripped)
            words = body.split()
            letters = [c for c in body if c.isalpha()]
            if letters and all(c.isupper() for c in letters) and len(letters) > 3:
                new_body = body.capitalize()
            else:
                suspicious = [w for w in words[1:]
                              if w[:1].isupper() and not _CAP_OK.match(w)]
                if len(suspicious) < 2:
                    fixed.append(line)
                    continue
                new_body = words[0] + " " + " ".join(
                    w if _CAP_OK.match(w) else w.lower() for w in words[1:])
            if new_body != body:
                log.append(f"Heading: \"{body}\" -> \"{new_body}\" (sentence case)")
                fixed.append(prefix + new_body)
                continue
        fixed.append(line)
    return fixed


def _renumber_paragraphs(lines: list[str], log: list[str]) -> list[str]:
    """Renumber existing 'N. ' paragraphs consecutively from 1."""
    counter = 0
    out = []
    for line in lines:
        m = _PARA_NUM.match(line.strip())
        if m:
            counter += 1
            old = int(m.group(1))
            if old != counter:
                line = re.sub(r"^(\s*)\d{1,3}\.", rf"\g<1>{counter}.", line, count=1)
                log.append(f"Numbering: paragraph {old} renumbered to {counter}")
        out.append(line)
    return out


def _mask_quoted(text: str) -> tuple[str, list[str]]:
    """Replace double-quoted spans with placeholders. Quoted material is
    verbatim — an editor never rewrites the inside of a quotation."""
    spans: list[str] = []

    def repl(m: re.Match) -> str:
        spans.append(m.group(0))
        return f"\x00Q{len(spans) - 1}\x00"

    return _DQ_SPAN.sub(repl, text), spans


def _unmask_quoted(text: str, spans: list[str]) -> str:
    for i, s in enumerate(spans):
        text = text.replace(f"\x00Q{i}\x00", s)
    return text


def autofix(text: str) -> tuple[str, list[str]]:
    """Apply all deterministic fixes; return (fixed_text, change_log)."""
    log: list[str] = []

    # Line-based fixes first (headings, renumbering), then flowing-text fixes.
    lines = text.splitlines()
    lines = _fix_headings(lines, log)
    lines = _renumber_paragraphs(lines, log)
    text = "\n".join(lines)

    # Normalize quotation marks FIRST, then protect everything inside
    # double quotes from all subsequent text-level fixes.
    text = _fix_quotes(text, log)
    text, quoted = _mask_quoted(text)

    text = _fix_never_abbreviate(text, log)
    text = _fix_first_use_acronyms(text, log)
    text = _fix_countries(text, log)
    text = _fix_spelling(text, log)
    text = _fix_ise(text, log)
    text = _fix_currency(text, log)
    text = _fix_numbers(text, log)

    text = _unmask_quoted(text, quoted)
    text = _fix_sub_markers(text, log)
    text = _fix_nested_indent(text, log)
    return text, log
