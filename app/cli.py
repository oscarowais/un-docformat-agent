"""Command-line interface.

Usage:
    python -m app.cli check <file.txt|file.md|file.docx> [--json]
    python -m app.cli check --text "raw text here" [--json]
    python -m app.cli format <file> [-o out.docx] [--no-fix]

`check`  — run compliance checks, print a text/JSON report.
`format` — apply deterministic autofixes, print the change log, and write a
           UN-formatted .docx (10-pt Times New Roman, US letter, 1" margins).

Exit codes: 0 = compliant / formatted OK, 1 = issues found, 2 = usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # .env must be loaded for --ai (FIREWORKS_* variables)

from app.autofix import autofix  # noqa: E402
from app.ingest import load_document, load_text
from app.output import write_changelog_docx, write_docx
from app.report import to_json, to_text
from app.rules.engine import run_checks, summarize


def _load(args, parser) -> "DocumentModel":  # noqa: F821
    if bool(args.file) == bool(getattr(args, "text", None)):
        parser.error("provide either a file path or --text, not both/neither")
    return load_document(args.file) if args.file else load_text(args.text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="un-docformat",
        description="UN DocFormat Agent — formatting compliance checker "
                    "(Secretariat report rule set)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Run compliance checks")
    p_check.add_argument("file", nargs="?", help="Path to .txt/.md/.docx")
    p_check.add_argument("--text", help="Check a raw text string instead")
    p_check.add_argument("--json", action="store_true",
                         help="Output JSON instead of a text report")

    p_fmt = sub.add_parser("format",
                           help="Autofix + write a UN-formatted .docx")
    p_fmt.add_argument("file", nargs="?", help="Path to .txt/.md/.docx")
    p_fmt.add_argument("--text", help="Format a raw text string instead")
    p_fmt.add_argument("-o", "--output", default="formatted.docx",
                       help="Output .docx path (default: formatted.docx)")
    p_fmt.add_argument("--no-fix", action="store_true",
                       help="Skip autofixes; just apply page/font formatting")
    p_fmt.add_argument("--ai", action="store_true",
                       help="Also run the Fireworks model fix pass "
                            "(requires FIREWORKS_API_KEY/FIREWORKS_MODEL)")

    args = parser.parse_args(argv)

    try:
        doc = _load(args, parser)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.command == "check":
        findings = run_checks(doc)
        print(to_json(doc, findings) if args.json else to_text(doc, findings))
        return 0 if summarize(findings)["compliant"] else 1

    if args.command == "format":
        text = doc.full_text
        change_log: list[str] = []
        if args.ai and not args.no_fix:
            from app.agent import process
            from app.model import FireworksClient
            if not FireworksClient().is_configured:
                print("warning: --ai requested but FIREWORKS_API_KEY / "
                      "FIREWORKS_MODEL are not set — AI pass will be "
                      "skipped (check your .env)", file=sys.stderr)
            result = process(text)
            text = result["text"]
            change_log = (result["autofix_log"]
                          + [f"[AI] {e}" for e in result["model_log"]])
            if result["model_error"]:
                print(f"warning: model pass failed, using autofix only "
                      f"({result['model_error']})", file=sys.stderr)
        elif not args.no_fix:
            text, change_log = autofix(text)

        out = write_docx(text, args.output)
        print(f"Wrote {out} ({len(change_log)} autofix(es) applied)")
        if change_log:
            log_path = Path(args.output).with_name(
                Path(args.output).stem + "_changelog.docx")
            write_changelog_docx(change_log, log_path,
                                 source=args.file or "(pasted text)")
            print(f"Wrote {log_path} (change log, separate document)")
        for entry in change_log:
            print(f"  - {entry}")

        # Re-check the fixed text and report what a model still needs to do.
        remaining = [f for f in run_checks(load_text(text))
                     if f.severity.value != "info"]
        if remaining:
            print(f"\n{len(remaining)} issue(s) remain (need editorial "
                  "judgement — model fix step, Day 3):")
            for f in remaining:
                print(f"  * [{f.severity.value}] {f.rule_id} {f.message}")
        else:
            print("\nNo remaining rule violations after autofix.")
        return 0 if not remaining else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
