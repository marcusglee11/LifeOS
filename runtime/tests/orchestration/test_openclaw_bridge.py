from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.orchestration.openclaw_bridge import (
    OPENCLAW_RESULT_KIND,
    OpenClawBridgeError,
    execute_openclaw_job,
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


def _sample_openclaw_job_payload() -> dict[str, object]:
    return {
        "kind": "lifeos.job.v0.1",
        "job_id": "JOB-900",
        "job_type": "build",
        "objective": "Execute bridged run",
        "scope": ["runtime/orchestration/*"],
        "non_goals": ["network"],
        "workdir": ".",
        "command": ["pytest", "-q"],
        "timeout_s": 120,
        "expected_artifacts": ["artifacts/terminal"],
        "context_refs": ["docs/11_admin/LIFEOS_STATE.md"],
    }


def test_execute_openclaw_job_terminal_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "artifacts" / "terminal").mkdir(parents=True)
    (repo_root / "artifacts" / "loop_state").mkdir(parents=True)

    terminal_path = repo_root / "artifacts" / "terminal" / "TP_run_900.yaml"
    terminal_path.write_text(
        "\n".join(
            [
                "run_id: run_900",
                "timestamp: '2026-02-18T12:00:00Z'",
                "outcome: PASS",
                "reason: pass",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo_root / "artifacts" / "loop_state" / "attempt_ledger.jsonl").write_text(
        "{\"attempt_id\": 1}\n",
        encoding="utf-8",
    )

    class FakeSpine:
        def __init__(self, *, repo_root: Path, use_worktree: bool, **_: object):
            assert repo_root == tmp_path.resolve()
            assert use_worktree is True

        def run(self, *, task_spec: dict[str, object], resume_from: object | None = None) -> dict[str, object]:
            assert isinstance(task_spec, dict)
            assert resume_from is None
            return {"state": "TERMINAL", "outcome": "PASS", "run_id": "run_900"}

    monkeypatch.setattr("runtime.orchestration.loop.spine.LoopSpine", FakeSpine)

    result = execute_openclaw_job(
        repo_root=repo_root,
        job_payload=_sample_openclaw_job_payload(),
    )

    assert result["kind"] == OPENCLAW_RESULT_KIND
    assert result["state"] == "terminal"
    assert result["outcome"] == "PASS"
    assert result["job_id"] == "JOB-900"
    assert result["terminal_packet_ref"] == "artifacts/terminal/TP_run_900.yaml"
    assert result["packet_refs"] == ["artifacts/terminal/TP_run_900.yaml"]
    assert result["ledger_refs"] == ["artifacts/loop_state/attempt_ledger.jsonl"]
    assert result["hash_manifest_ref"] == "artifacts/evidence/openclaw/jobs/JOB-900/hash_manifest.sha256"

    evidence_dir = repo_root / "artifacts" / "evidence" / "openclaw" / "jobs" / "JOB-900"
    ok, errors = verify_openclaw_evidence_contract(evidence_dir)
    assert ok is True
    assert errors == []


def test_execute_openclaw_job_checkpoint_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "artifacts" / "checkpoints").mkdir(parents=True)
    (repo_root / "artifacts" / "loop_state").mkdir(parents=True)

    checkpoint_path = repo_root / "artifacts" / "checkpoints" / "CP_run_901_2.yaml"
    checkpoint_path.write_text(
        "\n".join(
            [
                "run_id: run_901",
                "checkpoint_id: CP_run_901_2",
                "timestamp: '2026-02-18T12:01:00Z'",
                "trigger: ESCALATION_REQUESTED",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (repo_root / "artifacts" / "loop_state" / "attempt_ledger.jsonl").write_text(
        "{\"attempt_id\": 1}\n",
        encoding="utf-8",
    )

    class FakeSpine:
        def __init__(self, **_: object):
            pass

        def run(self, *, task_spec: dict[str, object], resume_from: object | None = None) -> dict[str, object]:
            assert isinstance(task_spec, dict)
            assert resume_from is None
            return {
                "state": "CHECKPOINT",
                "checkpoint_id": "CP_run_901_2",
                "run_id": "run_901",
            }

    monkeypatch.setattr("runtime.orchestration.loop.spine.LoopSpine", FakeSpine)

    result = execute_openclaw_job(
        repo_root=repo_root,
        job_payload=_sample_openclaw_job_payload(),
    )

    assert result["kind"] == OPENCLAW_RESULT_KIND
    assert result["state"] == "checkpoint"
    assert result["checkpoint_id"] == "CP_run_901_2"
    assert result["checkpoint_packet_ref"] == "artifacts/checkpoints/CP_run_901_2.yaml"
    assert result["packet_refs"] == ["artifacts/checkpoints/CP_run_901_2.yaml"]
    assert result["ledger_refs"] == ["artifacts/loop_state/attempt_ledger.jsonl"]


def test_execute_openclaw_job_blocks_when_terminal_packet_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakeSpine:
        def __init__(self, **_: object):
            pass

        def run(self, *, task_spec: dict[str, object], resume_from: object | None = None) -> dict[str, object]:
            assert isinstance(task_spec, dict)
            assert resume_from is None
            return {"state": "TERMINAL", "outcome": "PASS", "run_id": "run_missing"}

    monkeypatch.setattr("runtime.orchestration.loop.spine.LoopSpine", FakeSpine)

    result = execute_openclaw_job(
        repo_root=tmp_path,
        job_payload=_sample_openclaw_job_payload(),
    )

    assert result["kind"] == OPENCLAW_RESULT_KIND
    assert result["state"] == "terminal"
    assert result["outcome"] == "BLOCKED"
    assert "TERMINAL_PACKET_MISSING" in result["reason"]


def test_execute_openclaw_job_blocks_on_bridge_validation_error(tmp_path: Path) -> None:
    invalid_payload = dict(_sample_openclaw_job_payload())
    invalid_payload["kind"] = "invalid.kind"

    result = execute_openclaw_job(
        repo_root=tmp_path,
        job_payload=invalid_payload,
    )

    assert result["kind"] == OPENCLAW_RESULT_KIND
    assert result["state"] == "terminal"
    assert result["outcome"] == "BLOCKED"
    assert "OPENCLAW_BRIDGE_ERROR" in result["reason"]
