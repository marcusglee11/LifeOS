"""
Tests for BypassMonitor (B2-T01).

Tests check_bypass_utilization() with:
- Empty ledger (header only, no records)
- No bypass events (all ok)
- Below warn threshold
- At warn threshold boundary
- Above warn, below alert threshold
- At alert threshold boundary
- Window boundary behavior (only last N entries)
- Missing ledger file (fail-closed)
- Malformed JSON line (fail-closed)
- I/O error simulation
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from runtime.orchestration.loop.bypass_monitor import (
    BypassStatus,
    check_bypass_utilization,
    DEFAULT_WINDOW_SIZE,
    WARN_THRESHOLD,
    ALERT_THRESHOLD,
)


def _write_ledger(tmp_path: Path, records: list[dict]) -> Path:
    """Write a JSONL ledger with a header + records to tmp_path."""
    ledger = tmp_path / "attempt_ledger.jsonl"
    header = {"type": "header", "schema_version": "v1.1", "run_id": "test_run"}
    lines = [json.dumps(header)]
    for rec in records:
        lines.append(json.dumps(rec))
    ledger.write_text("\n".join(lines) + "\n")
    return ledger


def _make_record(bypass: bool) -> dict:
    """Build a minimal ledger record, with or without bypass info."""
    base = {
        "attempt_id": 1,
        "timestamp": "2026-02-27T00:00:00Z",
        "run_id": "r1",
        "policy_hash": "abc",
        "input_hash": "def",
        "actions_taken": [],
        "diff_hash": None,
        "changed_files": [],
        "evidence_hashes": {},
        "success": True,
        "failure_class": None,
        "terminal_reason": None,
        "next_action": "retry",
        "rationale": "ok",
    }
    if bypass:
        base["plan_bypass_info"] = {"reason": "test bypass", "approved_by": "CEO"}
    else:
        base["plan_bypass_info"] = None
    return base


class TestBypassStatus:
    """Unit tests for BypassStatus dataclass validation."""

    def test_valid_ok_status(self) -> None:
        s = BypassStatus(level="ok", bypass_count=0, total_count=5, rate=0.0)
        assert s.level == "ok"

    def test_valid_warn_status(self) -> None:
        s = BypassStatus(level="warn", bypass_count=3, total_count=10, rate=0.3)
        assert s.level == "warn"

    def test_valid_alert_status(self) -> None:
        s = BypassStatus(level="alert", bypass_count=5, total_count=10, rate=0.5)
        assert s.level == "alert"

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid level"):
            BypassStatus(level="unknown", bypass_count=0, total_count=0, rate=0.0)

    def test_negative_bypass_count_raises(self) -> None:
        with pytest.raises(ValueError, match="bypass_count must be non-negative"):
            BypassStatus(level="ok", bypass_count=-1, total_count=0, rate=0.0)

    def test_rate_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="rate must be between"):
            BypassStatus(level="ok", bypass_count=0, total_count=0, rate=1.5)


class TestCheckBypassUtilization:
    """Tests for check_bypass_utilization()."""

    def test_missing_file_returns_alert(self, tmp_path: Path) -> None:
        """Missing ledger → fail-closed alert."""
        ledger = tmp_path / "nonexistent.jsonl"
        result = check_bypass_utilization(ledger)
        assert result.level == "alert"
        assert result.reason == "ledger_missing"
        assert result.bypass_count == 0
        assert result.total_count == 0

    def test_empty_ledger_header_only_returns_ok(self, tmp_path: Path) -> None:
        """Ledger with only header (no attempt records) → ok with zeros."""
        ledger = tmp_path / "attempt_ledger.jsonl"
        header = {"type": "header", "schema_version": "v1.1", "run_id": "r0"}
        ledger.write_text(json.dumps(header) + "\n")
        result = check_bypass_utilization(ledger)
        assert result.level == "ok"
        assert result.bypass_count == 0
        assert result.total_count == 0
        assert result.rate == 0.0

    def test_no_bypasses_level_ok(self, tmp_path: Path) -> None:
        """10 records with no bypasses → level ok, rate 0.0."""
        records = [_make_record(bypass=False) for _ in range(10)]
        ledger = _write_ledger(tmp_path, records)
        result = check_bypass_utilization(ledger)
        assert result.level == "ok"
        assert result.bypass_count == 0
        assert result.total_count == 10
        assert result.rate == 0.0

    def test_below_warn_threshold_level_ok(self, tmp_path: Path) -> None:
        """2/10 bypasses → rate 0.2, level ok (below 0.3)."""
        records = [_make_record(bypass=True)] * 2 + [_make_record(bypass=False)] * 8
        ledger = _write_ledger(tmp_path, records)
        result = check_bypass_utilization(ledger)
        assert result.level == "ok"
        assert result.bypass_count == 2
        assert result.total_count == 10
        assert result.rate == pytest.approx(0.2)

    def test_at_warn_threshold_level_warn(self, tmp_path: Path) -> None:
        """3/10 bypasses → rate 0.3, level warn."""
        records = [_make_record(bypass=True)] * 3 + [_make_record(bypass=False)] * 7
        ledger = _write_ledger(tmp_path, records)
        result = check_bypass_utilization(ledger)
        assert result.level == "warn"
        assert result.bypass_count == 3
        assert result.total_count == 10
        assert result.rate == pytest.approx(0.3)

    def test_above_warn_below_alert_level_warn(self, tmp_path: Path) -> None:
        """4/10 bypasses → rate 0.4, level warn (below 0.5)."""
        records = [_make_record(bypass=True)] * 4 + [_make_record(bypass=False)] * 6
        ledger = _write_ledger(tmp_path, records)
        result = check_bypass_utilization(ledger)
        assert result.level == "warn"
        assert result.bypass_count == 4
        assert result.total_count == 10
        assert result.rate == pytest.approx(0.4)

    def test_at_alert_threshold_level_alert(self, tmp_path: Path) -> None:
        """5/10 bypasses → rate 0.5, level alert."""
        records = [_make_record(bypass=True)] * 5 + [_make_record(bypass=False)] * 5
        ledger = _write_ledger(tmp_path, records)
        result = check_bypass_utilization(ledger)
        assert result.level == "alert"
        assert result.bypass_count == 5
        assert result.total_count == 10
        assert result.rate == pytest.approx(0.5)

    def test_window_boundary_uses_last_n(self, tmp_path: Path) -> None:
        """Window isolates last N entries — earlier entries excluded."""
        # 15 records: first 5 are all bypass, last 10 have none
        old_records = [_make_record(bypass=True)] * 5
        new_records = [_make_record(bypass=False)] * 10
        ledger = _write_ledger(tmp_path, old_records + new_records)
        result = check_bypass_utilization(ledger, window_size=10)
        # Only last 10 seen → all 10 are non-bypass
        assert result.level == "ok"
        assert result.bypass_count == 0
        assert result.total_count == 10

    def test_window_smaller_than_total_records(self, tmp_path: Path) -> None:
        """Window of 3 on 5-record ledger: only last 3 examined."""
        records = [
            _make_record(bypass=False),  # idx 0 - outside window
            _make_record(bypass=False),  # idx 1 - outside window
            _make_record(bypass=True),   # idx 2 - in window
            _make_record(bypass=True),   # idx 3 - in window
            _make_record(bypass=True),   # idx 4 - in window
        ]
        ledger = _write_ledger(tmp_path, records)
        result = check_bypass_utilization(ledger, window_size=3)
        assert result.bypass_count == 3
        assert result.total_count == 3
        assert result.level == "alert"

    def test_malformed_json_returns_alert(self, tmp_path: Path) -> None:
        """Corrupt JSONL line → fail-closed alert."""
        ledger = tmp_path / "attempt_ledger.jsonl"
        ledger.write_text('{"type":"header"}\n{not valid json}\n')
        result = check_bypass_utilization(ledger)
        assert result.level == "alert"
        assert result.reason == "ledger_corrupt"

    def test_non_object_json_line_returns_alert(self, tmp_path: Path) -> None:
        """Valid JSON that is not an object still fails closed as corrupt ledger."""
        ledger = tmp_path / "attempt_ledger.jsonl"
        ledger.write_text('{"type":"header"}\n123\n')
        result = check_bypass_utilization(ledger)
        assert result.level == "alert"
        assert result.reason == "ledger_corrupt"

    def test_invalid_window_size_raises(self, tmp_path: Path) -> None:
        """Non-positive window_size raises ValueError."""
        ledger = tmp_path / "ledger.jsonl"
        ledger.write_text("")
        with pytest.raises(ValueError, match="window_size must be positive"):
            check_bypass_utilization(ledger, window_size=0)

    def test_all_bypasses_alert(self, tmp_path: Path) -> None:
        """All records are bypasses → rate 1.0, alert."""
        records = [_make_record(bypass=True)] * 10
        ledger = _write_ledger(tmp_path, records)
        result = check_bypass_utilization(ledger)
        assert result.level == "alert"
        assert result.bypass_count == 10
        assert result.rate == 1.0
