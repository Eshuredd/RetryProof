"""
observers.py — Persistent-state observers for RetryProof.

An observer reads the state of an external data store and returns a single
scalar value that is compared against the expected value declared in the
scenario.

Currently supported
-------------------
- SQLiteCountObserver  (type: "sqlite_count")
  Runs a parameterised SQL query against a SQLite database file and returns
  the first column of the first row as the observed value.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from retryproof.scenario import ObservationSpec


# ---------------------------------------------------------------------------
# Base protocol (duck-typed; not imported at runtime)
# ---------------------------------------------------------------------------

class _Observer:
    """Internal duck-type contract."""

    def observe(self) -> Any:
        """Return the current observed value."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# SQLite observer
# ---------------------------------------------------------------------------

class SQLiteCountObserver:
    """
    Executes *spec.query* against the SQLite file at *spec.database* with
    *spec.params* and returns the scalar value from the first row's first
    column.
    """

    def __init__(self, spec: ObservationSpec) -> None:
        self._spec = spec

    def observe(self) -> Any:
        conn = sqlite3.connect(self._spec.database)
        try:
            row = conn.execute(self._spec.query, self._spec.params).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return row[0]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_observer(spec: ObservationSpec) -> _Observer:
    """Return the correct observer for *spec.type*."""
    if spec.type == "sqlite_count":
        return SQLiteCountObserver(spec)
    raise ValueError(f"Unknown observation type: '{spec.type}'")
