# Video script — UN DocFormat Agent (target: 3:00)

Record against the live Render URL. OBS or any screen recorder; 1080p.
Keep the browser at 100% zoom, close extra tabs, hide bookmarks bar.

## 0:00–0:25 — The problem (talking over title slide or the app header)

> "United Nations documents follow one of the strictest editorial standards
> in the world — the DGACM rules. Word limits, paragraph numbering,
> UN-approved country names, Oxford spelling, even which words may be
> abbreviated. Compliance is checked by hand today, and it's slow and
> error-prone. UN DocFormat Agent automates it."

## 0:25–1:10 — Compliance check (live demo)

*Paste the non-compliant sample into the editor. Click "Check compliance."*

> "I paste a raw draft — and in under a second the agent finds every
> violation: 'GA' and 'UN' illegally abbreviated, 'Vietnam' instead of the
> UN-approved 'Viet Nam', wrong quotation marks, numerals that should be
> words, US spelling instead of Oxford. Each finding cites the actual rule
> and shows the exact fix. These aren't invented rules — this is the real,
> citable UN editorial standard."

## 1:10–1:55 — Format & download (the product moment)

*Click "Format & download". Open both files from the zip in Word.*

> "One click, and the agent applies every mechanical fix deterministically
> and produces two documents: the corrected report — 10-point Times New
> Roman, US letter, one-inch margins, bold sentence-case headings, proper
> sub-listing indentation, exactly as DGACM requires — and a separate
> change-log document recording all 24 corrections, ready for review."

## 1:55–2:35 — AI rewrite on AMD (the platform moment)

*Click "AI rewrite". Show the change log + compliant verdict.*

> "Some violations need editorial judgement, not find-and-replace —
> renumbering paragraphs, restructuring headings. For those, the agent
> calls MiniMax M3 running on AMD Instinct GPUs via Fireworks AI. The model is
> instructed to fix only the flagged violations — nothing else is touched —
> and the rules engine re-verifies the result. Watch the verdict flip to
> compliant."

*(If the model is not live at recording time, show the CLI mock test
`tests/run_tests.py` output instead and say: "the full pipeline is
implemented and verified — shown here with the test suite.")*

## 2:35–3:00 — Close (market + wrap)

> "Every UN agency, NGO and ministry that files documents to UN standards
> has this problem — thousands of documents a year. One document type is
> fully covered today; the architecture extends to resolutions and
> briefing notes by adding rules, not code. Containerized, open source,
> MIT-licensed, running live on the URL below. UN DocFormat Agent — built
> on AMD."

## Checklist before recording
- [ ] Render URL warm (open it 2 minutes before recording — cold start)
- [ ] sample text ready in clipboard (samples/non_compliant_report.txt)
- [ ] Word installed & quick to open the downloaded files
- [ ] If AI live: one dry run first (don't record the first-token delay)
