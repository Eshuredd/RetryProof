"""
verify_idempotency.py — RetryProof Milestone 1 verifier.

Verifies that the /events/order-confirmed endpoint is idempotent:
delivering the same event multiple times must produce exactly ONE shipment.

Usage
-----
    python -m verifier.verify_idempotency

Exit codes
----------
    0  — all contracts pass  (PASS)
    1  — at least one contract fails (FAIL)

Evidence is written to evidence/idempotency_report.json.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the package root is on sys.path when run as a script
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi.testclient import TestClient  # noqa: E402 (import after path fix)

EVIDENCE_DIR = _ROOT / "evidence"
EVIDENCE_FILE = EVIDENCE_DIR / "idempotency_report.json"

DUPLICATE_DELIVERIES = 5
EXPECTED_SHIPMENT_COUNT = 1


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_shipments(db_path: str) -> int:
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()
        return row[0]
    finally:
        conn.close()


def _run_scenario(
    client: TestClient,
    label: str,
    event_id: str,
    order_id: str,
    deliveries: int,
    db_path: str,
) -> dict:
    """Deliver *event_id* exactly *deliveries* times and count resulting rows."""
    payload = {
        "event_id": event_id,
        "event_type": "order.confirmed",
        "order_id": order_id,
    }

    responses = []
    for _ in range(deliveries):
        r = client.post("/events/order-confirmed", json=payload)
        responses.append({"status_code": r.status_code, "body": r.json()})

    actual = _count_shipments(db_path)
    passed = actual == EXPECTED_SHIPMENT_COUNT

    return {
        "label": label,
        "event_id": event_id,
        "order_id": order_id,
        "deliveries": deliveries,
        "expected_shipment_count": EXPECTED_SHIPMENT_COUNT,
        "actual_shipment_count": actual,
        "result": "PASS" if passed else "FAIL",
        "responses": responses,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_verification() -> dict:
    """
    Execute the full idempotency verification suite.

    Returns the evidence dict (also written to disk).
    Raises SystemExit(1) if any scenario fails.
    """
    from app.main import app  # imported here so TEST_DB_PATH is already set

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    overall_pass = True
    scenarios = []

    # ------------------------------------------------------------------
    # Scenario 1 — duplicate deliveries (the idempotency contract)
    # ------------------------------------------------------------------
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_dup = f.name

    try:
        os.environ["TEST_DB_PATH"] = db_path_dup
        with TestClient(app) as client:
            result = _run_scenario(
                client=client,
                label="duplicate_deliveries",
                event_id="evt_1001",
                order_id="order_1001",
                deliveries=DUPLICATE_DELIVERIES,
                db_path=db_path_dup,
            )
        scenarios.append(result)
        if result["result"] != "PASS":
            overall_pass = False
    finally:
        os.unlink(db_path_dup)
        os.environ.pop("TEST_DB_PATH", None)

    # ------------------------------------------------------------------
    # Scenario 2 — control: a distinct event must create its own shipment
    # ------------------------------------------------------------------
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_ctrl = f.name

    try:
        os.environ["TEST_DB_PATH"] = db_path_ctrl
        with TestClient(app) as client:
            # First event
            r1 = client.post(
                "/events/order-confirmed",
                json={
                    "event_id": "evt_2001",
                    "event_type": "order.confirmed",
                    "order_id": "order_2001",
                },
            )
            # Second, different event
            r2 = client.post(
                "/events/order-confirmed",
                json={
                    "event_id": "evt_2002",
                    "event_type": "order.confirmed",
                    "order_id": "order_2002",
                },
            )
            actual_ctrl = _count_shipments(db_path_ctrl)
            ctrl_passed = actual_ctrl == 2  # two distinct events → two rows

        scenarios.append(
            {
                "label": "control_distinct_events",
                "deliveries": 2,
                "expected_shipment_count": 2,
                "actual_shipment_count": actual_ctrl,
                "result": "PASS" if ctrl_passed else "FAIL",
                "responses": [
                    {"status_code": r1.status_code, "body": r1.json()},
                    {"status_code": r2.status_code, "body": r2.json()},
                ],
            }
        )
        if not ctrl_passed:
            overall_pass = False
    finally:
        os.unlink(db_path_ctrl)
        os.environ.pop("TEST_DB_PATH", None)

    # ------------------------------------------------------------------
    # Build evidence document
    # ------------------------------------------------------------------
    evidence = {
        "tool": "RetryProof",
        "milestone": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_result": "PASS" if overall_pass else "FAIL",
        "scenarios": scenarios,
    }

    with open(EVIDENCE_FILE, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2)

    # ------------------------------------------------------------------
    # Human-readable summary to stdout
    # ------------------------------------------------------------------
    print("\n=== RetryProof — Idempotency Verification Report ===\n")
    for s in scenarios:
        print(f"  Scenario : {s['label']}")
        print(f"  Deliveries         : {s['deliveries']}")
        print(f"  Expected shipments : {s['expected_shipment_count']}")
        print(f"  Actual shipments   : {s['actual_shipment_count']}")
        print(f"  Result             : {s['result']}")
        print()

    print(f"Overall  : {evidence['overall_result']}")
    print(f"Evidence : {EVIDENCE_FILE}\n")

    return evidence


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    evidence = run_verification()
    sys.exit(0 if evidence["overall_result"] == "PASS" else 1)
