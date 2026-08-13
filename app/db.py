"""
SQLite storage. The DB file lives at data/leads.db and is committed back to
the repo by the GitHub Actions workflow after each run, so it persists across
runs without needing a hosted database.
"""
import sqlite3
import json
import os
from contextlib import contextmanager
from datetime import datetime

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT NOT NULL,
    niche TEXT NOT NULL,
    location TEXT NOT NULL,
    website_url TEXT,
    quality_score INTEGER,
    scraped_data TEXT,          -- JSON blob
    enhanced_site_url TEXT,
    contact_email TEXT,
    outreach_method TEXT,       -- 'email' | 'contact_form' | 'none'
    outreach_status TEXT DEFAULT 'pending',  -- pending -> contacted -> replied / opted_out / failed
    outreach_date TEXT,
    response_status TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(business_name, location)
);

CREATE TABLE IF NOT EXISTS outreach_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    message_body TEXT,
    sent_at TEXT,
    status TEXT,               -- 'sent' | 'failed' | 'manual_review'
    error_message TEXT,
    FOREIGN KEY(prospect_id) REFERENCES prospect(id)
);

CREATE TABLE IF NOT EXISTS generated_site (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    html_content TEXT NOT NULL,
    public_url TEXT,
    generated_at TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    FOREIGN KEY(prospect_id) REFERENCES prospect(id)
);

CREATE TABLE IF NOT EXISTS opt_out (
    email TEXT PRIMARY KEY,
    requested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_state (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def is_duplicate(business_name: str, location: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM prospect WHERE business_name = ? AND location = ?",
            (business_name, location),
        ).fetchone()
        return row is not None


def is_opted_out(email: str) -> bool:
    if not email:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT email FROM opt_out WHERE email = ?", (email,)).fetchone()
        return row is not None


def record_opt_out(email: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO opt_out (email, requested_at) VALUES (?, ?)",
            (email, datetime.utcnow().isoformat()),
        )


def insert_prospect(business_name, niche, location, website_url, quality_score, scraped_data) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO prospect
               (business_name, niche, location, website_url, quality_score, scraped_data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (business_name, niche, location, website_url, quality_score,
             json.dumps(scraped_data), datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def update_prospect(prospect_id: int, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE prospect SET {cols} WHERE id = ?", (*fields.values(), prospect_id))


def insert_generated_site(prospect_id: int, html_content: str, public_url: str, version: int = 1):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO generated_site (prospect_id, html_content, public_url, generated_at, version)
               VALUES (?, ?, ?, ?, ?)""",
            (prospect_id, html_content, public_url, datetime.utcnow().isoformat(), version),
        )


def insert_outreach_log(prospect_id: int, method: str, message_body: str, status: str, error_message: str = None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO outreach_log (prospect_id, method, message_body, sent_at, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (prospect_id, method, message_body, datetime.utcnow().isoformat(), status, error_message),
        )


def prospects_contacted_today() -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) c FROM prospect WHERE outreach_status = 'contacted' "
            "AND date(outreach_date) = date('now')"
        ).fetchone()
        return row["c"]


def get_next_location(locations: list) -> str:
    """Cycles through `locations` one per call, remembering position in the
    DB so consecutive runs (even in fresh CI containers) pick up where the
    last run left off, and wrap back to the start after the last city."""
    if not locations:
        raise ValueError("No target locations configured")
    if len(locations) == 1:
        return locations[0]

    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM pipeline_state WHERE key = 'last_location_index'"
        ).fetchone()
        last_index = int(row["value"]) if row else -1
        next_index = (last_index + 1) % len(locations)
        conn.execute(
            "INSERT INTO pipeline_state (key, value) VALUES ('last_location_index', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(next_index),),
        )
        return locations[next_index]


def prospects_for_digest_since(iso_date: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM prospect WHERE created_at >= ? ORDER BY created_at DESC", (iso_date,)
        ).fetchall()
