"""Document model shared by ingestion, rules engine, and (later) the model layer.

Loaders (app/ingest) normalise .txt/.md/.docx input into a DocumentModel so
every rule checker works against one shape regardless of the source format.
Docx-only properties (font, page size, footnotes) go into `metadata`; rules
that need them skip gracefully when the source is plain text.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Paragraph:
    """One block of text (paragraph or heading) with source position."""

    index: int                    # 0-based paragraph index in the document
    text: str
    is_heading: bool = False      # set by loader (docx styles) or heuristics
    is_bold: bool = False         # entire paragraph bold (docx only, else False)


@dataclass
class DocumentModel:
    """Normalised document, independent of the original file format."""

    paragraphs: list[Paragraph] = field(default_factory=list)
    source_path: str | None = None
    source_format: str = "txt"    # "txt" | "md" | "docx" | "raw"
    # Docx-only page/typography metadata. Keys used by rules:
    #   fonts: set[str]              distinct font names found in runs
    #   font_sizes: set[float]       distinct point sizes found in runs
    #   page_width_in / page_height_in: float
    #   margins_in: dict(top/bottom/left/right -> float)
    #   has_endnotes: bool
    #   has_footnotes: bool
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.paragraphs)

    def word_count(self) -> int:
        """Total words incl. headings (UN limit counts footnotes, headings,
        hidden text — we count everything the loader captured)."""
        return sum(len(p.text.split()) for p in self.paragraphs)
