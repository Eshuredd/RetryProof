from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def database_path() -> str:
    return os.getenv("NOTIFICATION_DB_PATH", "notification_demo.db")


def get_db(path: str | None = None) -> sqlite3.Connection:
    db_path = path or database_path()

    parent = Path(db_path).parent
    parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str | None = None) -> None:
    conn = get_db(path)

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL UNIQUE,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # For databases created before the UNIQUE constraint was introduced,
        # remove duplicate message_id rows (keeping the earliest id) so the
        # unique index can always be created successfully.
        conn.execute(
            """
            DELETE FROM email_jobs
            WHERE id NOT IN (
                SELECT MIN(id) FROM email_jobs GROUP BY message_id
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_email_jobs_message_id
            ON email_jobs (message_id)
            """
        )
        conn.commit()
    finally:
        conn.close()