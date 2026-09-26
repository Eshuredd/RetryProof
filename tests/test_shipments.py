"""
test_shipments.py — Tests for POST /events/order-confirmed

Covers:
  - happy-path shipment creation
  - duplicate handling (acceptance test that INTENTIONALLY FAILS on this
    buggy implementation — do not weaken this assertion)
  - database isolation between test runs
"""

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def tmp_db(tmp_path):
    """Provide a fresh SQLite database path for each test."""
    db_file = str(tmp_path / "test_shipments.db")
    os.environ["TEST_DB_PATH"] = db_file
    yield db_file
    os.environ.pop("TEST_DB_PATH", None)


@pytest.fixture()
def client(tmp_db):
    """TestClient wired to the per-test temporary database."""
    from app.main import app
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_order_confirmed_returns_201(client):
    response = client.post(
        "/events/order-confirmed",
        json={
            "event_id": "evt_1001",
            "event_type": "order.confirmed",
            "order_id": "order_1001",
        },
    )
    assert response.status_code == 201


def test_order_confirmed_returns_shipment_id(client):
    response = client.post(
        "/events/order-confirmed",
        json={
            "event_id": "evt_1001",
            "event_type": "order.confirmed",
            "order_id": "order_1001",
        },
    )
    body = response.json()
    assert "shipment_id" in body
    assert body["event_id"] == "evt_1001"
    assert body["order_id"] == "order_1001"


def test_shipment_is_persisted(client, tmp_db):
    client.post(
        "/events/order-confirmed",
        json={
            "event_id": "evt_1001",
            "event_type": "order.confirmed",
            "order_id": "order_1001",
        },
    )
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute("SELECT * FROM shipments").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][1] == "evt_1001"   # event_id column
    assert rows[0][2] == "order_1001" # order_id column


# ---------------------------------------------------------------------------
# Acceptance test — INTENTIONALLY FAILS on the buggy Milestone 1 implementation
# ---------------------------------------------------------------------------

def test_duplicate_event_creates_only_one_shipment(client, tmp_db):
    """
    Delivering the same event_id 5 times must produce exactly 1 shipment row.

    THIS TEST IS EXPECTED TO FAIL against the Milestone 1 implementation.
    The bug: the handler performs an unconditional INSERT with no idempotency
    guard, so 5 deliveries create 5 rows.  Do NOT weaken this assertion.
    """
    payload = {
        "event_id": "evt_1001",
        "event_type": "order.confirmed",
        "order_id": "order_1001",
    }
    for _ in range(5):
        client.post("/events/order-confirmed", json=payload)

    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
    conn.close()

    assert count == 1, (
        f"Idempotency failure: expected 1 shipment after 5 deliveries of the "
        f"same event_id, but found {count}.  The handler must be fixed to check "
        f"for duplicate event_ids before inserting."
    )


# ---------------------------------------------------------------------------
# Database isolation
# ---------------------------------------------------------------------------

def test_fresh_database_has_no_shipments(tmp_db):
    conn = sqlite3.connect(tmp_db)
    # table may not exist yet if the app hasn't been called; that's fine.
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='shipments'"
    ).fetchall()
    if tables:
        count = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        assert count == 0
    conn.close()


def test_two_tests_do_not_share_state(tmp_path):
    """Each tmp_db fixture gives a different file, ensuring isolation."""
    db_a = str(tmp_path / "a.db")
    db_b = str(tmp_path / "b.db")
    assert db_a != db_b
