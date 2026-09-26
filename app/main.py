"""
main.py — RetryProof sample order-processing backend.

Endpoints
---------
GET  /health
POST /events/order-confirmed

IMPORTANT — INTENTIONAL BUG (Milestone 1)
------------------------------------------
The /events/order-confirmed handler does NOT check whether the event_id
has already been processed.  Every delivery creates a new shipment row,
even for duplicate event_ids.  This bug is required for the RetryProof
demonstration and will be fixed in a later milestone.
"""

import os
import sqlite3

from fastapi import FastAPI, Request
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
    event_type: str
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

    BUG (intentional, Milestone 1): no idempotency check.
    Duplicate event_ids each create a new shipment row.
    """
    conn: sqlite3.Connection = get_db(_db_path())
    try:
        cursor = conn.execute(
            "INSERT INTO shipments (event_id, order_id) VALUES (?, ?)",
            (event.event_id, event.order_id),
        )
        conn.commit()
        shipment_id: int = cursor.lastrowid  # type: ignore[assignment]
    finally:
        conn.close()

    return EventResponse(
        shipment_id=shipment_id,
        event_id=event.event_id,
        order_id=event.order_id,
    )
