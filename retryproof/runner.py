"""
runner.py — HTTP delivery engine and result evaluator for RetryProof.

Communicates with the target application over real HTTP using ``httpx``.
No knowledge of FastAPI, TestClient, or any particular application domain.
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
) -> dict[str, Any]:
    """Send a single HTTP request and return a compact response record."""
    url = base_url + path
    response = client.request(method, url, json=body)
    try:
        resp_body: Any = response.json()
    except Exception:
        resp_body = response.text
    return {
        "status_code": response.status_code,
        "body": resp_body,
    }


def _evaluate_observation(spec: ObservationSpec) -> dict[str, Any]:
    """Run the observer and build an observation result record."""
    observer = make_observer(spec)
    actual = observer.observe()
    passed = actual == spec.expected
    return {
        "type": spec.type,
        "query": spec.query,
        "params": spec.params,
        "expected": spec.expected,
        "actual": actual,
        "passed": passed,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(scenario: Scenario) -> dict[str, Any]:
    """
    Execute *scenario* against a live HTTP backend and return a result dict
    ready for evidence serialisation.

    Raises :class:`httpx.ConnectError` (or similar) if the target is not
    reachable — the caller (CLI) decides how to surface the error.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    deliveries_log: list[dict[str, Any]] = []
    with httpx.Client(timeout=10.0) as client:
        # --- Primary deliveries -------------------------------------------------
        for i in range(scenario.deliveries):
            record = _deliver(
                client,
                scenario.base_url,
                scenario.method,
                scenario.path,
                scenario.body,
            )
            deliveries_log.append(record)

        # --- Control checks (optional) -----------------------------------------
        controls_log: list[dict[str, Any]] = []
        for ctrl in scenario.controls:
            ctrl_response = _deliver(
                client,
                scenario.base_url,
                ctrl.method,
                ctrl.path,
                ctrl.body,
            )
            ctrl_obs = _evaluate_observation(ctrl.observation)
            ctrl_passed = ctrl_obs["passed"]
            controls_log.append(
                {
                    "label": ctrl.label,
                    "response": ctrl_response,
                    "observation": ctrl_obs,
                    "result": "PASS" if ctrl_passed else "FAIL",
                }
            )

    # --- Primary observation -----------------------------------------------
    primary_obs = _evaluate_observation(scenario.observation)
    primary_passed = primary_obs["passed"]

    # --- Overall verdict ---------------------------------------------------
    controls_passed = all(c["result"] == "PASS" for c in controls_log)
    overall_passed = primary_passed and controls_passed

    return {
        "scenario_name": scenario.name,
        "scenario_sha256": scenario.sha256,
        "scenario_path": scenario.raw_path,
        "timestamp": timestamp,
        "target": scenario.base_url,
        "request": {
            "method": scenario.method,
            "path": scenario.path,
            "body": scenario.body,
        },
        "deliveries": scenario.deliveries,
        "delivery_log": deliveries_log,
        "observation": primary_obs,
        "controls": controls_log,
        "result": "PASS" if overall_passed else "FAIL",
    }
