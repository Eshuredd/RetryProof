"""
main.py — RetryProof sample order-processing backend.

Endpoints
---------
GET  /health
POST /events/order-confirmed
"""

import os
import sqlite3

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.database import DEFAULT_DB_PATH, get_db

app = FastAPI(title="RetryProof Sample App")

# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _db_path() -> str:
    """Return the database path, honouring the TEST_DB_PATH env var."""
    return os.environ.get("TEST_DB_PATH", DEFAULT_DB_PATH)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class OrderConfirmedEvent(BaseModel):
    event_id: str
    event_type: Literal["order.confirmed"]
    order_id: str


class HealthResponse(BaseModel):
    status: str


class EventResponse(BaseModel):
    shipment_id: int
    event_id: str
    order_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/events/order-confirmed", response_model=EventResponse, status_code=201)
def order_confirmed(event: OrderConfirmedEvent) -> EventResponse:
    """
    Handle an order.confirmed event by creating a shipment record.

    Idempotent: if the event_id has already been processed the existing
    shipment row is returned without creating a duplicate.  The uniqueness
    guarantee is enforced by a UNIQUE constraint on shipments.event_id, so
    the protection lives in persistent database state and survives separate
    request handlers and process restarts.
    """
    conn: sqlite3.Connection = get_db(_db_path())
    try:
        # INSERT OR IGNORE leaves the existing row untouched on a duplicate
        # event_id; lastrowid is 0 in that case.
        cursor = conn.execute(
            "INSERT OR IGNORE INTO shipments (event_id, order_id) VALUES (?, ?)",
            (event.event_id, event.order_id),
        )
        conn.commit()

        if cursor.lastrowid:
            # New insertion — use the just-created row id.
            shipment_id: int = cursor.lastrowid  # type: ignore[assignment]
        else:
            # Duplicate delivery — fetch the id of the original shipment.
            row = conn.execute(
                "SELECT id FROM shipments WHERE event_id = ?",
                (event.event_id,),
            ).fetchone()
            shipment_id = row["id"]
    finally:
        conn.close()

    return EventResponse(
        shipment_id=shipment_id,
        event_id=event.event_id,
        order_id=event.order_id,
    )
