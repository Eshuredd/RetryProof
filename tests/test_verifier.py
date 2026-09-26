"""
test_verifier.py — Tests for the RetryProof verifier module.

These tests verify that the verifier itself works correctly:
  - the shipment-count helper reads the database accurately
  - the control scenario (two distinct events) correctly reports PASS
  - the verifier correctly DETECTS the duplicate-delivery bug and reports FAIL
  - the evidence JSON file is written with the expected structure

All of these tests should PASS on the Milestone 1 faulty baseline.
The duplicate-delivery test does NOT assert that the app behaves correctly;
it asserts that RetryProof correctly identifies the violation.
"""

import json
import os
import sqlite3

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers (mirrors verifier internals, used for direct DB inspection)
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
    """_count_shipments returns 0 on a freshly initialised database."""
    from app.database import get_db
    db_path = str(tmp_path / "v_test.db")
    conn = get_db(db_path)
    conn.close()
    assert _count_shipments(db_path) == 0


def test_verifier_control_scenario_passes(tmp_path):
    """
    Two distinct events delivered once each must produce exactly 2 shipments.
    The control scenario must PASS on both the buggy and the fixed build.
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
    RetryProof must correctly DETECT the duplicate-delivery violation.

    On the Milestone 1 faulty baseline, 5 deliveries of the same event_id
    produce 5 rows — not 1.  This test asserts that RetryProof observes the
    violation (actual_count > 1), not that the app avoids it.
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
        # RetryProof should observe more than 1 shipment — that is the violation.
        assert actual > 1, (
            f"Expected the faulty app to create > 1 shipment for 5 duplicate "
            f"deliveries, but found {actual}.  The intentional bug may have been "
            f"inadvertently fixed."
        )
    finally:
        os.environ.pop("TEST_DB_PATH", None)


def test_run_verification_writes_evidence(tmp_path, monkeypatch):
    """
    run_verification() must write a well-formed evidence JSON file and
    must report FAIL on the duplicate_deliveries scenario (Milestone 1).
    """
    import verifier.verify_idempotency as v_module

    fake_evidence_dir = tmp_path / "evidence"
    fake_evidence_file = fake_evidence_dir / "idempotency_report.json"

    monkeypatch.setattr(v_module, "EVIDENCE_DIR", fake_evidence_dir)
    monkeypatch.setattr(v_module, "EVIDENCE_FILE", fake_evidence_file)

    evidence = v_module.run_verification()

    # Evidence file must exist
    assert fake_evidence_file.exists(), "Evidence file was not created"

    # Re-read from disk to verify serialisation round-trip
    with open(fake_evidence_file) as f:
        data = json.load(f)

    # Structure checks
    assert data["milestone"] == 1
    assert data["tool"] == "RetryProof"
    assert "timestamp" in data
    assert "scenarios" in data
    assert "overall_result" in data

    # Duplicate scenario must be identified as FAIL
    dup_scenario = next(
        (s for s in data["scenarios"] if s["label"] == "duplicate_deliveries"),
        None,
    )
    assert dup_scenario is not None, "duplicate_deliveries scenario missing from evidence"
    assert dup_scenario["result"] == "FAIL", (
        "Verifier should report FAIL for duplicate_deliveries on the Milestone 1 build"
    )
    assert dup_scenario["actual_shipment_count"] > dup_scenario["expected_shipment_count"], (
        "Evidence should show actual > expected shipments for the duplicate scenario"
    )

    # Control scenario must be identified as PASS
    ctrl_scenario = next(
        (s for s in data["scenarios"] if s["label"] == "control_distinct_events"),
        None,
    )
    assert ctrl_scenario is not None, "control_distinct_events scenario missing from evidence"
    assert ctrl_scenario["result"] == "PASS"

    # Overall result must be FAIL (because duplicate scenario failed)
    assert data["overall_result"] == "FAIL"
