# VitalScan AI — Health Report Analyzer

An AI-assisted web app that reads uploaded lab reports (PDF/TXT), extracts lab values and patient info, flags abnormal results against clinical reference ranges, computes an educational health score, estimates risk levels for common conditions, and generates a downloadable PDF summary.

**This is an educational tool only. It is not a medical diagnosis. Always consult a licensed healthcare professional about your results.**

## Features

- Marketing landing page (hero, features, how-it-works, testimonials, FAQ)
- Email/password auth with hashed passwords and remember-me sessions
- Drag-and-drop upload with progress bar (PDF, TXT, PNG, JPEG)
- OCR fallback (Tesseract) for scanned or photographed reports — any PDF page or image with no usable text layer is automatically rasterized and OCR'd
- Invalid-document detection — uploads with no recognizable lab values or patient info are rejected with a clear message instead of silently saving an empty report
- Regex-based extraction of patient info + up to 24 lab markers (extensible — see below)
- Abnormal-value flagging (normal / low / high / critical) against reference ranges
- Weighted 0–100 health score across blood, kidney, liver, cholesterol, diabetes, vitamin, electrolyte, thyroid categories
- Educational risk levels (confidence-scored, not diagnostic) for 8 common conditions
- Plain-language AI summary + lifestyle recommendations (never prescribes medication)
- Interactive Plotly charts: bar, pie, radar, gauge, trend line
- Report history with search, delete, and side-by-side comparison (% change, improved/worsened)
- PDF and CSV export
- Admin panel (users, all reports, delete)
- Dark mode toggle, responsive layout, toast notifications, skeleton-ready loading states

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Flask | Small surface area, no need for a bigger framework here |
| Extraction | Python `re` (stdlib) | Lab reports are semi-tabular; regex against a reference table beats an NLP model for this |
| PDF reading | pdfplumber | Reliable text extraction from tabular PDF reports |
| PDF generation | reportlab | Full control over the exported report layout |
| Charts | Plotly | Interactive, and the spec's requested chart types map directly onto its API |
| Database | SQLite via stdlib `sqlite3` | Three tables, simple queries — no ORM overhead needed |
| Frontend | Bootstrap 5 + vanilla JS | No build step, ships fast, fully responsive |

**Deliberately not used (see "Known limitations / roadmap" below):** spaCy, Sentence Transformers, scikit-learn clustering/anomaly models. Each was evaluated and skipped for this version because a simpler approach covers the same requirement without the extra runtime weight or install complexity — details below.

## Project structure

```
medreport/
├── app.py                  # Flask routes
├── models/
│   └── lab_reference.py    # Single source of truth: test names, aliases, ranges, category weights
├── utils/
│   ├── extraction.py       # Text -> patient info + lab values
│   ├── scoring.py          # Lab values -> health score, risks, summary, recommendations
│   ├── charts.py           # Plotly figure builders
│   ├── pdf_report.py       # Downloadable PDF report builder
│   ├── file_parser.py      # Upload -> raw text (PDF/TXT; image OCR stubbed)
│   ├── db.py                # SQLite data access
│   └── test_core_logic.py  # Runnable self-check for extraction + scoring
├── templates/               # Jinja2 templates (landing, auth, dashboard, upload, report, history, compare, admin)
├── static/
│   ├── css/style.css        # Design tokens + components (light/dark)
│   └── js/main.js           # Dark mode toggle, dropzone upload
├── uploads/                  # Uploaded report files (gitignored)
├── reports/                  # Generated PDF exports (gitignored)
├── instance/                 # SQLite database file (gitignored)
├── requirements.txt
├── render.yaml               # Render deployment config
└── .env.example
```

## Architecture

```
Browser
  │  upload (PDF/TXT)
  ▼
Flask route /upload
  │
  ├─► file_parser.extract_text()      → raw text
  ├─► extraction.extract_all()        → patient info + LabResult[]   (models/lab_reference.py)
  ├─► scoring.health_score()          → 0-100 score
  ├─► scoring.assess_risks()          → risk levels per condition
  ├─► scoring.generate_summary()      → plain-language text
  └─► db.save_report()                → persisted to SQLite
        │
        ▼
  /report/<id>  ──► charts.py (Plotly)      → interactive dashboard view
              └───► pdf_report.py (reportlab) → downloadable PDF
```

## Adding a new lab test

Add one entry to `LAB_TESTS` in `models/lab_reference.py`:

```python
"ferritin": {
    "aliases": [r"ferritin"],
    "unit": "ng/mL", "low": 20, "high": 250,
    "critical_low": 10, "category": "blood",
},
```

Nothing else needs to change — extraction, flagging, scoring, and every template read from this table.

## Installation

OCR needs the **Tesseract** system binary installed separately from the Python packages (`pytesseract` is just a wrapper around it):

- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki, then add the install folder to your PATH

```bash
git clone <your-repo-url>
cd medreport
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then fill in SECRET_KEY
python app.py
```

Visit `http://localhost:5000`. The SQLite database is created automatically on first run.

To become an admin, sign up normally, then run:

```bash
python -c "from utils import db; conn = db.get_db(); conn.execute(\"UPDATE users SET is_admin = 1 WHERE email = 'you@example.com'\"); conn.commit()"
```

## Running the self-check

```bash
python utils/test_core_logic.py
```

This exercises extraction (patient info + lab values), flagging, health scoring, risk assessment, and summary generation against a sample report — it's the one test file the core logic depends on.

## Deploying to Render

This project deploys as a **Docker** web service (not Render's native Python runtime) — OCR needs the Tesseract system binary, which the `Dockerfile` installs; Render's native Python environment can't install system packages.

1. Push this repo to GitHub.
2. In Render, **New +** → **Blueprint**, point it at the repo (it will read `render.yaml` and `Dockerfile` automatically). Or set up manually:
   - **Environment:** Docker, `dockerfilePath: ./Dockerfile`
   - **Environment variable:** `SECRET_KEY` (generate one, don't reuse the dev default)
3. Deploy. First boot creates the SQLite file under `instance/`.

**Known limitations:**
- Render's free-tier filesystem is ephemeral — the SQLite DB and uploaded files reset on redeploy or after long idle periods. Fine for a portfolio demo; for anything persistent, swap in Render's managed Postgres (would mean changing `utils/db.py`'s connection function, not the rest of the app).
- OCR accuracy: Tesseract is trained on printed/typed text. It reads scanned or photographed *printed* reports reliably; true handwritten (cursive) values are not reliably recognized by any Tesseract configuration. If a report comes back with missing values, check whether the source was actually handwritten.

## API endpoints (internal)

All routes render HTML except:

| Route | Method | Returns |
|---|---|---|
| `/api/health` | GET | `{"status": "ok"}` — liveness check |
| `/report/<id>/export/pdf` | GET | `application/pdf` file download |
| `/report/<id>/export/csv` | GET | `text/csv` file download |

There is no public JSON API in this version — every other route is a server-rendered page guarded by session-based login.

## Known limitations / roadmap (phase 2)

These were scoped out of v1 deliberately, not overlooked — each has a clear, isolated upgrade path so adding it later doesn't touch the rest of the app:

- **Handwriting recognition:** Tesseract (used for OCR) is a printed-text engine — it does not reliably read handwritten/cursive values. A dedicated handwriting model (typically a cloud API) would need to be added as a second OCR pass in `utils/file_parser.py`; out of scope here since it requires a paid external service.
- **NLP-based extraction (spaCy/embeddings):** the current regex table handles standard lab report formats well; if real-world reports have inconsistent layouts often enough to matter, swap `extract_patient_info()` in `utils/extraction.py` for a trained NER pass — `extract_lab_values()` doesn't need to change.
- **ML risk model (clustering / isolation forest):** risk levels are currently rule-based against reference ranges, which is transparent and explainable for an educational tool. A trained model needs labeled outcome data to be more than decoration; once available, it's a drop-in replacement for `scoring.assess_risks()`.
- **CSV/Excel bulk export, admin analytics charts:** straightforward additions once the above are prioritized.

## Disclaimer

This application is provided for educational and portfolio demonstration purposes only. It does not provide medical advice, diagnosis, or treatment. Extracted values, health scores, and risk estimates are generated by simple rule-based logic, not clinical algorithms. Always seek the advice of a physician or other qualified health provider with any questions regarding a medical condition.
