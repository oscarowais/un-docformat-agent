"""UN-compliant .docx writer — pure stdlib (zipfile + hand-built OOXML).

Why not python-docx? Two reasons: (1) the output needs exactly four fixed
properties (10-pt Times New Roman, US letter, 1" margins, bold headings), so
a minimal OOXML template is simpler and fully deterministic; (2) it keeps
the writer dependency-free and testable anywhere (python-docx remains a
dependency for READING .docx input in app/ingest).

Produces: word/document.xml (+ styles, content types, rels) in a zip.
Validated by tests/test_docx_writer.py (unzips and asserts the XML).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from app.rules.checks_structure import (_HEADING_HINT, _ROMAN_ITEM,
                                        _SUB_ITEM_GOOD)

# Page geometry in twentieths of a point (twips): US letter, 1" margins.
_PAGE_W, _PAGE_H, _MARGIN = 12240, 15840, 1440
_FONT = "Times New Roman"
_SIZE_HALF_PT = "20"  # 10 pt

# Sub-listing indentation (Section 5: (i)/(ii) indented under (a)/(b)).
# Plain left indents so the markers sit at exactly 0.5" and 1" —
# a hanging offset shifts the first line back and makes steps uneven.
_IND = {
    1: '<w:ind w:left="720"/>',    # (a) level: 0.5"
    2: '<w:ind w:left="1440"/>',   # (i) level: 1", deeper
}


def _indent_level(line: str) -> int:
    """0 = normal paragraph, 1 = (a)-level item, 2 = (i)-level item.
    Roman check first: '(i)' is a roman numeral, not the letter i."""
    if _ROMAN_ITEM.match(line):
        return 2
    if _SUB_ITEM_GOOD.match(line):
        return 1
    return 0

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

# Document defaults: 10-pt Times New Roman for every run.
_STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="{_FONT}" w:hAnsi="{_FONT}" w:cs="{_FONT}"/>
<w:sz w:val="{_SIZE_HALF_PT}"/><w:szCs w:val="{_SIZE_HALF_PT}"/>
</w:rPr></w:rPrDefault></w:docDefaults>
</w:styles>"""


def _para_xml(text: str, bold: bool = False, indent_level: int = 0) -> str:
    """One <w:p>; internal newlines become <w:br/>. Sub-list items get
    structural indentation (w:ind), not literal spaces."""
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    ppr = f"<w:pPr>{_IND[indent_level]}</w:pPr>" if indent_level else ""
    parts = []
    for i, line in enumerate(text.split("\n")):
        if i > 0:
            parts.append("<w:br/>")
        if indent_level:
            line = line.strip()  # indentation is structural, not spaces
        parts.append(f"<w:t xml:space=\"preserve\">{escape(line)}</w:t>")
    return f"<w:p>{ppr}<w:r>{rpr}{''.join(parts)}</w:r></w:p>"


def _split_sub_items(block: str) -> list[str]:
    """Split a multi-line block so each sub-list item starts its own
    paragraph (needed for per-item w:ind); continuation lines stay attached."""
    segments: list[list[str]] = []
    for line in block.splitlines():
        if _indent_level(line) or not segments:
            segments.append([line])
        else:
            segments[-1].append(line)
    return ["\n".join(seg) for seg in segments]


def _is_heading_line(text: str) -> bool:
    t = text.strip()
    return bool(t and _HEADING_HINT.match(t) and len(t.split()) <= 12
                and not t.endswith((".", ":", ";")))


def write_docx(text: str, path: str | Path) -> Path:
    """Write `text` as a UN-formatted .docx (document content only — the
    change log goes in a SEPARATE file, see write_changelog_docx).

    Paragraph split: blank lines (falls back to single newlines).
    Headings (e.g. "II. Key findings") are rendered bold per UN style.
    """
    path = Path(path)
    blocks = re.split(r"\n\s*\n", text) if "\n\n" in text else text.splitlines()

    body: list[str] = []
    for block in blocks:
        block = block.rstrip()
        if not block.strip():
            continue
        for seg in _split_sub_items(block):
            body.append(_para_xml(seg, bold=_is_heading_line(seg),
                                  indent_level=_indent_level(seg)))

    sect = (f"<w:sectPr>"
            f"<w:pgSz w:w=\"{_PAGE_W}\" w:h=\"{_PAGE_H}\"/>"
            f"<w:pgMar w:top=\"{_MARGIN}\" w:right=\"{_MARGIN}\" "
            f"w:bottom=\"{_MARGIN}\" w:left=\"{_MARGIN}\" "
            f"w:header=\"720\" w:footer=\"720\" w:gutter=\"0\"/>"
            f"</w:sectPr>")

    document = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/"
        "wordprocessingml/2006/main\">"
        f"<w:body>{''.join(body)}{sect}</w:body></w:document>")

    _write_package(path, document)
    return path


def write_changelog_docx(entries: list[str], path: str | Path,
                         source: str = "") -> Path:
    """Write the change log as its OWN .docx document (kept separate from
    the formatted output so the deliverable carries no tooling artifacts)."""
    import datetime

    path = Path(path)
    body = [_para_xml("Change log — UN DocFormat Agent", bold=True)]
    meta = f"Generated {datetime.date.today().isoformat()}"
    if source:
        meta += f" from: {source}"
    body.append(_para_xml(meta))
    body.append(_para_xml(f"{len(entries)} change(s) applied:", bold=True))
    for i, entry in enumerate(entries, 1):
        body.append(_para_xml(f"{i}. {entry}"))

    sect = (f"<w:sectPr>"
            f"<w:pgSz w:w=\"{_PAGE_W}\" w:h=\"{_PAGE_H}\"/>"
            f"<w:pgMar w:top=\"{_MARGIN}\" w:right=\"{_MARGIN}\" "
            f"w:bottom=\"{_MARGIN}\" w:left=\"{_MARGIN}\" "
            f"w:header=\"720\" w:footer=\"720\" w:gutter=\"0\"/>"
            f"</w:sectPr>")
    document = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/"
        "wordprocessingml/2006/main\">"
        f"<w:body>{''.join(body)}{sect}</w:body></w:document>")
    _write_package(path, document)
    return path


def _write_package(path: Path, document_xml: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("word/document.xml", document_xml)
