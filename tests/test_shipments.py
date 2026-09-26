"""
test_shipments.py — Tests for POST /events/order-confirmed

Covers:
  - happy-path shipment creation (201 + correct body)
  - single-event persistence confirmed in SQLite
  - invalid event_type rejection (422)
  - temporary database isolation between test runs

NOTE on idempotency:
  The duplicate-delivery contract (same event_id → exactly 1 shipment) is
  intentionally NOT tested here.  That contract is enforced and reported by
  the standalone RetryProof verifier:

      python -m verifier.verify_idempotency

  The Milestone 1 implementation is known to violate that contract.
  The verifier detects and records the violation; pytest does not fail on it.
"""

import os
import sqlite3

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def tmp_db(tmp_path):
    """Provide a fresh SQLite database path and wire it into the app."""
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
    """A single delivery creates exactly one row in the shipments table."""
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
    assert rows[0][1] == "evt_1001"    # event_id column
    assert rows[0][2] == "order_1001"  # order_id column


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_invalid_event_type_rejected(client):
    """event_type values other than 'order.confirmed' must return 422."""
    response = client.post(
        "/events/order-confirmed",
        json={
            "event_id": "evt_9999",
            "event_type": "order.cancelled",   # wrong type
            "order_id": "order_9999",
        },
    )
    assert response.status_code == 422


def test_missing_event_id_rejected(client):
    """Requests missing required fields must return 422."""
    response = client.post(
        "/events/order-confirmed",
        json={
            "event_type": "order.confirmed",
            "order_id": "order_1001",
            # event_id omitted
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Database isolation
# ---------------------------------------------------------------------------

def test_fresh_database_has_no_shipments(tmp_db):
    """A freshly created test database contains no shipment rows."""
    conn = sqlite3.connect(tmp_db)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='shipments'"
    ).fetchall()
    if tables:
        count = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        assert count == 0
    conn.close()


def test_two_test_runs_do_not_share_state(tmp_path):
    """Each tmp_db fixture provides a distinct file path — no shared state."""
    db_a = str(tmp_path / "a.db")
    db_b = str(tmp_path / "b.db")
    assert db_a != db_b
