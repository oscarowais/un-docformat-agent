"""Tests for the deterministic autofix + docx writer (pure stdlib)."""

import zipfile
from pathlib import Path

from app.autofix import autofix
from app.ingest import load_text
from app.output import write_changelog_docx, write_docx
from app.rules.engine import run_checks


def test_spelling_fixed_and_logged():
    fixed, log = autofix("The program delivered its judgment.")
    assert "programme" in fixed and "judgement" in fixed
    assert any("Spelling" in e for e in log)


def test_ise_fixed_exceptions_kept():
    fixed, _ = autofix("They organise and comprise units.")
    assert "organize" in fixed
    assert "comprise" in fixed  # exception untouched


def test_country_fixed():
    fixed, log = autofix("Work continued in Vietnam and South Korea.")
    assert "Viet Nam" in fixed and "Republic of Korea" in fixed


def test_correct_country_untouched():
    fixed, log = autofix("Work continued in Viet Nam.")
    assert fixed == "Work continued in Viet Nam."
    assert not log


def test_never_abbreviate_expanded():
    fixed, _ = autofix("The UN and the GA met.")
    assert "The United Nations and the General Assembly met." == fixed


def test_un_inside_acronym_untouched():
    fixed, _ = autofix("The United Nations Development Programme (UNDP) works. "
                       "UNDP continued.")
    assert "UNDP" in fixed  # \bUN\b must not hit "UNDP"


def test_first_use_acronym_expanded():
    fixed, log = autofix("Cooperation with WHO remained strong. WHO agreed.")
    assert fixed.startswith("Cooperation with World Health Organization (WHO)")
    assert fixed.count("World Health Organization") == 1  # only first use


def test_currency_fixed():
    fixed, _ = autofix("Allocation of USD 250,000 was made.")
    assert "$250,000" in fixed


def test_quotes_fixed():
    fixed, _ = autofix("Described as 'highly effective' by all.")
    assert '"highly effective"' in fixed


def test_numbers_and_ordinals_fixed():
    fixed, _ = autofix("Received 5 mandates, the 3rd increase.")
    assert "five mandates" in fixed and "third increase" in fixed


def test_citation_number_untouched():
    fixed, _ = autofix("As noted in paragraph 5 above.")
    assert "paragraph 5" in fixed


def test_sub_marker_fixed():
    fixed, _ = autofix("a) The item was completed;")
    assert fixed.startswith("(a) The item")


def test_nested_item_indented():
    fixed, log = autofix("(a) The first item;\n(i) nested claim handled;")
    assert "\n    (i) nested claim handled;" in fixed
    assert any("indented" in e for e in log)


def test_already_indented_nested_item_untouched():
    fixed, log = autofix("(a) The first item;\n    (i) nested claim handled;")
    assert not log


def test_heading_case_fixed():
    fixed, _ = autofix("II. Key Findings And Observations\n\nBody text here.")
    assert "II. Key findings and observations" in fixed


def test_renumbering():
    body = ("contains at least twenty words of running text so the checker "
            "treats it as a body paragraph for numbering purposes today")
    fixed, log = autofix(f"4. First {body}.\n\n6. Second {body}.")
    assert fixed.startswith("1. First") and "\n\n2. Second" in fixed
    assert any("renumbered" in e for e in log)


def test_autofix_resolves_sample_mechanical_issues():
    sample = Path(__file__).parent.parent / "samples" / "non_compliant_report.txt"
    fixed, log = autofix(sample.read_text(encoding="utf-8"))
    assert len(log) >= 15
    remaining = {f.rule_id for f in run_checks(load_text(fixed))
                 if f.severity.value == "error"}
    # All mechanical error-level rules must be resolved by autofix.
    for resolved in ["UN-TERM-001", "UN-ABB-001", "UN-NUM-002"]:
        assert resolved not in remaining, remaining


def test_markdown_normalization():
    from app.ingest.loaders import normalize_markdown
    md = ("# Title Here\n\n"
          "Some **bold** and *emphasis* and `code` and ***both***.\n\n"
          "- first item\n* second item\n\n"
          "A [link text](https://example.com) inline.\n\n---\n")
    out = normalize_markdown(md)
    assert "#" not in out and "**" not in out and "`" not in out
    assert "bold" in out and "emphasis" in out and "both" in out
    assert "first item" in out and "second item" in out
    assert "link text" in out and "example.com" not in out
    assert "---" not in out


def test_readme_and_tech_terms_not_flagged():
    from app.rules import checks_terminology
    from app.ingest import load_text
    doc = load_text("See the README for the API and the JSON output. "
                    "The MIT licence and PDF export are described there.")
    rids = {f.rule_id for f in checks_terminology.check_abbreviations(doc)}
    assert "UN-ABB-003" not in rids


def test_docx_writer_produces_valid_un_formatted_file():
    import tempfile
    out = Path(tempfile.mkdtemp()) / "test_out.docx"
    text = ("I. Introduction\n\n1. The United Nations continued its work "
            "during the period under review.")
    write_docx(text, out)

    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert {"[Content_Types].xml", "word/document.xml",
                "word/styles.xml"} <= names
        doc = z.read("word/document.xml").decode()
        styles = z.read("word/styles.xml").decode()

    assert 'w:ascii="Times New Roman"' in styles      # font
    assert '<w:sz w:val="20"/>' in styles             # 10 pt
    assert '<w:pgSz w:w="12240" w:h="15840"/>' in doc  # US letter
    assert 'w:top="1440"' in doc                      # 1" margins
    assert "<w:b/>" in doc                            # bold heading
    assert "United Nations continued" in doc          # body content
    assert "change log" not in doc.lower()            # NO change log inside


def test_docx_writer_indents_sub_listings():
    import tempfile
    out = Path(tempfile.mkdtemp()) / "test_ind.docx"
    text = ("1. Findings were as follows:\n\n"
            "(a) The first item was completed;\n"
            "(i) nested claim was handled;")
    write_docx(text, out)
    with zipfile.ZipFile(out) as z:
        doc = z.read("word/document.xml").decode()
    # (a) level at exactly 0.5", (i) level at exactly 1" (no hanging
    # offset — markers must be equidistant from the margin)
    assert '<w:ind w:left="720"/>' in doc
    assert '<w:ind w:left="1440"/>' in doc
    # items became separate paragraphs, not <w:br/> runs in one paragraph
    assert doc.count("<w:p>") >= 3


def test_changelog_is_separate_document():
    import tempfile
    out = Path(tempfile.mkdtemp()) / "changes.docx"
    entries = ["Spelling: \"program\" -> \"programme\"",
               "Terminology: \"Vietnam\" -> \"Viet Nam\" (UNTERM)"]
    write_changelog_docx(entries, out, source="sample.txt")

    with zipfile.ZipFile(out) as z:
        doc = z.read("word/document.xml").decode()
        styles = z.read("word/styles.xml").decode()

    assert "Change log" in doc
    assert "sample.txt" in doc
    assert "programme" in doc and "Viet Nam" in doc
    assert "2 change(s) applied" in doc
    assert 'w:ascii="Times New Roman"' in styles      # same UN formatting
