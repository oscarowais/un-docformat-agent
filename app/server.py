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
    return render_template("index.html",
                           model_ready=FireworksClient().is_configured)


@app.post("/check")
def check():
    doc, err = _doc_from_request()
    if err:
        return {"error": err}, 400
    findings = run_checks(doc)
    return {
        "source": doc.source_path or "(pasted text)",
        "word_count": doc.word_count(),
        "summary": summarize(findings),
        "findings": [f.to_dict() for f in sort_findings(findings)],
    }


@app.post("/format")
def format_docx():
    """Deterministic autofix + download. The formatted document and the
    change log are SEPARATE .docx files, delivered together as a zip
    (a single HTTP response can't carry two attachments)."""
    doc, err = _doc_from_request()
    if err:
        return {"error": err}, 400
    fixed, change_log = autofix(doc.full_text)

    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "un_formatted.docx"
        write_docx(fixed, doc_path)
        files = [doc_path]
        if change_log:
            log_path = Path(tmpdir) / "change_log.docx"
            write_changelog_docx(change_log, log_path,
                                 source=doc.source_path or "(pasted text)")
            files.append(log_path)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, arcname=f.name)
        buf.seek(0)

    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="un_formatted_package.zip",
    )


@app.post("/fix")
def fix():
    """AI rewrite endpoint — disabled until Fireworks is configured (Day 2+)."""
    client = FireworksClient()
    if not client.is_configured:
        return {"error": "AI fix is not available yet — Fireworks credentials "
                         "pending (hackathon credits land Day 2)."}, 503
    return {"error": "Not implemented yet (Day 3 milestone)."}, 501


if __name__ == "__main__":
    # 0.0.0.0 so the containerized app is reachable; debug off by default.
    app.run(host="0.0.0.0", port=8000)
