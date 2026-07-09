# lablab.ai submission form — copy-paste pack

## Project Title
UN DocFormat Agent

## Short Description (elevator pitch)
An AI document-compliance agent that turns raw English drafts into fully
formatted UN Secretariat reports — enforcing the real DGACM/UN Editorial
Manual rules with a deterministic rules engine, then using Gemma on AMD
Instinct (via Fireworks AI) for fixes that need editorial judgement.
Outputs a compliant Word document plus a separate change-log document.

## Long Description
UN and UN-affiliated organizations produce thousands of formal documents a
year under one of the world's strictest editorial standards: the DGACM
Instructions and UN Editorial Manual. Word limits (8,500 for Secretariat
reports), consecutive paragraph numbering, bold sentence-case headings,
UNTERM country names ("Viet Nam", not "Vietnam"), Oxford spelling
("programme", "-ize"), rules about which institutions may ever be
abbreviated — today all checked by hand.

UN DocFormat Agent automates the entire pipeline:

1. **Rules engine (15+ checks, pure Python)** — validates a draft against
   the citable UN standard and reports every violation with rule ID,
   location, and exact fix. No hallucinated rules: docs/UN_RULES.md maps
   every check to its DGACM source.
2. **Deterministic autofix** — mechanical violations (spelling,
   terminology, currency, quotation style, numbers, sub-listing markers,
   renumbering) are fixed without any model, each recorded in a change log.
3. **AI rewrite on AMD** — violations needing editorial judgement go to
   MiniMax M3 running on AMD Instinct GPUs via the Fireworks AI API. The
   model is constrained to fix only the flagged issues; the rules engine
   re-verifies the output. (The client is model-agnostic — one env var
   swaps in any Fireworks-hosted model, including Gemma on a dedicated
   deployment.)
4. **UN-compliant Word output** — 10-pt Times New Roman, US letter, 1"
   margins, bold headings, correct sub-listing indentation — plus a
   SEPARATE change-log .docx for reviewers.

Fully containerized (Docker), 57-test suite, MIT-licensed, live demo
deployed. The architecture extends to other UN document types
(resolutions, briefing notes) by adding rules, not code — and to any
organization with a house style: the same engine could enforce ISO,
EU, or corporate editorial standards.

Note for judges: the live demo is on a free-tier host — first load may
take ~1 minute if the instance is cold.

## Technology Tags
Python, Flask, Docker, Fireworks AI, AMD Instinct, MiniMax, LLM, Agent,
document-processing, RegTech

## Category Tags
AI Agents, Productivity, Document Automation, GovTech

## Public GitHub Repository
https://github.com/oscarowais/un-docformat-agent

## Demo Application URL
https://un-docformat-agent.onrender.com

## Demo Application Platform
Render (Docker container)

## Cover Image
team_cover.png (already generated — AMD/UN design, 1200x675)

## Video Presentation
(record per video_script.md, upload to YouTube unlisted, paste link)

## Slide Presentation
(deck to be generated — slides.pptx)
