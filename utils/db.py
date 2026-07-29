"""
Thin sqlite3 wrapper. No SQLAlchemy: three tables, straightforward
queries -- an ORM here would be a dependency added to save typing four
SQL strings.
"""
import json
import sqlite3
from datetime import datetime, timezone

DB_PATH = "instance/app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    patient_info TEXT,     -- JSON
    lab_results TEXT,      -- JSON
    health_score INTEGER,
    risks TEXT,            -- JSON
    summary TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def create_user(email: str, password_hash: str) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
        (email, password_hash, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def save_report(user_id, filename, patient_info, lab_results, score, risks, summary) -> int:
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO reports
           (user_id, filename, patient_info, lab_results, health_score, risks, summary, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, filename, json.dumps(patient_info), json.dumps(lab_results),
         score, json.dumps(risks), summary, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    report_id = cur.lastrowid
    conn.close()
    return report_id


def get_reports_for_user(user_id, search: str = None):
    conn = get_db()
    if search:
        like = f"%{search}%"
        rows = conn.execute(
            """SELECT * FROM reports WHERE user_id = ?
               AND (filename LIKE ? OR patient_info LIKE ? OR summary LIKE ?)
               ORDER BY created_at DESC""",
            (user_id, like, like, like),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    conn.close()
    return rows


def get_report(report_id, user_id=None):
    conn = get_db()
    if user_id is not None:
        row = conn.execute(
            "SELECT * FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id)
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    return row


def delete_report(report_id, user_id) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def all_users():
    conn = get_db()
    rows = conn.execute("SELECT id, email, is_admin, created_at FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def all_reports():
    conn = get_db()
    rows = conn.execute(
        """SELECT reports.*, users.email FROM reports
           JOIN users ON users.id = reports.user_id
           ORDER BY reports.created_at DESC"""
    ).fetchall()
    conn.close()
    return rows


def admin_delete_report(report_id) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
