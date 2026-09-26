"""
scenario.py — Load, validate, and hash a RetryProof JSON scenario file.

A scenario is the frozen acceptance contract.  Its SHA-256 is embedded in
every piece of evidence produced from it so the exact test conditions can
always be reproduced.

Scenario schema
---------------
{
  "scenario_name": str,
  "target": {
    "base_url": str          # e.g. "http://localhost:8000"
  },
  "request": {
    "method": str,           # "POST", "GET", …
    "path": str,             # e.g. "/events/order-confirmed"
    "body": object | null    # JSON body (optional)
  },
  "retry": {
    "deliveries": int        # total number of HTTP deliveries (>= 1)
  },
  "observation": {
    "type": "sqlite_count",
    "database": str,         # path to SQLite file
    "query": str,            # SQL that returns a single scalar
    "params": array,         # positional parameters for the query
    "expected": int | str | float
  },
  "controls": [              # optional list of control requests
    {
      "label": str,
      "method": str,
      "path": str,
      "body": object | null,
      "observation": { ... } # same shape as top-level observation
    }
  ]
}
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ObservationSpec:
    type: str          # currently only "sqlite_count"
    database: str
    query: str
    params: list[Any]
    expected: Any


@dataclass
class ControlSpec:
    label: str
    method: str
    path: str
    body: Any
    observation: ObservationSpec


@dataclass
class Scenario:
    name: str
    base_url: str
    method: str
    path: str
    body: Any
    deliveries: int
    observation: ObservationSpec
    controls: list[ControlSpec]
    sha256: str          # hex digest of the raw scenario file bytes
    raw_path: str        # filesystem path the scenario was loaded from


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_observation(data: dict[str, Any], context: str) -> ObservationSpec:
    for key in ("type", "database", "query", "params", "expected"):
        if key not in data:
            raise ValueError(
                f"Scenario observation ({context}) is missing required key: '{key}'"
            )
    obs_type = data["type"]
    if obs_type != "sqlite_count":
        raise ValueError(
            f"Unsupported observation type '{obs_type}' in {context}. "
            "Only 'sqlite_count' is supported in v1."
        )
    if not isinstance(data["params"], list):
        raise ValueError(
            f"observation.params must be a JSON array in {context}"
        )
    return ObservationSpec(
        type=obs_type,
        database=data["database"],
        query=data["query"],
        params=data["params"],
        expected=data["expected"],
    )


def _parse_control(raw: dict[str, Any], index: int) -> ControlSpec:
    context = f"controls[{index}]"
    for key in ("label", "method", "path", "observation"):
        if key not in raw:
            raise ValueError(
                f"Control entry {context} is missing required key: '{key}'"
            )
    return ControlSpec(
        label=raw["label"],
        method=raw["method"].upper(),
        path=raw["path"],
        body=raw.get("body"),
        observation=_parse_observation(raw["observation"], context),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load(path: str | Path) -> Scenario:
    """
    Load a scenario from *path*, validate its structure, and return a
    :class:`Scenario`.  Raises :class:`ValueError` for schema violations.
    """
    file_path = Path(path)
    raw_bytes = file_path.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    try:
        data: dict[str, Any] = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Scenario file is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Scenario file must be a JSON object at the top level.")

    for key in ("scenario_name", "target", "request", "retry", "observation"):
        if key not in data:
            raise ValueError(f"Scenario is missing required top-level key: '{key}'")

    # target
    target = data["target"]
    if "base_url" not in target:
        raise ValueError("Scenario target is missing 'base_url'.")

    # request
    req = data["request"]
    for key in ("method", "path"):
        if key not in req:
            raise ValueError(f"Scenario request is missing required key: '{key}'")

    # retry
    retry = data["retry"]
    if "deliveries" not in retry:
        raise ValueError("Scenario retry is missing 'deliveries'.")
    deliveries = retry["deliveries"]
    if not isinstance(deliveries, int) or deliveries < 1:
        raise ValueError("retry.deliveries must be an integer >= 1.")

    # observation
    observation = _parse_observation(data["observation"], "observation")

    # controls (optional)
    controls: list[ControlSpec] = []
    for i, ctrl in enumerate(data.get("controls", [])):
        controls.append(_parse_control(ctrl, i))

    return Scenario(
        name=data["scenario_name"],
        base_url=target["base_url"].rstrip("/"),
        method=req["method"].upper(),
        path=req["path"],
        body=req.get("body"),
        deliveries=deliveries,
        observation=observation,
        controls=controls,
        sha256=sha256,
        raw_path=str(file_path),
    )
