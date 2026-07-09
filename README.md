---
title: UN DocFormat Agent
emoji: 🇺🇳
colorFrom: red
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# UN DocFormat Agent

Formatting and compliance agent for UN-style documentation, built for the
**AMD Developer Hackathon: ACT II — Track 3 (Unicorn Track)**, July 2026.

Paste or upload a raw English draft; the agent checks it against the real
UN editorial rule set (DGACM / UN Editorial Manual) for **Secretariat
reports** — word limits, paragraph numbering, heading style, terminology
(UNTERM country names, abbreviation rules), Oxford spelling, quotation
style, numbers/currency conventions — and reports every violation with a
concrete fix. Model-assisted rewriting and Q&A (Fireworks AI on AMD) land
in later milestones.

## Status (Day 1 milestone)

- ✅ Rules engine — 15+ rule checks, pure Python, no model needed (`app/rules/`)
- ✅ Ingestion — .txt / .md / .docx → normalized document model (`app/ingest/`)
- ✅ Deterministic autofix — mechanical fixes + change log, no model needed (`app/autofix.py`)
- ✅ UN-formatted .docx output — 10-pt Times New Roman, US letter, 1" margins,
  bold headings, plus a SEPARATE change-log .docx (`app/output/`, stdlib OOXML writer)
- ✅ CLI — `python -m app.cli check <file>` and `format <file> -o out.docx`
- ✅ Web UI — paste/upload → compliance report + "Format & download .docx" (`app/server.py`, `webui/`)
- ✅ Dockerfile
- ✅ Fireworks AI integration — full client + agent pipeline (`app/model/`,
  `app/agent.py`), mock-tested end to end; goes live the moment
  FIREWORKS_API_KEY/FIREWORKS_MODEL are set in .env (no code changes)
- ✅ Agent pipeline — autofix → rules re-check → model fix (only remaining
  violations) → final verification, with graceful degradation if the model
  is unavailable. CLI: `format --ai`; UI: "AI rewrite" button; API: `/fix`
- ⏳ Q&A over compiled docs — client method ready (`answer_question`),
  UI wiring Day 4

## Quick start

```bash
pip install -r requirements.txt

# CLI — check the bundled non-compliant sample
python -m app.cli check samples/non_compliant_report.txt
python -m app.cli check samples/non_compliant_report.txt --json

# CLI — autofix + write a UN-formatted Word file (with change-log annex)
python -m app.cli format samples/non_compliant_report.txt -o formatted.docx

# Web UI — http://localhost:8000
python -m app.server

# Tests
pytest
```

## Docker

```bash
docker build -t un-docformat-agent .
docker run -p 8000:8000 un-docformat-agent
# with Fireworks credentials (Day 2+): docker run -p 8000:8000 --env-file .env un-docformat-agent
```

## Configuration

Copy `.env.example` to `.env` and set `FIREWORKS_API_KEY` / `FIREWORKS_MODEL`
(demo uses `accounts/fireworks/models/minimax-m3`, serverless on AMD
Instinct). Without credentials the app runs in rules-engine-only mode; the
"AI rewrite" action stays disabled.

The client is model-agnostic: any OpenAI-compatible endpoint works via
`FIREWORKS_MODEL`/`FIREWORKS_BASE_URL` — including Google's Gemma family on
a Fireworks dedicated deployment, with zero code changes.

## Project layout

```
app/
  document.py        # normalized DocumentModel shared by all layers
  ingest/loaders.py  # .txt/.md/.docx -> DocumentModel (incl. docx page metadata)
  rules/             # rules engine: engine.py + checks_* modules + vocab.py
  autofix.py         # deterministic mechanical fixes + change log
  output/            # UN-compliant .docx writer (stdlib OOXML)
  model/             # Fireworks AI client (stub until credits land)
  report.py          # text/JSON report rendering
  cli.py             # command-line interface (check / format)
  server.py          # Flask app (single-page UI)
webui/index.html     # UI
samples/             # deliberately non-compliant demo input
docs/UN_RULES.md     # rule set ↔ check mapping (ground-truth spec)
tests/               # pytest suite
```

## Rule set

See [docs/UN_RULES.md](docs/UN_RULES.md) for the full rule ↔ check mapping.
Sources: UN Editorial Manual Online and DGACM Instructions for the
Preparation of Official Documents. Demo scope is one document type
(Secretariat report) per the project brief.
