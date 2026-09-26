"""
__main__.py — RetryProof CLI entry point.

Usage
-----
    python -m retryproof run <scenario.json>

Exit codes
----------
    0  PASS
    1  FAIL  (or any unhandled error)
"""

from __future__ import annotations

import sys
from pathlib import Path


def _cmd_run(scenario_path: str) -> int:
    """Load *scenario_path*, run it, persist evidence, and return exit code."""
    # Local imports so the module is importable without optional deps at
    # package-level import time.
    import httpx

    from retryproof import evidence, runner, scenario as scenario_mod

    try:
        scen = scenario_mod.load(scenario_path)
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"[RetryProof] ERROR loading scenario: {exc}", file=sys.stderr)
        return 1

    print(f"[RetryProof] Running scenario: {scen.name}")
    print(f"[RetryProof] Target          : {scen.base_url}")
    print(f"[RetryProof] Deliveries      : {scen.deliveries}")
    print(f"[RetryProof] Scenario SHA-256: {scen.sha256}")

    try:
        result = runner.run(scen)
    except httpx.ConnectError as exc:
        print(
            f"[RetryProof] ERROR: could not connect to {scen.base_url} — {exc}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[RetryProof] ERROR during run: {exc}", file=sys.stderr)
        return 1

    evidence.print_summary(result)

    evidence_file = evidence.write(result)
    print(f"[RetryProof] Evidence written : {evidence_file}")

    return 0 if result["result"] == "PASS" else 1


def main() -> None:
    args = sys.argv[1:]

    if len(args) == 2 and args[0] == "run":
        sys.exit(_cmd_run(args[1]))

    # Help / unrecognised command
    print(
        "Usage: python -m retryproof run <scenario.json>",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
