from __future__ import annotations

import pytest

from runtime.orchestration.openclaw_bridge import (
    OPENCLAW_RESULT_KIND,
    OpenClawBridgeError,
    map_openclaw_job_to_spine_invocation,
    map_spine_artifacts_to_openclaw_result,
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

