"""Rules engine tests — pure Python, no network/model access needed.

Run with pytest, or with the dependency-free runner: python tests/run_tests.py
"""

from app.ingest import load_text
from app.rules.engine import run_checks, summarize
from app.rules import checks_length, checks_structure, checks_style, \
    checks_terminology


def ids(findings):
    return {f.rule_id for f in findings}


# --- word count --------------------------------------------------------------

def test_word_count_over_limit():
    doc = load_text("word " * 9000)
    f = checks_length.check_word_count(doc)
    assert "UN-LEN-001" in ids(f)


def test_word_count_ok():
    doc = load_text("A short compliant paragraph.")
    f = checks_length.check_word_count(doc)
    assert ids(f) == {"UN-LEN-000"}


# --- headings ----------------------------------------------------------------

def test_block_caps_heading_flagged():
    doc = load_text("I. INTRODUCTION AND BACKGROUND\n\n" + "text " * 30)
    assert "UN-HDG-001" in ids(checks_structure.check_headings(doc))


def test_title_case_heading_flagged():
    doc = load_text("II. Key Findings And Observations\n\n" + "text " * 30)
    assert "UN-HDG-002" in ids(checks_structure.check_headings(doc))


def test_sentence_case_heading_ok():
    doc = load_text("II. Key findings and observations\n\n" + "text " * 30)
    assert not ids(checks_structure.check_headings(doc))


# --- paragraph numbering -----------------------------------------------------

def test_missing_numbering_flagged():
    paras = "\n\n".join("This unnumbered body paragraph contains at least "
                        "twenty words of running text to be treated as body "
                        "content by the checker heuristics." for _ in range(4))
    doc = load_text(paras)
    assert "UN-NUM-001" in ids(checks_structure.check_paragraph_numbering(doc))


def test_gap_in_numbering_flagged():
    body = ("contains at least twenty words of running text so the checker "
            "treats it as a body paragraph for numbering purposes today")
    doc = load_text(f"1. First {body}.\n\n2. Second {body}.\n\n4. Fourth {body}.")
    f = checks_structure.check_paragraph_numbering(doc)
    assert "UN-NUM-002" in ids(f)


def test_consecutive_numbering_ok():
    body = ("contains at least twenty words of running text so the checker "
            "treats it as a body paragraph for numbering purposes today")
    doc = load_text(f"1. First {body}.\n\n2. Second {body}.\n\n3. Third {body}.")
    assert not ids(checks_structure.check_paragraph_numbering(doc))


# --- sub-listings ------------------------------------------------------------

def test_bad_sublist_marker_flagged():
    doc = load_text("a) The programme of work was completed;")
    assert "UN-SUB-001" in ids(checks_structure.check_sublistings(doc))


def test_good_sublist_marker_ok():
    doc = load_text("(a) The programme of work was completed;")
    assert "UN-SUB-001" not in ids(checks_structure.check_sublistings(doc))


# --- terminology -------------------------------------------------------------

def test_un_abbreviation_flagged():
    doc = load_text("The UN continued its support.")
    f = checks_terminology.check_abbreviations(doc)
    assert "UN-ABB-001" in ids(f)


def test_known_acronym_without_expansion_flagged():
    doc = load_text("Cooperation with UNDP remained strong.")
    assert "UN-ABB-002" in ids(checks_terminology.check_abbreviations(doc))


def test_expanded_acronym_ok():
    doc = load_text("The United Nations Development Programme (UNDP) grew. "
                    "UNDP continued its work.")
    assert "UN-ABB-002" not in ids(checks_terminology.check_abbreviations(doc))


def test_country_name_flagged():
    doc = load_text("Support continued in Vietnam and South Korea.")
    f = checks_terminology.check_country_names(doc)
    assert len([x for x in f if x.rule_id == "UN-TERM-001"]) == 2


def test_correct_country_name_ok():
    doc = load_text("Support continued in Viet Nam.")
    assert not ids(checks_terminology.check_country_names(doc))


# --- style -------------------------------------------------------------------

def test_us_spelling_flagged():
    doc = load_text("The program delivered its judgment on time.")
    rids = ids(checks_style.check_spelling(doc))
    assert "UN-SPL-001" in rids


def test_ise_suffix_flagged():
    doc = load_text("The mission continued to organise workshops.")
    assert "UN-SPL-002" in ids(checks_style.check_spelling(doc))


def test_ise_exception_not_flagged():
    doc = load_text("The report will comprise three sections and advise action.")
    assert "UN-SPL-002" not in ids(checks_style.check_spelling(doc))


def test_single_quotes_flagged():
    doc = load_text("Participants called it 'highly effective' overall.")
    assert "UN-QUO-001" in ids(checks_style.check_quotations(doc))


def test_apostrophe_not_flagged():
    doc = load_text("The Secretary-General's report doesn't cover this.")
    assert "UN-QUO-001" not in ids(checks_style.check_quotations(doc))


def test_small_number_flagged():
    doc = load_text("The Organization received 5 new mandates.")
    assert "UN-NUMW-001" in ids(checks_style.check_numbers(doc))


def test_paragraph_citation_not_flagged():
    doc = load_text("As noted in paragraph 5 of the previous report.")
    assert "UN-NUMW-001" not in ids(checks_style.check_numbers(doc))


def test_ordinal_flagged():
    doc = load_text("This was the 3rd such increase.")
    assert "UN-NUMW-002" in ids(checks_style.check_numbers(doc))


def test_currency_code_flagged():
    doc = load_text("The allocation amounted to USD 250,000 in total.")
    assert "UN-CUR-001" in ids(checks_style.check_currency(doc))


# --- end to end --------------------------------------------------------------

def test_sample_document_end_to_end():
    from pathlib import Path
    sample = Path(__file__).parent.parent / "samples" / "non_compliant_report.txt"
    from app.ingest import load_document
    doc = load_document(sample)
    findings = run_checks(doc)
    s = summarize(findings)
    assert not s["compliant"]
    rids = ids(findings)
    # The sample was built to trip (at least) these rules:
    for expected in ["UN-HDG-001", "UN-HDG-002", "UN-ABB-001", "UN-TERM-001",
                     "UN-SPL-001", "UN-SPL-002", "UN-QUO-001", "UN-NUMW-001",
                     "UN-NUMW-002", "UN-CUR-001", "UN-SUB-001"]:
        assert expected in rids, f"sample should trigger {expected}"


def test_compliant_text_is_clean():
    text = (
        "1. The present report is submitted pursuant to General Assembly "
        "resolution 77/1. The United Nations continued its programme of "
        "work in Viet Nam during the reporting period under review.\n\n"
        "2. The Secretariat received five new mandates, the third such "
        "increase. The total allocation amounted to $250,000 for the year "
        "under review, disbursed in the first quarter as planned there."
    )
    doc = load_text(text)
    findings = [f for f in run_checks(doc) if f.severity.value != "info"]
    assert findings == [], [f.to_dict() for f in findings]
