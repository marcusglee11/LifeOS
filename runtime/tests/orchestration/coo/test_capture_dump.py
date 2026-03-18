from __future__ import annotations

import json

from runtime.orchestration.coo.commands import _maybe_capture_dump


def test_no_capture_when_env_unset(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("LIFEOS_COO_CAPTURE_DIR", raising=False)
    _maybe_capture_dump(
        mode="propose",
        raw_output="schema_version: task_proposal.v1",
        run_id="run-1",
        kind="task_proposal",
        parse_status="pass",
        parse_recovery_stage="direct",
        claim_violations=[],
    )
    assert list(tmp_path.iterdir()) == []


def test_capture_writes_json_when_env_set(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LIFEOS_COO_CAPTURE_DIR", str(tmp_path))
    _maybe_capture_dump(
        mode="propose",
        raw_output="schema_version: task_proposal.v1",
        run_id="run-1",
        kind="task_proposal",
        parse_status="pass",
        parse_recovery_stage="direct",
        claim_violations=[],
    )
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_capture_json_has_expected_keys(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LIFEOS_COO_CAPTURE_DIR", str(tmp_path))
    monkeypatch.setenv("LIFEOS_COO_CAPTURE_LABEL", "fixture")
    _maybe_capture_dump(
        mode="direct",
        raw_output="schema_version: escalation_packet.v1",
        run_id="run-2",
        kind="escalation_packet",
        parse_status="pass",
        parse_recovery_stage="direct",
        claim_violations=[],
    )
    payload = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    for key in ["capture_ts", "label", "mode", "run_id", "kind", "parse_status", "raw_output"]:
        assert key in payload
