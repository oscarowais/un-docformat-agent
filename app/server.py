"""Flask UI — single page: paste/upload → compliance report → formatted .docx.

Endpoints:
    GET  /        UI
    POST /check   findings JSON (rules engine only, no model)
    POST /format  autofix + UN-formatted .docx download (deterministic)
    POST /fix     AI rewrite — disabled until Fireworks is configured (Day 2+)

Run locally:  python -m app.server   (or via Docker, see Dockerfile)
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file

from app.autofix import autofix
from app.ingest import load_document, load_text
from app.model import FireworksClient
from app.output import write_changelog_docx, write_docx
from app.report import sort_findings
from app.rules.engine import run_checks, summarize

load_dotenv()

app = Flask(__name__,
            template_folder=str(Path(__file__).parent.parent / "webui"))

ALLOWED_SUFFIXES = {".txt", ".md", ".docx"}
MAX_UPLOAD_MB = 5
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def _doc_from_request():
    """Shared input handling for /check and /format. Returns (doc, error)."""
    upload = request.files.get("file")
    text = (request.form.get("text") or "").strip()
    if upload and upload.filename:
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            return None, (f"Unsupported file type {suffix}; "
                          "use .txt, .md or .docx")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            upload.save(tmp.name)
            doc = load_document(tmp.name)
        doc.source_path = upload.filename  # show original name, not tmp
        return doc, None
    if text:
        return load_text(text), None
    return None, "Paste some text or upload a file."


@app.get("/")
def index():
    from app import __build__
    return render_template("index.html",
                           model_ready=FireworksClient().is_configured,
                           build=__build__)


@app.post("/check")
def check():
    doc, err = _doc_from_request()
    if err:
        return {"error": err}, 400
    findings = run_checks(doc)
    return {
        "source": doc.source_path or "(pasted text)",
        # extracted text so the UI can show exactly what was checked
        # (critical for uploaded files — the editor mirrors the document)
        "text": doc.full_text,
        "word_count": doc.word_count(),
        "summary": summarize(findings),
        "findings": [f.to_dict() for f in sort_findings(findings)],
    }


@app.post("/format")
def format_docx():
    """Deterministic autofix + download package.

    Returns JSON (not a raw file) so the UI can BOTH offer the zip download
    and mirror the formatted text into the editor: the zip (formatted .docx
    + change-log .docx — always both) travels base64-encoded.
    """
    import base64

    doc, err = _doc_from_request()
    if err:
        return {"error": err}, 400
    original = doc.full_text
    fixed, change_log = autofix(original)

    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "un_formatted.docx"
        write_docx(fixed, doc_path)
        # ALWAYS include the change log — an explicit "0 changes" document
        # beats a silently missing file.
        log_path = Path(tmpdir) / "change_log.docx"
        write_changelog_docx(
            change_log or ["No changes required — the document already "
                           "satisfied all mechanical rules."],
            log_path, source=doc.source_path or "(pasted text)")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in (doc_path, log_path):
                z.write(f, arcname=f.name)

    return {
        "text": fixed,
        "original_text": original,
        "autofix_log": change_log,
        "source": doc.source_path or "(pasted text)",
        "word_count": len(fixed.split()),
        "filename": "un_formatted_package.zip",
        "zip_base64": base64.b64encode(buf.getvalue()).decode("ascii"),
    }


@app.post("/fix")
def fix():
    """Full agent pipeline: autofix + Fireworks model fix + final re-check."""
    client = FireworksClient()
    if not client.is_configured:
        return {"error": "AI rewrite is not available yet — Fireworks "
                         "credentials pending. Deterministic formatting "
                         "still works via Format & download."}, 503
    doc, err = _doc_from_request()
    if err:
        return {"error": err}, 400
    from app.agent import process
    result = process(doc.full_text, client=client)
    # Fields the shared UI renderer expects alongside the pipeline output:
    result["source"] = doc.source_path or "(pasted text)"
    result["word_count"] = len(result["text"].split())
    # Pre-pipeline text so the UI's "Restore source" works for uploads too.
    result["original_text"] = doc.full_text
    return result


if __name__ == "__main__":
    # 0.0.0.0 so the containerized app is reachable; debug off by default.
    # PORT env respected so free hosts (Render/HF Spaces/etc.) can inject it.
    import os as _os
    app.run(host="0.0.0.0", port=int(_os.environ.get("PORT", 8000)))
