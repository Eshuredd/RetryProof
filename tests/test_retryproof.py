"""
tests/test_retryproof.py — Unit tests for the RetryProof engine.

These tests exercise RetryProof itself.  They do NOT require the sample
FastAPI application to be running — all HTTP calls are replaced with fakes.

Coverage
--------
- valid scenario parsing
- invalid scenario rejection (multiple schema violations)
- scenario SHA-256 generation
- SQLiteCountObserver
- runner PASS evaluation
- runner FAIL evaluation
- evidence write and print
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
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

def _write_scenario(tmp_path: Path, data: dict[str, Any]) -> Path:
    """Write *data* as JSON to a temp file and return its path."""
    p = tmp_path / "scenario.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _minimal_scenario_data(**overrides) -> dict[str, Any]:
    """Return the minimal valid scenario dict, optionally patched."""
    base: dict[str, Any] = {
        "scenario_name": "test_scenario",
        "target": {"base_url": "http://localhost:9999"},
        "request": {"method": "POST", "path": "/test", "body": {"key": "val"}},
        "retry": {"deliveries": 3},
        "observation": {
            "type": "sqlite_count",
            "database": "test.db",
            "query": "SELECT COUNT(*) FROM tbl WHERE id = ?",
            "params": ["x"],
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
        assert scen.deliveries == 3
        assert scen.observation.expected == 1

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

    def test_controls_parsed(self, tmp_path):
        data = _minimal_scenario_data()
        data["controls"] = [
            {
                "label": "ctrl_1",
                "method": "POST",
                "path": "/ctrl",
                "body": None,
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
        assert scen.controls[0].observation.expected == 2

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
        )
        with pytest.raises(ValueError, match="Unknown observation type"):
            make_observer(spec)


# ---------------------------------------------------------------------------
# Runner — PASS / FAIL evaluation (HTTP mocked)
# ---------------------------------------------------------------------------

def _make_scenario(
    tmp_path: Path,
    db_path: str,
    deliveries: int = 3,
    expected: int = 1,
    query_param: str = "evt_x",
) -> Scenario:
    """Build a Scenario pointing at *db_path* without touching the network."""
    data: dict[str, Any] = {
        "scenario_name": "runner_test",
        "target": {"base_url": "http://localhost:9999"},
        "request": {"method": "POST", "path": "/test", "body": {"k": "v"}},
        "retry": {"deliveries": deliveries},
        "observation": {
            "type": "sqlite_count",
            "database": db_path,
            "query": "SELECT COUNT(*) FROM tbl WHERE id = ?",
            "params": [query_param],
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


class TestRunnerEvaluation:
    def _mock_response(self) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True}
        return resp

    def test_pass_when_observation_matches(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(tmp_path, db, deliveries=3, expected=1)

        mock_resp = self._mock_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = runner.run(scen)

        assert result["result"] == "PASS"
        assert result["observation"]["actual"] == 1
        assert result["observation"]["expected"] == 1
        assert result["observation"]["passed"] is True

    def test_fail_when_observation_mismatches(self, tmp_path):
        from retryproof import runner

        # DB has 3 rows but expected is 1 → FAIL
        db = _make_db_with_count(tmp_path, 3)
        scen = _make_scenario(tmp_path, db, deliveries=3, expected=1)

        mock_resp = self._mock_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = runner.run(scen)

        assert result["result"] == "FAIL"
        assert result["observation"]["actual"] == 3
        assert result["observation"]["passed"] is False

    def test_result_includes_delivery_log(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(tmp_path, db, deliveries=2, expected=1)

        mock_resp = self._mock_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = runner.run(scen)

        assert len(result["delivery_log"]) == 2

    def test_result_includes_required_fields(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(tmp_path, db)

        mock_resp = self._mock_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = runner.run(scen)

        for field in (
            "scenario_name",
            "scenario_sha256",
            "timestamp",
            "target",
            "request",
            "deliveries",
            "delivery_log",
            "observation",
            "controls",
            "result",
        ):
            assert field in result, f"Missing field: {field}"

    def test_scenario_sha256_in_result(self, tmp_path):
        from retryproof import runner

        db = _make_db_with_count(tmp_path, 1)
        scen = _make_scenario(tmp_path, db)

        mock_resp = self._mock_response()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = runner.run(scen)

        assert result["scenario_sha256"] == scen.sha256
        assert len(result["scenario_sha256"]) == 64


# ---------------------------------------------------------------------------
# Evidence generation
# ---------------------------------------------------------------------------

class TestEvidenceGeneration:
    def _make_result(self, verdict: str = "PASS") -> dict:
        return {
            "scenario_name": "test_evidence",
            "scenario_sha256": "a" * 64,
            "scenario_path": "scenarios/test.json",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "target": "http://localhost:9999",
            "request": {"method": "POST", "path": "/test", "body": None},
            "deliveries": 3,
            "delivery_log": [{"status_code": 200, "body": {}}] * 3,
            "observation": {
                "type": "sqlite_count",
                "query": "SELECT COUNT(*) FROM tbl",
                "params": [],
                "expected": 1,
                "actual": 1 if verdict == "PASS" else 3,
                "passed": verdict == "PASS",
            },
            "controls": [],
            "result": verdict,
        }

    def test_evidence_written_to_file(self, tmp_path):
        result = self._make_result("PASS")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        assert out_path.exists()
        assert out_path.suffix == ".json"

    def test_evidence_file_contains_valid_json(self, tmp_path):
        result = self._make_result("PASS")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        with open(out_path, encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["result"] == "PASS"
        assert saved["scenario_sha256"] == "a" * 64

    def test_evidence_file_named_after_scenario(self, tmp_path):
        result = self._make_result("PASS")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        assert "test_evidence" in out_path.name

    def test_evidence_pass_preserves_verdict(self, tmp_path):
        result = self._make_result("PASS")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        assert saved["result"] == "PASS"

    def test_evidence_fail_preserves_verdict(self, tmp_path):
        result = self._make_result("FAIL")
        out_path = evidence_mod.write(result, evidence_dir=tmp_path)
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        assert saved["result"] == "FAIL"

    def test_evidence_dir_created_if_absent(self, tmp_path):
        deep_dir = tmp_path / "a" / "b" / "c"
        assert not deep_dir.exists()
        result = self._make_result()
        evidence_mod.write(result, evidence_dir=deep_dir)
        assert deep_dir.exists()

    def test_print_summary_does_not_raise(self, capsys):
        result = self._make_result("PASS")
        evidence_mod.print_summary(result)
        captured = capsys.readouterr()
        assert "test_evidence" in captured.out
        assert "PASS" in captured.out
        assert "a" * 64 in captured.out
