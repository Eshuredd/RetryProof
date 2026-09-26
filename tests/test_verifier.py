"""
Tests for the RetryProof verifier.

These tests validate the verifier infrastructure itself.

Important:
- pytest should PASS both before and after the application is repaired.
- The standalone verifier is responsible for deciding whether the
  application satisfies the retry-safety contract.
"""

import json
import os
import sqlite3

from fastapi.testclient import TestClient


def _count_shipments(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM shipments"
        ).fetchone()[0]
    finally:
        conn.close()


def test_verifier_count_helper(tmp_path):
    """Shipment counting reads persisted SQLite state correctly."""
    from app.database import get_db

    db_path = str(tmp_path / "count_test.db")

    conn = get_db(db_path)
    conn.close()

    assert _count_shipments(db_path) == 0


def test_control_distinct_events_create_two_shipments(tmp_path):
    """
    Two genuinely different valid events must create two shipments.

    This must remain true both before and after the idempotency repair.
    """
    from app.main import app

    db_path = str(tmp_path / "control.db")
    os.environ["TEST_DB_PATH"] = db_path

    try:
        with TestClient(app) as client:
            response_1 = client.post(
                "/events/order-confirmed",
                json={
                    "event_id": "evt_A",
                    "event_type": "order.confirmed",
                    "order_id": "order_A",
                },
            )

            response_2 = client.post(
                "/events/order-confirmed",
                json={
                    "event_id": "evt_B",
                    "event_type": "order.confirmed",
                    "order_id": "order_B",
                },
            )

        assert response_1.status_code == 201
        assert response_2.status_code == 201
        assert _count_shipments(db_path) == 2

    finally:
        os.environ.pop("TEST_DB_PATH", None)


def test_run_verification_writes_consistent_evidence(tmp_path, monkeypatch):
    """
    The verifier must write a valid evidence document whose verdicts
    agree with the observed shipment counts.

    This test intentionally does NOT require the application to be
    either faulty or fixed.
    """
    import verifier.verify_idempotency as verifier

    evidence_dir = tmp_path / "evidence"
    evidence_file = evidence_dir / "idempotency_report.json"

    monkeypatch.setattr(
        verifier,
        "EVIDENCE_DIR",
        evidence_dir,
    )
    monkeypatch.setattr(
        verifier,
        "EVIDENCE_FILE",
        evidence_file,
    )

    result = verifier.run_verification()

    assert evidence_file.exists()

    with open(evidence_file, encoding="utf-8") as file:
        saved = json.load(file)

    # Basic evidence structure
    assert saved["tool"] == "RetryProof"
    assert saved["milestone"] == 1
    assert "timestamp" in saved
    assert "overall_result" in saved
    assert isinstance(saved["scenarios"], list)

    duplicate = next(
        scenario
        for scenario in saved["scenarios"]
        if scenario["label"] == "duplicate_deliveries"
    )

    control = next(
        scenario
        for scenario in saved["scenarios"]
        if scenario["label"] == "control_distinct_events"
    )

    # Retry-safety contract must always remain unchanged.
    assert duplicate["deliveries"] == 5
    assert duplicate["expected_shipment_count"] == 1

    # Verify the verdict is derived from the real observed count.
    expected_duplicate_result = (
        "PASS"
        if duplicate["actual_shipment_count"]
        == duplicate["expected_shipment_count"]
        else "FAIL"
    )

    assert duplicate["result"] == expected_duplicate_result

    # The control contract is always:
    # two distinct events -> two legitimate shipments.
    assert control["deliveries"] == 2
    assert control["expected_shipment_count"] == 2
    assert control["actual_shipment_count"] == 2
    assert control["result"] == "PASS"

    # Overall result must correspond to all scenario results.
    expected_overall = (
        "PASS"
        if all(
            scenario["result"] == "PASS"
            for scenario in saved["scenarios"]
        )
        else "FAIL"
    )

    assert saved["overall_result"] == expected_overall

    # The returned object and saved evidence should agree.
    assert result["overall_result"] == saved["overall_result"]