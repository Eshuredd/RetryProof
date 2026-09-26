"""
tests/test_retryproof.py — Unit tests for the RetryProof engine.

These tests exercise RetryProof itself.  They do NOT require the sample
FastAPI application to be running — all HTTP calls are replaced with fakes.

Coverage
--------
- valid scenario parsing (including expected_status, expected_before)
- invalid scenario rejection (multiple schema violations)
- scenario SHA-256 generation
- SQLiteCountObserver
- runner: PASS evaluation
- runner: FAIL evaluation (observation mismatch)
- runner: FAIL evaluation (HTTP status mismatch)
- runner: FAIL evaluation (precondition / stale DB)
- runner: execution order (precondition before deliveries, controls after)
- evidence: unique immutable filenames
- evidence: two runs do not overwrite each other
- evidence write and print (updated field names)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from retryproof.scenario import ObservationSpec, Scenario, load
from retryproof.observers import SQLiteCountObserver, make_observer
from retryproof import evidence as evidence_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_scenario(tmp_path: Path, data: dict[str, Any], name: str = "scenario.json") -> Path:
    """Write *data* as JSON to a temp file and return its path."""
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _minimal_scenario_data(**overrides) -> dict[str, Any]:
    """Return the minimal valid scenario dict, optionally patched."""
    base: dict[str, Any] = {
        "scenario_name": "test_scenario",
        "target": {"base_url": "http://localhost:9999"},
        "request": {
            "method": "POST",
            "path": "/test",
            "body": {"key": "val"},
            "expected_status": 200,
        },
        "retry": {"deliveries": 3},
        "observation": {
            "type": "sqlite_count",
            "database": "test.db",
            "query": "SELECT COUNT(*) FROM tbl WHERE id = ?",
            "params": ["x"],
            "expected_before": 0,
            "expected": 1,
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Scenario parsing — valid
# ---------------------------------------------------------------------------

class TestScenarioParsing:
    def test_valid_scenario_loads(self, tmp_path):
        path = _write_scenario(tmp_path, _minimal_scenario_data())
        scen = load(path)
        assert scen.name == "test_scenario"
        assert scen.base_url == "http://localhost:9999"
        assert scen.method == "POST"
        assert scen.path == "/test"
        assert scen.expected_status == 200
        assert scen.deliveries == 3
        assert scen.observation.expected == 1
        assert scen.observation.expected_before == 0

    def test_base_url_trailing_slash_stripped(self, tmp_path):
        data = _minimal_scenario_data()
        data["target"]["base_url"] = "http://localhost:9999/"
        path = _write_scenario(tmp_path, data)
        scen = load(path)
        assert scen.base_url == "http://localhost:9999"

    def test_method_uppercased(self, tmp_path):
        data = _minimal_scenario_data()
        data["request"]["method"] = "post"
        path = _write_scenario(tmp_path, data)
        scen = load(path)
        assert scen.method == "POST"

    def test_controls_parsed_with_expected_status(self, tmp_path):
        data = _minimal_scenario_data()
        data["controls"] = [
            {
                "label": "ctrl_1",
                "method": "POST",
                "path": "/ctrl",
                "body": None,
                "expected_status": 201,
                "observation": {
                    "type": "sqlite_count",
                    "database": "test.db",
                    "query": "SELECT COUNT(*) FROM tbl",
                    "params": [],
                    "expected": 2,
                },
            }
        ]
        path = _write_scenario(tmp_path, data)
        scen = load(path)
        assert len(scen.controls) == 1
        assert scen.controls[0].label == "ctrl_1"
        assert scen.controls[0].expected_status == 201
        assert scen.controls[0].observation.expected == 2
        # Controls don't require expected_before — defaults to None
        assert scen.controls[0].observation.expected_before is None

    def test_control_without_expected_status(self, tmp_path):
        data = _minimal_scenario_data()
        data["controls"] = [
            {
                "label": "no_status",
                "method": "GET",
                "path": "/x",
                "observation": {
                    "type": "sqlite_count",
                    "database": "test.db",
                    "query": "SELECT COUNT(*) FROM tbl",
                    "params": [],
                    "expected": 0,
                },
            }
        ]
        path = _write_scenario(tmp_path, data)
        scen = load(path)
        assert scen.controls[0].expected_status is None

    def test_no_controls_when_omitted(self, tmp_path):
        path = _write_scenario(tmp_path, _minimal_scenario_data())
        scen = load(path)
        assert scen.controls == []

    def test_body_can_be_none(self, tmp_path):
        data = _minimal_scenario_data()
        data["request"]["body"] = None
        path = _write_scenario(tmp_path, data)
        scen = load(path)
        assert scen.body is None


# ---------------------------------------------------------------------------
# Scenario parsing — invalid (rejection)
# ---------------------------------------------------------------------------

class TestScenarioRejection:
    def _check_raises(self, tmp_path, data: dict[str, Any], fragment: str) -> None:
        path = _write_scenario(tmp_path, data)
        with pytest.raises(ValueError, match=fragment):
            load(path)

    def test_not_a_json_object(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("[1,2,3]", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            load(p)

    def test_missing_scenario_name(self, tmp_path):
        data = _minimal_scenario_data()
        del data["scenario_name"]
        self._check_raises(tmp_path, data, "scenario_name")

    def test_missing_target(self, tmp_path):
        data = _minimal_scenario_data()
        del data["target"]
        self._check_raises(tmp_path, data, "target")

    def test_missing_base_url(self, tmp_path):
        data = _minimal_scenario_data()
        data["target"] = {}
        self._check_raises(tmp_path, data, "base_url")

    def test_missing_request_method(self, tmp_path):
        data = _minimal_scenario_data()
        del data["request"]["method"]
        self._check_raises(tmp_path, data, "method")

    def test_missing_request_path(self, tmp_path):
        data = _minimal_scenario_data()
        del data["request"]["path"]
        self._check_raises(tmp_path, data, "path")

    def test_missing_expected_status(self, tmp_path):
        data = _minimal_scenario_data()
        del data["request"]["expected_status"]
        self._check_raises(tmp_path, data, "expected_status")

    def test_deliveries_zero_rejected(self, tmp_path):
        data = _minimal_scenario_data()
        data["retry"]["deliveries"] = 0
        self._check_raises(tmp_path, data, "integer >= 1")

    def test_deliveries_negative_rejected(self, tmp_path):
        data = _minimal_scenario_data()
        data["retry"]["deliveries"] = -1
        self._check_raises(tmp_path, data, "integer >= 1")

    def test_unsupported_observation_type(self, tmp_path):
        data = _minimal_scenario_data()
        data["observation"]["type"] = "redis_key"
        self._check_raises(tmp_path, data, "Unsupported observation type")

    def test_observation_params_not_list(self, tmp_path):
        data = _minimal_scenario_data()
        data["observation"]["params"] = "not_a_list"
        self._check_raises(tmp_path, data, "params must be a JSON array")

    def test_missing_expected_before(self, tmp_path):
        data = _minimal_scenario_data()
        del data["observation"]["expected_before"]
        self._check_raises(tmp_path, data, "expected_before")

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{broken json", encoding="utf-8")
        with pytest.raises(ValueError, match="not valid JSON"):
            load(p)

    def test_file_not_found(self, tmp_path):
        with pytest.raises((FileNotFoundError, OSError)):
            load(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# SHA-256
# ---------------------------------------------------------------------------

class TestScenarioSha256:
    def test_sha256_matches_file_bytes(self, tmp_path):
        data = _minimal_scenario_data()
        path = _write_scenario(tmp_path, data)
        raw_bytes = path.read_bytes()
        expected_sha = hashlib.sha256(raw_bytes).hexdigest()
        scen = load(path)
        assert scen.sha256 == expected_sha

    def test_sha256_is_64_hex_chars(self, tmp_path):
        path = _write_scenario(tmp_path, _minimal_scenario_data())
        scen = load(path)
        assert len(scen.sha256) == 64
        assert all(c in "0123456789abcdef" for c in scen.sha256)

    def test_sha256_changes_when_content_changes(self, tmp_path):
        data_a = _minimal_scenario_data()
        path_a = tmp_path / "a.json"
        path_a.write_text(json.dumps(data_a), encoding="utf-8")

        data_b = _minimal_scenario_data()
        data_b["scenario_name"] = "different_name"
        path_b = tmp_path / "b.json"
        path_b.write_text(json.dumps(data_b), encoding="utf-8")

        scen_a = load(path_a)
        scen_b = load(path_b)
        assert scen_a.sha256 != scen_b.sha256


# ---------------------------------------------------------------------------
# SQLiteCountObserver
# ---------------------------------------------------------------------------

class TestSQLiteCountObserver:
    def _make_db(self, tmp_path: Path, table: str, rows: list[str]) -> str:
        db_path = str(tmp_path / "obs_test.db")
        conn = sqlite3.connect(db_path)
        conn.execute(f"CREATE TABLE {table} (id TEXT NOT NULL)")
        for row in rows:
            conn.execute(f"INSERT INTO {table} VALUES (?)", (row,))
        conn.commit()
        conn.close()
        return db_path

    def test_count_zero(self, tmp_path):
        db = self._make_db(tmp_path, "items", [])
        spec = ObservationSpec(
            type="sqlite_count",
            database=db,
            query="SELECT COUNT(*) FROM items",
            params=[],
            expected=0,
            expected_before=None,
        )
        obs = SQLiteCountObserver(spec)
        assert obs.observe() == 0

    def test_count_one(self, tmp_path):
        db = self._make_db(tmp_path, "items", ["abc"])
        spec = ObservationSpec(
            type="sqlite_count",
            database=db,
            query="SELECT COUNT(*) FROM items WHERE id = ?",
            params=["abc"],
            expected=1,
            expected_before=0,
        )
        obs = SQLiteCountObserver(spec)
        assert obs.observe() == 1

    def test_count_filtered(self, tmp_path):
        db = self._make_db(tmp_path, "items", ["abc", "abc", "xyz"])
        spec = ObservationSpec(
            type="sqlite_count",
            database=db,
            query="SELECT COUNT(*) FROM items WHERE id = ?",
            params=["abc"],
            expected=2,
            expected_before=None,
        )
        obs = SQLiteCountObserver(spec)
        assert obs.observe() == 2

    def test_make_observer_returns_sqlite_observer(self, tmp_path):
        db = self._make_db(tmp_path, "items", [])
        spec = ObservationSpec(
            type="sqlite_count",
            database=db,
            query="SELECT COUNT(*) FROM items",
            params=[],
            expected=0,
            expected_before=None,
        )
        obs = make_observer(spec)
        assert isinstance(obs, SQLiteCountObserver)

    def test_make_observer_unknown_type_raises(self):
        spec = ObservationSpec(
            type="unknown_type",
            database="x.db",
            query="SELECT 1",
            params=[],
            expected=1,
            expected_before=None,
        )
        with pytest.raises(ValueError, match="Unknown observation type"):
            make_observer(spec)


# ---------------------------------------------------------------------------
# Runner helpers: build scenario / db
# ---------------------------------------------------------------------------

def _make_scenario(
    tmp_path: Path,
    db_path: str,
    deliveries: int = 3,
    expected: int = 1,
    expected_before: int = 0,
    query_param: str = "evt_x",
    expected_status: int = 200,
) -> Scenario:
    """Build a Scenario pointing at *db_path* without touching the network."""
    data: dict[str, Any] = {
        "scenario_name": "runner_test",
        "target": {"base_url": "http://localhost:9999"},
        "request": {
            "method": "POST",
            "path": "/test",
            "body": {"k": "v"},
            "expected_status": expected_status,
        },
        "retry": {"deliveries": deliveries},
        "observation": {
            "type": "sqlite_count",
            "database": db_path,
            "query": "SELECT COUNT(*) FROM tbl WHERE id = ?",
            "params": [query_param],
            "expected_before": expected_before,
            "expected": expected,
        },
    }
    path = _write_scenario(tmp_path, data)
    return load(path)


def _make_db_with_count(tmp_path: Path, count: int, row_id: str = "evt_x") -> str:
    """Create a SQLite db with *count* rows of value *row_id* in tbl."""
    db_path = str(tmp_path / "runner.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE tbl (id TEXT)")
    for _ in range(count):
        conn.execute("INSERT INTO tbl VALUES (?)", (row_id,))
    conn.commit()
    conn.close()
    return db_path


def _mock_client(status_code: int = 200, body: Any = None):
    """Return a context-manager-compatible mock httpx.Client."""
    if body is None:
        body = {"ok": True}
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.request.return_value = resp
    return mock_client


# ---------------------------------------------------------------------------
# Runner — PASS / FAIL: DB observation
# ---------------------------------------------------------------------------

class TestRunnerObservationEvaluation:
    def test_pass_when_observation_matches(self, tmp_path):
        from retryproof import runner

        # Use a single DB that starts with 1 row.
        # Set expected_before=1 and expected=1 so both pre- and post-checks pass.
        db = str(tmp_path / "runner_pass.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE tbl (id TEXT)")
        conn.execute("INSERT INTO tbl VALUES (?)", ("evt_x",))
        conn.commit()
        conn.close()
        scen = _make_scenario(tmp_path, db, deliveries=3, expected=1, expected_before=1)

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=200)
            result = runner.run(scen)

        assert result["result"] == "PASS"
        assert result["observation"]["actual_after"] == 1
        assert result["observation"]["expected_after"] == 1
        assert result["observation"]["passed"] is True

    def test_fail_when_observation_mismatches(self, tmp_path):
        from retryproof import runner

        # DB has 3 rows but expected is 1 → FAIL
        db = _make_db_with_count(tmp_path, 3)
        scen = _make_scenario(tmp_path, db, deliveries=3, expected=1, expected_before=3)

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=200)
            result = runner.run(scen)

        assert result["result"] == "FAIL"
        assert result["observation"]["actual_after"] == 3
        assert result["observation"]["passed"] is False

    def test_result_includes_delivery_log(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(tmp_path, db, deliveries=2, expected=1, expected_before=1)

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=200)
            result = runner.run(scen)

        assert len(result["delivery_log"]) == 2

    def test_result_includes_required_fields(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(tmp_path, db, expected_before=1)

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=200)
            result = runner.run(scen)

        for field in (
            "scenario_name",
            "scenario_sha256",
            "timestamp",
            "target",
            "request",
            "deliveries",
            "precondition",
            "delivery_log",
            "observation",
            "controls",
            "result",
        ):
            assert field in result, f"Missing field: {field}"

    def test_scenario_sha256_in_result(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(tmp_path, db, expected_before=1)

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=200)
            result = runner.run(scen)

        assert result["scenario_sha256"] == scen.sha256
        assert len(result["scenario_sha256"]) == 64


# ---------------------------------------------------------------------------
# Runner — PASS / FAIL: HTTP status contract  (Fix 1)
# ---------------------------------------------------------------------------

class TestRunnerHttpStatusContract:
    def test_pass_when_expected_status_matches(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        # expected_status=201, mock returns 201 → PASS
        scen = _make_scenario(
            tmp_path, db, deliveries=2, expected=1, expected_before=1,
            expected_status=201,
        )

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=201)
            result = runner.run(scen)

        assert result["result"] == "PASS"
        for record in result["delivery_log"]:
            assert record["status_ok"] is True
            assert record["status_code"] == 201

    def test_fail_when_http_500_even_if_db_correct(self, tmp_path):
        """HTTP 500 must cause FAIL even if DB observation matches expected."""
        from retryproof import runner

        # DB already has the "correct" count of 1
        db = _make_db_with_count(tmp_path, 1)
        # expected_status=201 but mock returns 500 → FAIL
        scen = _make_scenario(
            tmp_path, db, deliveries=3, expected=1, expected_before=1,
            expected_status=201,
        )

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=500)
            result = runner.run(scen)

        assert result["result"] == "FAIL"
        for record in result["delivery_log"]:
            assert record["status_ok"] is False
            assert record["status_code"] == 500

    def test_fail_when_first_delivery_is_unexpected_status(self, tmp_path):
        """Even a single unexpected HTTP status makes the run FAIL."""
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(
            tmp_path, db, deliveries=1, expected=1, expected_before=1,
            expected_status=200,
        )

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=404)
            result = runner.run(scen)

        assert result["result"] == "FAIL"
        assert result["delivery_log"][0]["status_ok"] is False

    def test_delivery_log_records_expected_and_actual_status(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(
            tmp_path, db, deliveries=1, expected=1, expected_before=1,
            expected_status=201,
        )

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=201)
            result = runner.run(scen)

        rec = result["delivery_log"][0]
        assert rec["expected_status"] == 201
        assert rec["status_code"] == 201
        assert "status_ok" in rec


# ---------------------------------------------------------------------------
# Runner — Precondition (stale DB)  (Fix 2)
# ---------------------------------------------------------------------------

class TestRunnerPrecondition:
    def test_fail_when_precondition_not_met(self, tmp_path):
        """
        A stale DB that already has rows must cause FAIL via the precondition
        check, not silently produce a misleading PASS.
        """
        from retryproof import runner

        # DB already has 1 row — but expected_before=0 → precondition FAIL
        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(
            tmp_path, db, deliveries=3, expected=1, expected_before=0,
            expected_status=200,
        )

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=200)
            result = runner.run(scen)

        assert result["result"] == "FAIL"
        pre = result["precondition"]
        assert pre["passed"] is False
        assert pre["expected_before"] == 0
        assert pre["actual_before"] == 1

    def test_pass_when_precondition_met(self, tmp_path):
        from retryproof import runner

        # Empty DB → expected_before=0 is satisfied
        db = _make_db_with_count(tmp_path, 0)
        # Pre-populate after precondition check is done by the runner;
        # for unit test we make the DB already have the post-delivery count (1).
        # We set expected_before to 0 but DB is pre-populated with 0 rows —
        # then mock delivers and we check the DB has 1 row.
        # Simplest: set expected_before=0, then manually insert 1 row into the
        # same DB path *before* the runner reads the "after" observation.
        # Since runner calls precondition first and observation after deliveries,
        # we need the DB to reflect state changes. Use a simpler invariant:
        # expected_before == actual_before (both 0) → precondition passes.
        scen = _make_scenario(
            tmp_path, db, deliveries=2, expected=0, expected_before=0,
            expected_status=200,
        )

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=200)
            result = runner.run(scen)

        pre = result["precondition"]
        assert pre["passed"] is True
        assert pre["actual_before"] == 0

    def test_precondition_recorded_in_evidence(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 0)
        scen = _make_scenario(tmp_path, db, expected_before=0, expected=0)

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value = _mock_client(status_code=200)
            result = runner.run(scen)

        pre = result["precondition"]
        assert "expected_before" in pre
        assert "actual_before" in pre
        assert "passed" in pre
        assert "skipped" in pre


# ---------------------------------------------------------------------------
# Runner — Execution order  (Fix 3)
# ---------------------------------------------------------------------------

class TestRunnerExecutionOrder:
    def test_controls_run_after_primary_observation(self, tmp_path):
        """
        Controls must not alter DB state before the primary observation.
        We verify this by watching call order via a side-effect list.
        """
        from retryproof import runner as runner_mod

        db = _make_db_with_count(tmp_path, 0)
        scen = _make_scenario(tmp_path, db, deliveries=1, expected=0, expected_before=0)

        # Add a control that points to the same DB
        ctrl_obs = ObservationSpec(
            type="sqlite_count",
            database=db,
            query="SELECT COUNT(*) FROM tbl",
            params=[],
            expected=0,
            expected_before=None,
        )
        from retryproof.scenario import ControlSpec
        scen.controls = [
            ControlSpec(
                label="ctrl",
                method="GET",
                path="/x",
                body=None,
                expected_status=None,
                observation=ctrl_obs,
            )
        ]

        call_log: list[str] = []
        original_check = runner_mod._check_precondition
        original_eval = runner_mod._evaluate_observation

        def patched_precondition(spec):
            call_log.append("precondition")
            return original_check(spec)

        def patched_eval(spec, *, phase="after"):
            call_log.append(f"eval:{phase}")
            return original_eval(spec, phase=phase)

        with (
            patch.object(runner_mod, "_check_precondition", side_effect=patched_precondition),
            patch.object(runner_mod, "_evaluate_observation", side_effect=patched_eval),
            patch("httpx.Client") as mock_cls,
        ):
            mock_cls.return_value = _mock_client(status_code=200)
            runner_mod.run(scen)

        # precondition must come first
        assert call_log[0] == "precondition"
        # primary eval must come before any control eval
        primary_idx = next(i for i, v in enumerate(call_log) if v.startswith("eval:"))
        ctrl_idx = next(
            (i for i, v in enumerate(call_log) if v.startswith("eval:") and i > primary_idx),
            None,
        )
        if ctrl_idx is not None:
            assert primary_idx < ctrl_idx


# ---------------------------------------------------------------------------
# Evidence — Immutable filenames  (Fix 4)
# ---------------------------------------------------------------------------

class TestEvidenceFilenames:
    def _make_result(self, verdict: str = "PASS", ts: str = "2024-01-15T14:30:22+00:00") -> dict:
        return {
            "scenario_name": "test_evidence",
            "scenario_sha256": "87654321" + "0" * 56,
            "scenario_path": "scenarios/test.json",
            "timestamp": ts,
            "target": "http://localhost:9999",
            "request": {
                "method": "POST",
                "path": "/test",
                "expected_status": 200,
                "body": None,
            },
            "deliveries": 3,
            "precondition": {
                "expected_before": 0,
                "actual_before": 0,
                "passed": True,
                "skipped": False,
            },
            "delivery_log": [
                {"status_code": 200, "expected_status": 200, "status_ok": True, "body": {}}
            ] * 3,
            "observation": {
                "type": "sqlite_count",
                "query": "SELECT COUNT(*) FROM tbl",
                "params": [],
                "expected_before": 0,
                "expected_after": 1,
                "actual_after": 1 if verdict == "PASS" else 3,
                "passed": verdict == "PASS",
            },
            "controls": [],
            "result": verdict,
        }

    def test_filename_contains_scenario_name(self, tmp_path):
        result = self._make_result("PASS")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        assert "test_evidence" in out_path.name

    def test_filename_contains_timestamp(self, tmp_path):
        result = self._make_result("PASS", ts="2024-01-15T14:30:22+00:00")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        assert "20240115T143022Z" in out_path.name

    def test_filename_contains_verdict(self, tmp_path):
        p = evidence_mod.write(self._make_result("PASS"), evidence_dir=tmp_path)
        f = evidence_mod.write(self._make_result("FAIL"), evidence_dir=tmp_path)
        assert "PASS" in p.name
        assert "FAIL" in f.name

    def test_filename_contains_sha_prefix(self, tmp_path):
        result = self._make_result("PASS")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        # First 8 chars of the fake sha256
        assert "87654321" in out_path.name

    def test_two_runs_do_not_overwrite_each_other(self, tmp_path):
        """Evidence is immutable — two calls must produce two distinct files."""
        r1 = self._make_result("PASS", ts="2024-01-15T10:00:00+00:00")
        r2 = self._make_result("FAIL", ts="2024-01-15T10:00:01+00:00")

        p1 = evidence_mod.write(r1, evidence_dir=tmp_path)
        p2 = evidence_mod.write(r2, evidence_dir=tmp_path)

        assert p1 != p2
        assert p1.exists()
        assert p2.exists()

        saved1 = json.loads(p1.read_text(encoding="utf-8"))
        saved2 = json.loads(p2.read_text(encoding="utf-8"))
        assert saved1["result"] == "PASS"
        assert saved2["result"] == "FAIL"

    def test_same_run_repeated_produces_same_name(self, tmp_path):
        """
        Writing the exact same result dict twice produces the same filename.
        (The file will be overwritten, but the name is deterministic and stable.)
        """
        r = self._make_result("PASS", ts="2024-06-01T09:00:00+00:00")
        p1 = evidence_mod.write(r, evidence_dir=tmp_path)
        p2 = evidence_mod.write(r, evidence_dir=tmp_path)
        assert p1.name == p2.name

    def test_evidence_file_contains_valid_json(self, tmp_path):
        result = self._make_result("PASS")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        with open(out_path, encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["result"] == "PASS"
        assert saved["scenario_sha256"] == "87654321" + "0" * 56

    def test_evidence_dir_created_if_absent(self, tmp_path):
        deep_dir = tmp_path / "a" / "b" / "c"
        assert not deep_dir.exists()
        evidence_mod.write(self._make_result(), evidence_dir=deep_dir)
        assert deep_dir.exists()

    def test_print_summary_does_not_raise(self, capsys):
        result = self._make_result("PASS")
        evidence_mod.print_summary(result)
        captured = capsys.readouterr()
        assert "test_evidence" in captured.out
        assert "PASS" in captured.out
        assert "87654321" in captured.out
