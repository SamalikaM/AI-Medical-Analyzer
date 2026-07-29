import csv
import io
import json
import os
from functools import wraps

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                    send_file, session, url_for)
import pytesseract
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from utils import charts, db
from utils.extraction import extract_all, looks_like_medical_report
from utils.file_parser import allowed_file, extract_text
from utils.pdf_report import build_pdf_report
from utils.scoring import (assess_risks, generate_recommendations,
                            generate_summary, health_score)

UPLOAD_DIR = "uploads"
REPORTS_DIR = "reports"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs("instance", exist_ok=True)
db.init_db()


# ---------- auth helpers ----------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if not db.get_user_by_id(session["user_id"]):
            # session refers to a user that no longer exists (e.g. database
            # was reset while this browser was still logged in) -- clear it
            # rather than let a stale user_id hit a foreign-key error later.
            session.clear()
            flash("Your session was out of date -- please log in again.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def _lab_results_to_dicts(lab_results):
    return [r.__dict__ for r in lab_results]


# ---------- public pages ----------

@app.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.", "danger")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("register"))
        if db.get_user_by_email(email):
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("register"))
        user_id = db.create_user(email, generate_password_hash(password))
        session["user_id"] = user_id
        session["email"] = email
        session["is_admin"] = False
        flash("Account created!", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))
        session.permanent = bool(request.form.get("remember"))
        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["is_admin"] = bool(user["is_admin"])
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ---------- dashboard / core app ----------

@app.route("/dashboard")
@login_required
def dashboard():
    reports = db.get_reports_for_user(session["user_id"])
    recent = reports[:5]
    scores = [r["health_score"] for r in reports if r["health_score"] is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else None
    trend_data = [{"created_at": r["created_at"], "health_score": r["health_score"]}
                  for r in reversed(reports) if r["health_score"] is not None]
    total_risks = 0
    for r in reports:
        total_risks += len(json.loads(r["risks"] or "[]"))

    return render_template(
        "dashboard.html",
        recent=recent,
        report_count=len(reports),
        avg_score=avg_score,
        latest_score=reports[0]["health_score"] if reports else None,
        total_risks=total_risks,
        trend_chart=charts.score_trend_line(trend_data),
    )


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Please choose a file.", "danger")
            return redirect(url_for("upload"))
        if not allowed_file(file.filename):
            flash("Unsupported file type. Use PDF, TXT, PNG, or JPEG.", "danger")
            return redirect(url_for("upload"))

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_DIR, f"{session['user_id']}_{filename}")
        file.save(filepath)

        try:
            text = extract_text(filepath)
        except pytesseract.TesseractNotFoundError:
            flash("OCR isn't installed on this server, so image uploads can't be read yet. "
                  "Please upload a PDF or TXT report, or install Tesseract OCR "
                  "(see README) and try again.", "warning")
            return redirect(url_for("upload"))
        if not text.strip():
            flash("Couldn't read any text from that file. If it's a photo or scan, "
                  "try a clearer, well-lit image.", "warning")
            return redirect(url_for("upload"))

        extraction = extract_all(text)
        if not looks_like_medical_report(extraction, text):
            flash("This doesn't look like a medical lab report -- no recognizable "
                  "patient info or lab values were found. Please upload a valid report.", "danger")
            return redirect(url_for("upload"))

        lab_dicts = _lab_results_to_dicts(extraction.lab_results)
        score = health_score(extraction.lab_results)
        risks = assess_risks(extraction.lab_results)
        summary = generate_summary(extraction.lab_results, score)

        report_id = db.save_report(
            session["user_id"], filename, extraction.patient_info,
            lab_dicts, score, risks, summary,
        )
        return redirect(url_for("view_report", report_id=report_id))

    return render_template("upload.html")


@app.route("/report/<int:report_id>")
@login_required
def view_report(report_id):
    report = db.get_report(report_id, session["user_id"])
    if not report:
        flash("Report not found.", "danger")
        return redirect(url_for("history"))

    lab_results = json.loads(report["lab_results"])
    risks = json.loads(report["risks"])
    patient_info = json.loads(report["patient_info"])
    recommendations = generate_recommendations(
        [type("R", (), r) for r in lab_results]  # lightweight attr-access shim
    )

    return render_template(
        "report.html",
        report=report,
        patient_info=patient_info,
        lab_results=lab_results,
        risks=risks,
        recommendations=recommendations,
        bar_chart=charts.lab_values_bar(lab_results),
        pie_chart=charts.flag_distribution_pie(lab_results),
        radar_chart=charts.risk_radar(risks),
        gauge_chart=charts.health_score_gauge(report["health_score"]),
    )


@app.route("/history")
@login_required
def history():
    search = request.args.get("q", "").strip()
    reports = db.get_reports_for_user(session["user_id"], search or None)
    return render_template("history.html", reports=reports, search=search)


@app.route("/report/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_report(report_id):
    db.delete_report(report_id, session["user_id"])
    flash("Report deleted.", "success")
    return redirect(url_for("history"))


@app.route("/compare")
@login_required
def compare():
    ids = request.args.getlist("id")
    if len(ids) != 2:
        reports = db.get_reports_for_user(session["user_id"])
        return render_template("compare_select.html", reports=reports)

    r1 = db.get_report(int(ids[0]), session["user_id"])
    r2 = db.get_report(int(ids[1]), session["user_id"])
    if not r1 or not r2:
        flash("One or both reports not found.", "danger")
        return redirect(url_for("compare"))

    # order oldest -> newest for a clear "before/after"
    if r1["created_at"] > r2["created_at"]:
        r1, r2 = r2, r1

    l1 = {v["test"]: v for v in json.loads(r1["lab_results"])}
    l2 = {v["test"]: v for v in json.loads(r2["lab_results"])}
    comparisons = []
    for test in sorted(set(l1) | set(l2)):
        v1, v2 = l1.get(test), l2.get(test)
        if v1 and v2:
            pct = round(((v2["value"] - v1["value"]) / v1["value"]) * 100, 1) if v1["value"] else 0
            comparisons.append({
                "label": v2["label"], "before": v1["value"], "after": v2["value"],
                "unit": v2["unit"], "pct_change": pct,
                "improved": v2["flag"] == "normal" and v1["flag"] != "normal",
                "worsened": v1["flag"] == "normal" and v2["flag"] != "normal",
            })
    return render_template("compare.html", r1=r1, r2=r2, comparisons=comparisons)


# ---------- exports ----------

@app.route("/report/<int:report_id>/export/pdf")
@login_required
def export_pdf(report_id):
    report = db.get_report(report_id, session["user_id"])
    if not report:
        flash("Report not found.", "danger")
        return redirect(url_for("history"))
    lab_results = json.loads(report["lab_results"])
    risks = json.loads(report["risks"])
    patient_info = json.loads(report["patient_info"])
    recommendations = generate_recommendations([type("R", (), r) for r in lab_results])
    out_path = os.path.join(REPORTS_DIR, f"report_{report_id}.pdf")
    build_pdf_report(out_path, patient_info, lab_results, report["health_score"],
                      risks, report["summary"], recommendations)
    return send_file(out_path, as_attachment=True, download_name=f"health_report_{report_id}.pdf")


@app.route("/report/<int:report_id>/export/csv")
@login_required
def export_csv(report_id):
    report = db.get_report(report_id, session["user_id"])
    if not report:
        flash("Report not found.", "danger")
        return redirect(url_for("history"))
    lab_results = json.loads(report["lab_results"])
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Test", "Value", "Unit", "Low", "High", "Flag"])
    for r in lab_results:
        writer.writerow([r["label"], r["value"], r["unit"], r["low"], r["high"], r["flag"]])
    mem = io.BytesIO(buf.getvalue().encode("utf-8"))
    return send_file(mem, as_attachment=True, download_name=f"report_{report_id}.csv", mimetype="text/csv")


# ---------- admin ----------

@app.route("/admin")
@admin_required
def admin_panel():
    users = db.all_users()
    reports = db.all_reports()
    return render_template("admin.html", users=users, reports=reports)


@app.route("/admin/report/<int:report_id>/delete", methods=["POST"])
@admin_required
def admin_delete(report_id):
    db.admin_delete_report(report_id)
    flash("Report deleted by admin.", "success")
    return redirect(url_for("admin_panel"))


# ---------- api (used by dashboard JS for polling / live updates) ----------

@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
