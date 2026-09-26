"""
database.py — SQLite helpers for RetryProof sample app.

get_db(path) opens (or creates) a SQLite database at *path* and returns
the connection.  Callers are responsible for closing it.
"""

import sqlite3

DEFAULT_DB_PATH = "shipments.db"


def get_db(path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return an open SQLite connection to *path*, creating tables if needed."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the shipments table if it does not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shipments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id   TEXT    NOT NULL,
            order_id   TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
