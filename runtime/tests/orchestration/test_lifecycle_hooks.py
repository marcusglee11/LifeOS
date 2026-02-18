"""Tests for lifecycle hooks — pre-run and post-run governance gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from runtime.orchestration.loop.lifecycle_hooks import (
    HookResult,
    HookSequenceResult,
    check_policy_hash_present,
    check_envelope_constraints,
    check_protected_paths,
    check_terminal_packet_present,
    check_ledger_append_success,
    check_evidence_completeness,
    run_hook_sequence,
    run_pre_hooks,
    run_post_hooks,
)


# ---------------------------------------------------------------------------
# Pre-run hook unit tests
# ---------------------------------------------------------------------------


class TestPolicyHashPresent:
    def test_passes_when_hash_provided(self) -> None:
        result = check_policy_hash_present(policy_hash="abc123")
        assert result.passed
        assert result.name == "policy_hash_present"

    def test_fails_when_hash_missing(self) -> None:
        result = check_policy_hash_present(policy_hash=None)
        assert not result.passed

    def test_fails_when_hash_empty(self) -> None:
        result = check_policy_hash_present(policy_hash="")
        assert not result.passed


class TestEnvelopeConstraints:
    def test_passes_with_valid_paths(self, tmp_path: Path) -> None:
        result = check_envelope_constraints(
            scope_paths=["runtime/foo.py"],
            repo_root=tmp_path,
            allowed_paths=["runtime/*"],
            denied_paths=[],
        )
        assert result.passed

    def test_fails_on_denied_path(self, tmp_path: Path) -> None:
        result = check_envelope_constraints(
            scope_paths=["docs/00_foundations/constitution.md"],
            repo_root=tmp_path,
            allowed_paths=["**"],
            denied_paths=["docs/00_foundations/*"],
        )
        assert not result.passed
        assert "envelope violations" in result.reason

    def test_passes_when_no_scope_paths(self, tmp_path: Path) -> None:
        result = check_envelope_constraints(
            scope_paths=[],
            repo_root=tmp_path,
            allowed_paths=[],
            denied_paths=[],
        )
        assert result.passed


class TestProtectedPaths:
    def test_passes_on_safe_paths(self) -> None:
        result = check_protected_paths(scope_paths=["runtime/orchestration/loop/spine.py"])
        assert result.passed

    def test_fails_on_protected_path(self) -> None:
        result = check_protected_paths(scope_paths=["docs/00_foundations/LifeOS_Constitution_v2.0.md"])
        assert not result.passed
        assert "protected path violations" in result.reason

    def test_passes_when_empty(self) -> None:
        result = check_protected_paths(scope_paths=[])
        assert result.passed


# ---------------------------------------------------------------------------
# Post-run hook unit tests
# ---------------------------------------------------------------------------


class TestTerminalPacketPresent:
    def test_passes_when_file_exists(self, tmp_path: Path) -> None:
        pkt = tmp_path / "TP_run1.yaml"
        pkt.write_text("outcome: PASS")
        result = check_terminal_packet_present(terminal_packet_path=pkt)
        assert result.passed

    def test_fails_when_file_missing(self, tmp_path: Path) -> None:
        result = check_terminal_packet_present(terminal_packet_path=tmp_path / "missing.yaml")
        assert not result.passed

    def test_fails_when_path_none(self) -> None:
        result = check_terminal_packet_present(terminal_packet_path=None)
        assert not result.passed


class TestLedgerAppendSuccess:
    def test_passes_on_true(self) -> None:
        assert check_ledger_append_success(ledger_write_ok=True).passed

    def test_fails_on_false(self) -> None:
        assert not check_ledger_append_success(ledger_write_ok=False).passed


class TestEvidenceCompleteness:
    def test_skipped_when_no_dir(self) -> None:
        result = check_evidence_completeness(evidence_dir=None)
        assert result.passed
        assert "skipped" in result.reason

    def test_fails_when_dir_missing(self, tmp_path: Path) -> None:
        result = check_evidence_completeness(evidence_dir=tmp_path / "nonexistent")
        assert not result.passed

    def test_fails_when_files_missing(self, tmp_path: Path) -> None:
        edir = tmp_path / "evidence"
        edir.mkdir()
        result = check_evidence_completeness(evidence_dir=edir, evidence_tier="light")
        assert not result.passed
        assert "EVIDENCE_MISSING" in result.reason


# ---------------------------------------------------------------------------
# Sequence runner tests
# ---------------------------------------------------------------------------


def _hook_pass(**_: Any) -> HookResult:
    return HookResult(name="stub_pass", passed=True, reason="ok")


def _hook_fail(**_: Any) -> HookResult:
    return HookResult(name="stub_fail", passed=False, reason="intentional failure")


def _hook_raises(**_: Any) -> HookResult:
    raise RuntimeError("boom")


class TestHookSequenceResult:
    def test_all_passed_true(self) -> None:
        seq = HookSequenceResult(phase="test")
        seq.results = [HookResult(name="a", passed=True, reason="ok")]
        assert seq.all_passed

    def test_all_passed_false(self) -> None:
        seq = HookSequenceResult(phase="test")
        seq.results = [
            HookResult(name="a", passed=True, reason="ok"),
            HookResult(name="b", passed=False, reason="nope"),
        ]
        assert not seq.all_passed

    def test_failed_hooks_property(self) -> None:
        seq = HookSequenceResult(phase="test")
        seq.results = [
            HookResult(name="a", passed=True, reason="ok"),
            HookResult(name="b", passed=False, reason="nope"),
        ]
        assert len(seq.failed_hooks) == 1
        assert seq.failed_hooks[0].name == "b"


class TestRunHookSequence:
    def test_all_pass(self) -> None:
        seq = run_hook_sequence([_hook_pass, _hook_pass], "test", {})
        assert seq.all_passed
        assert len(seq.results) == 2

    def test_mixed_results_no_short_circuit(self) -> None:
        """All hooks run even after one fails."""
        seq = run_hook_sequence([_hook_fail, _hook_pass], "test", {})
        assert not seq.all_passed
        assert len(seq.results) == 2  # Both ran

    def test_exception_captured(self) -> None:
        seq = run_hook_sequence([_hook_raises], "test", {})
        assert not seq.all_passed
        assert "hook raised" in seq.results[0].reason


class TestPreRunRunner:
    def test_custom_hooks(self) -> None:
        seq = run_pre_hooks({}, hooks=[_hook_pass])
        assert seq.all_passed
        assert seq.phase == "pre_run"


class TestPostRunRunner:
    def test_custom_hooks(self) -> None:
        seq = run_post_hooks({}, hooks=[_hook_fail])
        assert not seq.all_passed
        assert seq.phase == "post_run"


# ---------------------------------------------------------------------------
# Spine integration tests for resume() + post-run hooks
# ---------------------------------------------------------------------------


class TestResumePostRunHooks:
    """Integration tests verifying post-run hooks fire on resume()."""

    def test_resume_fires_post_hooks_on_pass(self, tmp_path: Path) -> None:
        """Post-run hooks should execute on resume() when outcome is PASS."""
        from runtime.orchestration.loop.spine import LoopSpine
        from runtime.api.governance_api import hash_json
        import yaml

        # Setup spine with custom post-run hooks
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "artifacts").mkdir(parents=True)
        (repo / "artifacts" / "terminal").mkdir()
        (repo / "artifacts" / "checkpoints").mkdir()
        (repo / "artifacts" / "ledger").mkdir()

        # Track hook execution
        hook_executed = {"called": False}

        def custom_post_hook(**kwargs: Any) -> HookResult:
            hook_executed["called"] = True
            assert kwargs.get("terminal_packet_path") is not None
            assert kwargs.get("ledger_write_ok") is not None
            return HookResult(name="test_post_hook", passed=True, reason="ok")

        spine = LoopSpine(
            repo_root=repo,
            post_run_hooks=[custom_post_hook],
        )

        # Create a minimal checkpoint
        run_id = "test-resume-123"
        checkpoint_id = "CP_test-resume-123_step_3"
        task_spec = {
            "goal": "test task",
            "evidence_dir": None,
            "evidence_tier": "light",
        }

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "run_id": run_id,
            "step_index": 6,  # steward step (last step, will complete)
            "task_spec": task_spec,
            "policy_hash": hash_json({"version": "1.0"}),
            "timestamp": "2026-02-17T12:00:00Z",
            "trigger": "ESCALATION_REQUESTED",
            "resolved": True,
            "resolution_decision": "APPROVED",
        }

        checkpoint_file = repo / "artifacts" / "checkpoints" / f"{checkpoint_id}.yaml"
        checkpoint_file.write_text(yaml.dump(checkpoint_data))

        # Mock methods to isolate post-hook testing
        def mock_get_policy_hash() -> str:
            return hash_json({"version": "1.0"})

        def mock_run_chain(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {
                "outcome": "PASS",
                "reason": "pass",
                "steps_executed": ["steward"],
                "commit_hash": "abc123",
            }

        spine._get_current_policy_hash = mock_get_policy_hash  # type: ignore
        spine._run_chain_steps = mock_run_chain  # type: ignore

        # Execute resume
        with patch("runtime.orchestration.loop.spine.verify_repo_clean"):
            result = spine.resume(checkpoint_id)

        # Verify hook was called
        assert hook_executed["called"], "Post-run hook should have been called on resume"
        assert result["outcome"] == "PASS"
        assert result["resumed"] is True

    def test_resume_post_hooks_can_downgrade_pass_to_blocked(self, tmp_path: Path) -> None:
        """Post-run hooks should be able to downgrade PASS to BLOCKED on resume."""
        from runtime.orchestration.loop.spine import LoopSpine
        from runtime.api.governance_api import hash_json
        import yaml

        # Setup spine
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "artifacts").mkdir(parents=True)
        (repo / "artifacts" / "terminal").mkdir()
        (repo / "artifacts" / "checkpoints").mkdir()
        (repo / "artifacts" / "ledger").mkdir()

        # Failing hook
        def failing_post_hook(**kwargs: Any) -> HookResult:
            return HookResult(
                name="evidence_check",
                passed=False,
                reason="evidence incomplete"
            )

        spine = LoopSpine(
            repo_root=repo,
            post_run_hooks=[failing_post_hook],
        )

        # Create checkpoint
        run_id = "test-resume-456"
        checkpoint_id = "CP_test-resume-456_step_3"
        task_spec = {
            "goal": "test task",
            "evidence_dir": None,
            "evidence_tier": "light",
        }

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "run_id": run_id,
            "step_index": 6,
            "task_spec": task_spec,
            "policy_hash": hash_json({"version": "1.0"}),
            "timestamp": "2026-02-17T12:00:00Z",
            "trigger": "ESCALATION_REQUESTED",
            "resolved": True,
            "resolution_decision": "APPROVED",
        }

        checkpoint_file = repo / "artifacts" / "checkpoints" / f"{checkpoint_id}.yaml"
        checkpoint_file.write_text(yaml.dump(checkpoint_data))

        # Mock methods to isolate post-hook testing
        def mock_get_policy_hash() -> str:
            return hash_json({"version": "1.0"})

        def mock_run_chain(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {
                "outcome": "PASS",
                "reason": "pass",
                "steps_executed": ["steward"],
                "commit_hash": "abc123",
            }

        spine._get_current_policy_hash = mock_get_policy_hash  # type: ignore
        spine._run_chain_steps = mock_run_chain  # type: ignore

        # Execute resume
        with patch("runtime.orchestration.loop.spine.verify_repo_clean"):
            result = spine.resume(checkpoint_id)

        # Verify outcome was downgraded to BLOCKED
        assert result["outcome"] == "BLOCKED"

        # Verify terminal packet was re-emitted with BLOCKED outcome and correct reason
        terminal_file = repo / "artifacts" / "terminal" / f"TP_{run_id}.yaml"
        assert terminal_file.exists()
        terminal_data = yaml.safe_load(terminal_file.read_text())
        assert terminal_data["outcome"] == "BLOCKED"
        assert "post_run_hook_failed" in terminal_data["reason"]
        assert "evidence_check" in terminal_data["reason"]
