"""SQLite database layer for case study data."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path) -> None:
    """Create tables if they don't exist."""
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            industry TEXT DEFAULT '',
            onboarded_at TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
            label TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
            category TEXT DEFAULT '',
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            unit TEXT DEFAULT '',
            change_pct TEXT DEFAULT '',
            change_vs TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS screenshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            original_name TEXT DEFAULT '',
            caption TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
            category TEXT DEFAULT '',
            content TEXT NOT NULL,
            source TEXT DEFAULT '',
            entry_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# --- Brands ---

def create_brand(db_path: str | Path, name: str, industry: str = "",
                 onboarded_at: str = "", notes: str = "") -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        "INSERT INTO brands (name, industry, onboarded_at, notes, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, industry, onboarded_at, notes, datetime.now().isoformat()),
    )
    conn.commit()
    brand_id = cur.lastrowid
    conn.close()
    return brand_id


def get_brands(db_path: str | Path) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT b.*, COUNT(s.id) as snapshot_count,
               MAX(s.snapshot_date) as last_snapshot
        FROM brands b
        LEFT JOIN snapshots s ON s.brand_id = b.id
        GROUP BY b.id
        ORDER BY b.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_brand(db_path: str | Path, brand_id: int) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM brands WHERE id = ?", (brand_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_brand(db_path: str | Path, brand_id: int) -> None:
    conn = get_connection(db_path)
    conn.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
    conn.commit()
    conn.close()


# --- Snapshots ---

def create_snapshot(db_path: str | Path, brand_id: int, label: str,
                    snapshot_date: str, notes: str = "") -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        "INSERT INTO snapshots (brand_id, label, snapshot_date, notes, created_at) VALUES (?, ?, ?, ?, ?)",
        (brand_id, label, snapshot_date, notes, datetime.now().isoformat()),
    )
    conn.commit()
    snapshot_id = cur.lastrowid
    conn.close()
    return snapshot_id


def get_snapshots(db_path: str | Path, brand_id: int) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM snapshots WHERE brand_id = ? ORDER BY snapshot_date DESC",
        (brand_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_snapshot(db_path: str | Path, snapshot_id: int) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_snapshot(db_path: str | Path, snapshot_id: int) -> None:
    conn = get_connection(db_path)
    conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
    conn.commit()
    conn.close()


# --- Metrics ---

def add_metric(db_path: str | Path, snapshot_id: int, category: str, name: str,
               value: str, unit: str = "", change_pct: str = "", change_vs: str = "") -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        "INSERT INTO metrics (snapshot_id, category, name, value, unit, change_pct, change_vs) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (snapshot_id, category, name, value, unit, change_pct, change_vs),
    )
    conn.commit()
    metric_id = cur.lastrowid
    conn.close()
    return metric_id


def get_metrics(db_path: str | Path, snapshot_id: int) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM metrics WHERE snapshot_id = ? ORDER BY category, name",
        (snapshot_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Screenshots ---

def add_screenshot(db_path: str | Path, snapshot_id: int, filename: str,
                   original_name: str = "", caption: str = "") -> int:
    conn = get_connection(db_path)
    cur = conn.execute(
        "INSERT INTO screenshots (snapshot_id, filename, original_name, caption) VALUES (?, ?, ?, ?)",
        (snapshot_id, filename, original_name, caption),
    )
    conn.commit()
    screenshot_id = cur.lastrowid
    conn.close()
    return screenshot_id


def get_screenshots(db_path: str | Path, snapshot_id: int) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM screenshots WHERE snapshot_id = ? ORDER BY id",
        (snapshot_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Entries (free-form text) ---

def create_entry(db_path: str | Path, brand_id: int, category: str, content: str,
                 source: str = "", entry_date: str = "") -> int:
    if not entry_date:
        entry_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection(db_path)
    cur = conn.execute(
        "INSERT INTO entries (brand_id, category, content, source, entry_date, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (brand_id, category, content, source, entry_date, datetime.now().isoformat()),
    )
    conn.commit()
    entry_id = cur.lastrowid
    conn.close()
    return entry_id


def get_entries(db_path: str | Path, brand_id: int) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM entries WHERE brand_id = ? ORDER BY entry_date DESC, created_at DESC",
        (brand_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_entry(db_path: str | Path, entry_id: int) -> None:
    conn = get_connection(db_path)
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


# --- Full brand data for case study generation ---

def get_brand_full(db_path: str | Path, brand_id: int) -> dict | None:
    """Get brand with all snapshots, metrics, and screenshots."""
    brand = get_brand(db_path, brand_id)
    if not brand:
        return None

    snapshots = get_snapshots(db_path, brand_id)
    for snap in snapshots:
        snap["metrics"] = get_metrics(db_path, snap["id"])
        snap["screenshots"] = get_screenshots(db_path, snap["id"])

    brand["snapshots"] = snapshots
    brand["entries"] = get_entries(db_path, brand_id)
    return brand
