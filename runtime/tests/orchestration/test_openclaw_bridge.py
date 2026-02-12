from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.orchestration.openclaw_bridge import (
    OPENCLAW_RESULT_KIND,
    OpenClawBridgeError,
    map_openclaw_job_to_spine_invocation,
    map_spine_artifacts_to_openclaw_result,
    resolve_openclaw_job_evidence_dir,
    verify_openclaw_evidence_contract,
    write_openclaw_evidence_contract,
)


def test_map_openclaw_job_to_spine_invocation_success() -> None:
    job_payload = {
        "kind": "lifeos.job.v0.1",
        "job_id": "JOB-001",
        "job_type": "build",
        "objective": "Implement bridge mapping",
        "scope": ["tests only"],
        "non_goals": ["no network"],
        "workdir": ".",
        "command": ["pytest", "-q", "runtime/tests/orchestration/test_openclaw_bridge.py"],
        "timeout_s": 900,
        "expected_artifacts": ["stdout.txt", "stderr.txt"],
        "context_refs": ["docs/11_admin/LIFEOS_STATE.md"],
    }

    payload = map_openclaw_job_to_spine_invocation(job_payload)

    assert payload["job_id"] == "JOB-001"
    assert payload["run_id"] == "openclaw:JOB-001"
    assert payload["task_spec"]["source"] == "openclaw"
    assert payload["task_spec"]["constraints"]["timeout_s"] == 900
    assert payload["task_spec"]["command"][0] == "pytest"


def test_map_openclaw_job_to_spine_invocation_invalid_kind() -> None:
    with pytest.raises(OpenClawBridgeError, match="unsupported job kind"):
        map_openclaw_job_to_spine_invocation(
            {
                "kind": "unsupported",
                "job_id": "J1",
                "job_type": "build",
                "objective": "x",
                "workdir": ".",
                "command": ["pytest"],
                "timeout_s": 1,
            }
        )


def test_map_spine_terminal_to_openclaw_result_success() -> None:
    terminal_packet = {
        "run_id": "run-123",
        "timestamp": "2026-02-12T12:00:00Z",
        "outcome": "PASS",
        "reason": "pass",
    }

    result = map_spine_artifacts_to_openclaw_result(
        job_id="JOB-001",
        terminal_packet=terminal_packet,
        terminal_packet_ref="artifacts/terminal/TP_run-123.yaml",
    )

    assert result["kind"] == OPENCLAW_RESULT_KIND
    assert result["job_id"] == "JOB-001"
    assert result["state"] == "terminal"
    assert result["terminal_packet_ref"] == "artifacts/terminal/TP_run-123.yaml"
    assert result["packet_refs"] == []
    assert result["ledger_refs"] == []


def test_map_spine_checkpoint_to_openclaw_result_success() -> None:
    checkpoint_packet = {
        "run_id": "run-123",
        "checkpoint_id": "CP_123",
        "timestamp": "2026-02-12T12:00:00Z",
        "trigger": "ESCALATION_REQUESTED",
    }
    result = map_spine_artifacts_to_openclaw_result(
        job_id="JOB-001",
        checkpoint_packet=checkpoint_packet,
        checkpoint_packet_ref="artifacts/checkpoints/CP_123.yaml",
    )

    assert result["state"] == "checkpoint"
    assert result["checkpoint_id"] == "CP_123"
    assert result["checkpoint_packet_ref"] == "artifacts/checkpoints/CP_123.yaml"


def test_map_spine_result_rejects_ambiguous_inputs() -> None:
    with pytest.raises(OpenClawBridgeError, match="exactly one"):
        map_spine_artifacts_to_openclaw_result(
            job_id="JOB-001",
            terminal_packet={"run_id": "r", "timestamp": "t", "outcome": "PASS", "reason": "pass"},
            checkpoint_packet={"run_id": "r", "timestamp": "t", "trigger": "x", "checkpoint_id": "cp"},
        )


def test_resolve_openclaw_job_evidence_dir_is_deterministic(tmp_path: Path) -> None:
    expected = tmp_path / "artifacts" / "evidence" / "openclaw" / "jobs" / "JOB-009"
    assert resolve_openclaw_job_evidence_dir(tmp_path, "JOB-009") == expected


def test_write_and_verify_openclaw_evidence_contract(tmp_path: Path) -> None:
    written = write_openclaw_evidence_contract(
        repo_root=tmp_path,
        job_id="JOB-777",
        packet_refs=["artifacts/terminal/TP_run-777.yaml"],
        ledger_refs=["artifacts/loop_state/attempt_ledger.jsonl"],
    )

    evidence_dir = Path(written["evidence_dir"])
    assert evidence_dir == tmp_path / "artifacts" / "evidence" / "openclaw" / "jobs" / "JOB-777"

    packet_refs_payload = json.loads((evidence_dir / "packet_refs.json").read_text(encoding="utf-8"))
    ledger_refs_payload = json.loads((evidence_dir / "ledger_refs.json").read_text(encoding="utf-8"))
    assert packet_refs_payload["packet_refs"] == ["artifacts/terminal/TP_run-777.yaml"]
    assert ledger_refs_payload["ledger_refs"] == ["artifacts/loop_state/attempt_ledger.jsonl"]

    ok, errors = verify_openclaw_evidence_contract(evidence_dir)
    assert ok is True
    assert errors == []


def test_verify_openclaw_evidence_contract_fails_when_required_file_missing(tmp_path: Path) -> None:
    written = write_openclaw_evidence_contract(
        repo_root=tmp_path,
        job_id="JOB-778",
        packet_refs=["artifacts/terminal/TP_run-778.yaml"],
        ledger_refs=["artifacts/loop_state/attempt_ledger.jsonl"],
    )

    evidence_dir = Path(written["evidence_dir"])
    (evidence_dir / "packet_refs.json").unlink()
    ok, errors = verify_openclaw_evidence_contract(evidence_dir)
    assert ok is False
    assert any("packet_refs.json" in error for error in errors)


def test_verify_openclaw_evidence_contract_reports_corrupt_json(tmp_path: Path) -> None:
    written = write_openclaw_evidence_contract(
        repo_root=tmp_path,
        job_id="JOB-779",
        packet_refs=["artifacts/terminal/TP_run-779.yaml"],
        ledger_refs=["artifacts/loop_state/attempt_ledger.jsonl"],
    )

    evidence_dir = Path(written["evidence_dir"])
    (evidence_dir / "packet_refs.json").write_text("{not-json}\n", encoding="utf-8")
    ok, errors = verify_openclaw_evidence_contract(evidence_dir)
    assert ok is False
    assert any("packet_refs.json is not valid JSON" == error for error in errors)


@pytest.mark.parametrize(
    "job_id",
    [
        "",
        "   ",
        "../escape",
        "..\\escape",
        "bad/job",
        "bad\\job",
        "bad*char",
    ],
)
def test_resolve_openclaw_job_evidence_dir_rejects_invalid_job_id(
    tmp_path: Path, job_id: str
) -> None:
    with pytest.raises(OpenClawBridgeError):
        resolve_openclaw_job_evidence_dir(tmp_path, job_id)
