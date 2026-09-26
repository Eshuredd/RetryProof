"""
evidence.py — Persist and display RetryProof run results.

Responsibilities
----------------
- Write the result dict as a JSON evidence file with a unique, immutable name.
- Print a human-readable summary to stdout.
- Return the path to the written file.

File naming
-----------
Each run produces a distinct file so previous evidence is never overwritten:

    <scenario_name>_<UTC-timestamp>_<PASS|FAIL>_<first8-sha256>.json

Example:
    order_confirmed_idempotency_20241015T143022Z_PASS_87e86351.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_EVIDENCE_DIR = Path("evidence")


def _build_filename(result: dict[str, Any]) -> str:
    """Return a unique, human-readable evidence filename for *result*."""
    safe_name = result["scenario_name"].replace(" ", "_")
    # Derive timestamp from the result itself so replaying is consistent.
    ts_raw: str = result.get("timestamp", datetime.now(timezone.utc).isoformat())
    # Normalise to compact UTC form: 20241015T143022Z
    try:
        dt = datetime.fromisoformat(ts_raw)
        ts = dt.strftime("%Y%m%dT%H%M%SZ")
    except ValueError:
        ts = ts_raw[:19].replace(":", "").replace("-", "")
    verdict = result.get("result", "UNKNOWN")
    sha_prefix = result.get("scenario_sha256", "0" * 64)[:8]
    return f"{safe_name}_{ts}_{verdict}_{sha_prefix}.json"


def write(result: dict[str, Any], evidence_dir: Path | None = None) -> Path:
    """
    Serialise *result* to a JSON file inside *evidence_dir* (defaults to
    ``evidence/`` in the current working directory).

    Every call produces a **new** uniquely named file — previous evidence
    is never overwritten.

    Returns the :class:`~pathlib.Path` of the written file.
    """
    out_dir = evidence_dir if evidence_dir is not None else _EVIDENCE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = _build_filename(result)
    out_file = out_dir / filename

    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    return out_file


def print_summary(result: dict[str, Any]) -> None:
    """Print a human-readable summary of *result* to stdout."""
    line = "=" * 62
    print(f"\n{line}")
    print(f"  RetryProof -- {result['scenario_name']}")
    print(line)
    print(f"  Timestamp     : {result['timestamp']}")
    print(f"  Target        : {result['target']}")
    req = result["request"]
    print(f"  Method / Path : {req['method']} {req['path']}")
    print(f"  Expected HTTP : {req.get('expected_status', 'n/a')}")
    print(f"  Deliveries    : {result['deliveries']}")

    pre = result.get("precondition", {})
    if not pre.get("skipped"):
        pre_ok = "[OK  ]" if pre.get("passed") else "[FAIL]"
        print(
            f"\n  Precondition  : {pre_ok} "
            f"expected_before={pre.get('expected_before')}  "
            f"actual_before={pre.get('actual_before')}"
        )

    # HTTP status summary across deliveries
    log = result.get("delivery_log", [])
    statuses = [str(d["status_code"]) for d in log]
    all_ok = all(d.get("status_ok", True) for d in log)
    status_flag = "[OK  ]" if all_ok else "[FAIL]"
    print(f"\n  HTTP statuses : {status_flag} {', '.join(statuses)}")

    obs = result["observation"]
    obs_ok = "[OK  ]" if obs.get("passed") else "[FAIL]"
    print(f"\n  Observation   : {obs_ok}")
    print(f"    Query         : {obs['query']}")
    print(f"    Params        : {obs['params']}")
    print(f"    Expected before : {obs.get('expected_before', 'n/a')}")
    print(f"    Expected after  : {obs['expected_after']}")
    print(f"    Actual after    : {obs['actual_after']}")

    if result["controls"]:
        print(f"\n  Controls")
        for ctrl in result["controls"]:
            c_obs = ctrl["observation"]
            c_resp = ctrl["response"]
            print(
                f"    [{ctrl['result']:4s}] {ctrl['label']} "
                f"http={c_resp['status_code']} "
                f"expected_after={c_obs['expected_after']} "
                f"actual_after={c_obs['actual_after']}"
            )

    print(f"\n  Scenario SHA-256 : {result['scenario_sha256']}")
    print(f"\n  Result : {result['result']}")
    print(f"{line}\n")
