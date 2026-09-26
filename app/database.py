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
            event_id   TEXT    NOT NULL UNIQUE,
            order_id   TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    # Migrate existing databases that were created without the UNIQUE constraint.
    _migrate_add_event_id_unique(conn)
    conn.commit()


def _migrate_add_event_id_unique(conn: sqlite3.Connection) -> None:
    """
    Idempotently enforce a UNIQUE index on event_id for databases that were
    created before the constraint was added to the CREATE TABLE statement.

    SQLite does not support ALTER TABLE … ADD CONSTRAINT, so we use a
    named unique index instead.  CREATE UNIQUE INDEX IF NOT EXISTS is a
    no-op when the index already exists, making this safe to call on every
    startup.
    """
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_shipments_event_id
        ON shipments (event_id)
        """
    )
