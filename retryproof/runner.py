"""
runner.py — HTTP delivery engine and result evaluator for RetryProof.

Communicates with the target application over real HTTP using ``httpx``.
No knowledge of FastAPI, TestClient, or any particular application domain.

Execution order
---------------
1. Check primary precondition  (observation.expected_before)
2. Send primary HTTP deliveries (assert each response matches expected_status)
3. Observe primary result       (observation.expected)
4. Execute each control         (deliver → observe)
5. Build and return result dict
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from retryproof.observers import make_observer
from retryproof.scenario import ControlSpec, ObservationSpec, Scenario


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _deliver(
    client: httpx.Client,
    base_url: str,
    method: str,
    path: str,
    body: Any,
    expected_status: int | None,
) -> dict[str, Any]:
    """
    Send a single HTTP request and return a compact response record.

    ``status_ok`` is True when *expected_status* is None (not checked) OR
    when the actual status matches *expected_status*.
    """
    url = base_url + path
    response = client.request(method, url, json=body)
    try:
        resp_body: Any = response.json()
    except Exception:
        resp_body = response.text

    status_ok = (
        expected_status is None
        or response.status_code == expected_status
    )
    return {
        "status_code": response.status_code,
        "expected_status": expected_status,
        "status_ok": status_ok,
        "body": resp_body,
    }


def _evaluate_observation(
    spec: ObservationSpec,
    *,
    phase: str = "after",
) -> dict[str, Any]:
    """
    Run the observer and build an observation result record.

    *phase* is recorded for clarity but not used in logic here.
    """
    observer = make_observer(spec)
    actual = observer.observe()
    passed = actual == spec.expected
    return {
        "type": spec.type,
        "query": spec.query,
        "params": spec.params,
        "expected_before": spec.expected_before,
        "expected_after": spec.expected,
        "actual_after": actual,
        "passed": passed,
    }


def _check_precondition(spec: ObservationSpec) -> dict[str, Any]:
    """
    Observe the current state and check it against *spec.expected_before*.

    Returns a precondition record.  ``passed`` is True when expected_before
    is None (no check declared) or when the actual value matches.
    """
    if spec.expected_before is None:
        return {
            "expected_before": None,
            "actual_before": None,
            "passed": True,
            "skipped": True,
        }
    observer = make_observer(spec)
    actual_before = observer.observe()
    passed = actual_before == spec.expected_before
    return {
        "expected_before": spec.expected_before,
        "actual_before": actual_before,
        "passed": passed,
        "skipped": False,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(scenario: Scenario) -> dict[str, Any]:
    """
    Execute *scenario* against a live HTTP backend and return a result dict
    ready for evidence serialisation.

    Execution order: precondition → deliveries → primary observation → controls.

    Raises :class:`httpx.ConnectError` (or similar) if the target is not
    reachable — the caller (CLI) decides how to surface the error.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Step 1: Primary precondition check (before any HTTP traffic)
    # ------------------------------------------------------------------
    precondition = _check_precondition(scenario.observation)

    deliveries_log: list[dict[str, Any]] = []
    controls_log: list[dict[str, Any]] = []

    with httpx.Client(timeout=10.0) as client:
        # --------------------------------------------------------------
        # Step 2: Primary deliveries
        # --------------------------------------------------------------
        for _ in range(scenario.deliveries):
            record = _deliver(
                client,
                scenario.base_url,
                scenario.method,
                scenario.path,
                scenario.body,
                scenario.expected_status,
            )
            deliveries_log.append(record)

        # --------------------------------------------------------------
        # Step 3: Primary observation (after all deliveries)
        # --------------------------------------------------------------
        primary_obs = _evaluate_observation(scenario.observation)

        # --------------------------------------------------------------
        # Step 4: Controls (each: deliver once, then observe)
        # --------------------------------------------------------------
        for ctrl in scenario.controls:
            ctrl_response = _deliver(
                client,
                scenario.base_url,
                ctrl.method,
                ctrl.path,
                ctrl.body,
                ctrl.expected_status,
            )
            ctrl_obs = _evaluate_observation(ctrl.observation)
            ctrl_status_ok = ctrl_response["status_ok"]
            ctrl_obs_passed = ctrl_obs["passed"]
            ctrl_passed = ctrl_status_ok and ctrl_obs_passed
            controls_log.append(
                {
                    "label": ctrl.label,
                    "response": ctrl_response,
                    "observation": ctrl_obs,
                    "result": "PASS" if ctrl_passed else "FAIL",
                }
            )

    # ------------------------------------------------------------------
    # Step 5: Overall verdict
    # ------------------------------------------------------------------
    precondition_ok = precondition["passed"]
    deliveries_status_ok = all(d["status_ok"] for d in deliveries_log)
    primary_obs_passed = primary_obs["passed"]
    controls_passed = all(c["result"] == "PASS" for c in controls_log)

    overall_passed = (
        precondition_ok
        and deliveries_status_ok
        and primary_obs_passed
        and controls_passed
    )

    return {
        "scenario_name": scenario.name,
        "scenario_sha256": scenario.sha256,
        "scenario_path": scenario.raw_path,
        "timestamp": timestamp,
        "target": scenario.base_url,
        "request": {
            "method": scenario.method,
            "path": scenario.path,
            "expected_status": scenario.expected_status,
            "body": scenario.body,
        },
        "deliveries": scenario.deliveries,
        "precondition": precondition,
        "delivery_log": deliveries_log,
        "observation": primary_obs,
        "controls": controls_log,
        "result": "PASS" if overall_passed else "FAIL",
    }
