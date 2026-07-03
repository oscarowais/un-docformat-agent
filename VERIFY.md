# Local Verification Checklist (Day 1 build)

Run from the `output/` folder (repo root). Windows PowerShell assumed;
commands are identical on Linux/macOS unless noted.

## 1. Environment

```powershell
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Expected: flask, python-docx, python-dotenv, pytest install cleanly.

## 2. Test suite

```powershell
pytest -q
```

Expected: **42 passed**, 0 failed.
(Fallback without pytest: `python tests/run_tests.py` → "42 passed, 0 failed")

## 3. CLI — compliance check

```powershell
python -m app.cli check samples/non_compliant_report.txt
```

Expected: report ends **NOT COMPLIANT** with **6 errors, 17 warnings**
(GA/UN abbreviations, numbering gaps, Vietnam/South Korea, plus spelling,
quotes, ordinals, currency warnings). Exit code 1 (`echo $LASTEXITCODE` → 1).

```powershell
python -m app.cli check samples/non_compliant_report.txt --json
```

Expected: valid JSON with `summary` + `findings` array.

## 4. CLI — format + docx output

```powershell
python -m app.cli format samples/non_compliant_report.txt -o formatted.docx
```

Expected: "**24 autofix(es) applied**", TWO files written
(`formatted.docx` + `formatted_changelog.docx`), change log printed, then
"1 issue(s) remain" (unnumbered body paragraphs — left for the model step).

**Open `formatted.docx` in Word and verify:**
- [ ] Font is Times New Roman 10 pt throughout
- [ ] Page size Letter, margins 1" (Layout tab)
- [ ] Headings bold, sentence case ("I. Introduction and background")
- [ ] Body text contains "United Nations", "Viet Nam", "$250,000", "five", "third"
- [ ] Sub-listings properly indented: (a)/(b) at 0.5", (i) deeper at 1"
      (real Word indentation — cursor in the line, check the ruler)
- [ ] NO change log inside the document itself

**Open `formatted_changelog.docx` and verify:**
- [ ] Separate document titled "Change log — UN DocFormat Agent"
- [ ] Source file + date line, then all 24 numbered changes

## 5. CLI — clean input control

```powershell
python -m app.cli check --text "1. The United Nations continued its programme of work in Viet Nam during the reporting period under review."
```

Expected: **COMPLIANT**, exit code 0.

## 6. Web UI

```powershell
python -m app.server
```

Then at http://localhost:8000 :
- [ ] Page loads; "Fix with AI (pending credits)" button is greyed out
- [ ] Paste the sample text → "Check compliance" → 6 errors / 17 warnings shown
- [ ] "Format & download .docx" downloads `un_formatted_package.zip`
      containing `un_formatted.docx` + `change_log.docx`; both open in Word
- [ ] Upload `samples/non_compliant_report.txt` as a file → same results
- [ ] (optional) Upload any real .docx → font/page-size/margin checks appear

## 7. Docker (submission hard requirement)

```powershell
docker build -t un-docformat-agent .
docker run -p 8000:8000 un-docformat-agent
```

Expected: builds cleanly; http://localhost:8000 behaves exactly as step 6.

## 8. Repo hygiene (before pushing to GitHub)

```powershell
git init
git add .
git status        # confirm .env NOT listed (only .env.example)
git commit -m "Day 1: rules engine, autofix, docx output, UI, Docker"
```

- [ ] No `.env`, no `__pycache__`, no credentials anywhere in the commit

## If anything fails

Note the step number and exact output, and report back — per the fallback
guideline, catching a failure now (Checkpoint 1 is end of Day 2) is cheap;
catching it on Day 5 is not.
