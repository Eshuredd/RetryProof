"""
evidence.py — Persist and display RetryProof run results.

Responsibilities
----------------
- Write the result dict as a JSON evidence file.
- Print a human-readable summary to stdout.
- Return the path to the written file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_EVIDENCE_DIR = Path("evidence")


def write(result: dict[str, Any], evidence_dir: Path | None = None) -> Path:
    """
    Serialise *result* to a JSON file inside *evidence_dir* (defaults to
    ``evidence/`` in the current working directory).

    The file is named after the scenario: ``<scenario_name>_retryproof.json``
    with spaces replaced by underscores.

    Returns the :class:`~pathlib.Path` of the written file.
    """
    out_dir = evidence_dir if evidence_dir is not None else _EVIDENCE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = result["scenario_name"].replace(" ", "_")
    out_file = out_dir / f"{safe_name}_retryproof.json"

    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    return out_file


def print_summary(result: dict[str, Any]) -> None:
    """Print a human-readable summary of *result* to stdout."""
    line = "=" * 60
    print(f"\n{line}")
    print(f"  RetryProof — {result['scenario_name']}")
    print(line)
    print(f"  Timestamp     : {result['timestamp']}")
    print(f"  Target        : {result['target']}")
    print(f"  Method / Path : {result['request']['method']} {result['request']['path']}")
    print(f"  Deliveries    : {result['deliveries']}")

    obs = result["observation"]
    print(f"\n  Observation")
    print(f"    Query    : {obs['query']}")
    print(f"    Params   : {obs['params']}")
    print(f"    Expected : {obs['expected']}")
    print(f"    Actual   : {obs['actual']}")

    if result["controls"]:
        print(f"\n  Controls")
        for ctrl in result["controls"]:
            c_obs = ctrl["observation"]
            print(
                f"    [{ctrl['result']:4s}] {ctrl['label']} "
                f"(expected={c_obs['expected']}, actual={c_obs['actual']})"
            )

    print(f"\n  Scenario SHA-256 : {result['scenario_sha256']}")
    print(f"\n  Result : {result['result']}")
    print(f"{line}\n")
