# UN Formatting Rule Set (ground truth for the demo)

Source: UN Editorial Manual Online / DGACM Instructions for the Preparation
of Official Documents (per project brief, Section 5 — re-verified against
UN DGACM sources as of July 3, 2026). Target document type: **Secretariat
report** (clearest documented rule set).

| Rule ID | Rule | Engine check | Severity |
|---|---|---|---|
| UN-LEN-001/002 | Secretariat reports max 8,500 words (incl. footnotes, headings, hidden text); 10,700 for non-Secretariat; waiver to exceed | `checks_length.check_word_count` | error / warning |
| UN-FMT-001/002 | Microsoft Word, 10-pt Times New Roman | `checks_docx.check_font` (docx only) | error |
| UN-PAGE-001/002 | US letter (8.5"×11"), standard 1" margins | `checks_docx.check_page_setup` (docx only) | error / warning |
| UN-NOTE-001 | Footnotes only, never endnotes | `checks_docx.check_notes` (docx only) | error |
| UN-HDG-001/002/003 | Headings bold, sentence case (no Title Case / block caps) | `checks_structure.check_headings` | warning |
| UN-NUM-001/002/003 | Body paragraphs numbered consecutively; paragraph numbers (not pages) cited | `checks_structure.check_paragraph_numbering` | error / warning |
| UN-SUB-001/002 | Sub-listings (a), (b)…; nested (i), (ii)… indented | `checks_structure.check_sublistings` | warning / info |
| UN-ABB-001 | "United Nations", "General Assembly" etc. never abbreviated in running text | `checks_terminology.check_abbreviations` | error |
| UN-ABB-002/003 | Abbreviations spelled out in full on first occurrence | `checks_terminology.check_abbreviations` | warning / info |
| UN-TERM-001 | Country names per UNTERM ("Viet Nam", "Republic of Korea", …) | `checks_terminology.check_country_names` | error |
| UN-SPL-001 | Concise Oxford spelling, first-listed form ("programme", "judgement") | `checks_style.check_spelling` | warning |
| UN-SPL-002 | -ize preferred over -ise | `checks_style.check_spelling` | warning |
| UN-QUO-001 | Quotations in double quotation marks | `checks_style.check_quotations` | warning |
| UN-NUMW-001/002 | Numbers under 10 in words; ordinals first–ninety-ninth in words | `checks_style.check_numbers` | warning |
| UN-CUR-001/002 | Currency symbols ($, €, SwF), country prefix for non-US dollars (Can$50) | `checks_style.check_currency` | warning / info |

Notes for the model layer (Day 3): findings are emitted as structured JSON
(`Finding.to_dict()`), designed to be passed to the Fireworks model together
with the source text so the model fixes *only* flagged issues and produces a
change log entry per fix.
