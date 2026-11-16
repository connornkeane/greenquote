import json
import os
import sqlite3
from datetime import datetime

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_phone TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    travel_miles REAL NOT NULL DEFAULT 0,
    terrain TEXT NOT NULL,
    frequency TEXT NOT NULL,
    notes TEXT,
    labor_total REAL NOT NULL,
    material_total REAL NOT NULL,
    discount REAL NOT NULL,
    travel_fee REAL NOT NULL,
    minimum_adjustment REAL NOT NULL DEFAULT 0,
    subtotal REAL NOT NULL,
    tax REAL NOT NULL,
    total REAL NOT NULL,
    deposit REAL NOT NULL,
    labor_hours REAL NOT NULL,
    crew_days INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Draft',
    proposal TEXT,
    forecast_json TEXT,
    recommended_date TEXT,
    location_label TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quote_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    service_key TEXT NOT NULL,
    label TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    labor_cost REAL NOT NULL,
    material_cost REAL NOT NULL,
    line_total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    event TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_quote ON quote_items(quote_id);
CREATE INDEX IF NOT EXISTS idx_activity_quote ON activity(quote_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);
"""

TOTAL_FIELDS = [
    "labor_total", "material_total", "discount", "travel_fee", "minimum_adjustment",
    "subtotal", "tax", "total", "deposit", "labor_hours", "crew_days",
]

INPUT_FIELDS = [
    "customer_name", "customer_email", "customer_phone", "city", "state",
    "travel_miles", "terrain", "frequency", "notes",
]


def get_db():
    if "db" not in g:
        path = current_app.config["DATABASE_PATH"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    get_db().executescript(SCHEMA)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _log(db, quote_id, event, detail=""):
    db.execute(
        "INSERT INTO activity (quote_id, event, detail, created_at) VALUES (?, ?, ?, ?)",
        (quote_id, event, detail, _now()),
    )


def _row_values(clean, result):
    values = {field: clean[field] for field in INPUT_FIELDS}
    for field in TOTAL_FIELDS:
        value = result[field]
        values[field] = value if isinstance(value, int) else float(value)
    return values


def _insert_items(db, quote_id, items):
    db.executemany(
        """INSERT INTO quote_items
           (quote_id, service_key, label, quantity, unit, labor_cost, material_cost, line_total)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                quote_id, item["service_key"], item["label"], item["quantity"], item["unit"],
                float(item["labor_cost"]), float(item["material_cost"]), float(item["line_total"]),
            )
            for item in items
        ],
    )


def create_quote(clean, result):
    db = get_db()
    values = _row_values(clean, result)
    values["created_at"] = values["updated_at"] = _now()
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    cursor = db.execute(
        f"INSERT INTO quotes ({columns}) VALUES ({placeholders})", list(values.values())
    )
    _insert_items(db, cursor.lastrowid, result["items"])
    _log(db, cursor.lastrowid, "Created", f"Quoted at ${float(result['total']):,.2f}")
    db.commit()
    return cursor.lastrowid


def update_quote(quote_id, clean, result):
    db = get_db()
    values = _row_values(clean, result)
    values["updated_at"] = _now()
    values["proposal"] = None
    assignments = ", ".join(f"{column} = ?" for column in values)
    db.execute(
        f"UPDATE quotes SET {assignments} WHERE id = ?", [*values.values(), quote_id]
    )
    db.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))
    _insert_items(db, quote_id, result["items"])
    _log(db, quote_id, "Edited", f"Re-priced at ${float(result['total']):,.2f}")
    db.commit()


def get_quote(quote_id):
    db = get_db()
    quote = db.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    if quote is None:
        return None, []
    items = db.execute(
        "SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id", (quote_id,)
    ).fetchall()
    return quote, items


def list_quotes(status=None):
    db = get_db()
    if status:
        return db.execute(
            "SELECT * FROM quotes WHERE status = ? ORDER BY updated_at DESC", (status,)
        ).fetchall()
    return db.execute("SELECT * FROM quotes ORDER BY updated_at DESC").fetchall()


def get_activity(quote_id):
    return get_db().execute(
        "SELECT * FROM activity WHERE quote_id = ? ORDER BY id DESC LIMIT 20", (quote_id,)
    ).fetchall()


def quote_quantities(items):
    return {item["service_key"]: item["quantity"] for item in items}


def update_status(quote_id, status):
    db = get_db()
    db.execute(
        "UPDATE quotes SET status = ?, updated_at = ? WHERE id = ?", (status, _now(), quote_id)
    )
    _log(db, quote_id, "Status", f"Marked {status}")
    db.commit()


def save_proposal(quote_id, proposal):
    db = get_db()
    db.execute(
        "UPDATE quotes SET proposal = ?, updated_at = ? WHERE id = ?",
        (proposal, _now(), quote_id),
    )
    _log(db, quote_id, "Proposal", "Proposal written")
    db.commit()


def save_forecast(quote_id, forecast):
    db = get_db()
    db.execute(
        """UPDATE quotes SET forecast_json = ?, recommended_date = ?, location_label = ?,
           updated_at = ? WHERE id = ?""",
        (
            json.dumps(forecast["days"]), forecast["recommended_date"],
            forecast["location"], _now(), quote_id,
        ),
    )
    _log(db, quote_id, "Forecast", f"Best start {forecast['recommended_date'] or 'not found'}")
    db.commit()


def dashboard_stats():
    db = get_db()
    row = db.execute(
        """SELECT
             COUNT(*) AS quote_count,
             COALESCE(SUM(CASE WHEN status IN ('Draft', 'Sent') THEN total END), 0) AS pipeline,
             COALESCE(SUM(CASE WHEN status = 'Accepted' THEN total END), 0) AS won,
             SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) AS accepted,
             SUM(CASE WHEN status IN ('Accepted', 'Declined') THEN 1 ELSE 0 END) AS decided
           FROM quotes"""
    ).fetchone()
    decided = row["decided"] or 0
    win_rate = round(100 * (row["accepted"] or 0) / decided) if decided else None
    return {
        "quote_count": row["quote_count"],
        "pipeline": row["pipeline"],
        "won": row["won"],
        "win_rate": win_rate,
    }
