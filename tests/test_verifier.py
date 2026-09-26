"""
test_verifier.py — Tests for the verifier module.

These tests exercise the verifier's own logic, not the app directly.
The idempotency scenario test mirrors what run_verification() checks and
is also expected to fail on this buggy implementation.
"""

import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_shipments(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Verifier unit tests
# ---------------------------------------------------------------------------

def test_verifier_count_helper(tmp_path):
    """_count_shipments returns 0 on a freshly-initialised database."""
    from app.database import get_db
    db_path = str(tmp_path / "v_test.db")
    conn = get_db(db_path)
    conn.close()
    assert _count_shipments(db_path) == 0


def test_verifier_control_scenario_passes(tmp_path):
    """
    Two distinct events delivered once each must produce exactly 2 shipments.
    The control scenario should always PASS (even on the buggy build).
    """
    from app.main import app

    db_path = str(tmp_path / "ctrl.db")
    os.environ["TEST_DB_PATH"] = db_path
    try:
        with TestClient(app) as client:
            client.post(
                "/events/order-confirmed",
                json={"event_id": "evt_A", "event_type": "order.confirmed", "order_id": "ord_A"},
            )
            client.post(
                "/events/order-confirmed",
                json={"event_id": "evt_B", "event_type": "order.confirmed", "order_id": "ord_B"},
            )
        assert _count_shipments(db_path) == 2
    finally:
        os.environ.pop("TEST_DB_PATH", None)


def test_verifier_detects_duplicate_shipments(tmp_path):
    """
    Verifier must detect that 5 deliveries of the same event_id produce > 1 row.

    THIS TEST IS EXPECTED TO FAIL on the Milestone 1 buggy implementation:
    the actual count will be 5, not 1, so the final assertion triggers.
    """
    from app.main import app

    db_path = str(tmp_path / "dup.db")
    os.environ["TEST_DB_PATH"] = db_path
    try:
        with TestClient(app) as client:
            for _ in range(5):
                client.post(
                    "/events/order-confirmed",
                    json={
                        "event_id": "evt_1001",
                        "event_type": "order.confirmed",
                        "order_id": "order_1001",
                    },
                )
        actual = _count_shipments(db_path)
        # The verifier contract: exactly one shipment regardless of delivery count
        assert actual == 1, (
            f"Verifier contract FAIL: expected 1 shipment, got {actual}. "
            "The duplicate-delivery bug is confirmed and must be fixed."
        )
    finally:
        os.environ.pop("TEST_DB_PATH", None)


def test_run_verification_writes_evidence(tmp_path, monkeypatch):
    """
    run_verification() must write an evidence JSON file.
    We monkeypatch the evidence path to avoid writing to the real evidence/ dir.
    The function will still report FAIL (because of the bug) — that's expected.
    """
    import verifier.verify_idempotency as v_module

    fake_evidence_dir = tmp_path / "evidence"
    fake_evidence_file = fake_evidence_dir / "idempotency_report.json"

    monkeypatch.setattr(v_module, "EVIDENCE_DIR", fake_evidence_dir)
    monkeypatch.setattr(v_module, "EVIDENCE_FILE", fake_evidence_file)

    evidence = v_module.run_verification()

    assert fake_evidence_file.exists(), "Evidence file was not created"

    import json
    with open(fake_evidence_file) as f:
        data = json.load(f)

    assert data["milestone"] == 1
    assert "scenarios" in data
    assert "overall_result" in data
    assert data["overall_result"] in ("PASS", "FAIL")
