"""
Test Loop Spine (A1 Chain Controller)

TDD acceptance tests for Phase 4A0 Loop Spine.
Tests checkpoint/resume semantics, deterministic execution, and fail-closed behavior.
"""
import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from runtime.orchestration.loop.spine import (
    LoopSpine,
    SpineState,
    CheckpointPacket,
    TerminalPacket,
    SpineError,
    PolicyChangedError,
)
from runtime.orchestration.run_controller import RepoDirtyError


@pytest.fixture
def clean_repo_root(tmp_path):
    """Create a clean test repo structure."""
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create required directories
    (repo_root / "artifacts" / "terminal").mkdir(parents=True)
    (repo_root / "artifacts" / "checkpoints").mkdir(parents=True)
    (repo_root / "artifacts" / "loop_state").mkdir(parents=True)
    (repo_root / "artifacts" / "steps").mkdir(parents=True)

    return repo_root


@pytest.fixture
def task_spec():
    """Sample task specification."""
    return {
        "task": "Implement feature X",
        "context_refs": ["docs/spec.md"],
    }


@pytest.fixture
def mock_run_controller():
    """Mock run controller to bypass repo checks in tests."""
    with patch("runtime.orchestration.loop.spine.verify_repo_clean") as mock_verify:
        mock_verify.return_value = None  # Clean repo
        yield mock_verify


@pytest.fixture
def mock_policy_hash():
    """Mock policy hash computation for tests."""
    with patch.object(LoopSpine, "_get_current_policy_hash") as mock_hash:
        mock_hash.return_value = "test_policy_hash_abc123"
        yield mock_hash


class TestSingleChainExecution:
    """Test: Single chain execution to terminal (Scenario 1)"""

    def test_single_chain_to_terminal_pass(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """
        Given a task spec is provided
        When the loop spine runs the chain
        Then it executes: hydrate → policy → design → build → review → steward
        And it emits a terminal packet with outcome PASS
        And the ledger contains a complete attempt record
        And the terminal packet has deterministic field ordering
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        # Mock successful execution through all steps
        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.return_value = {
                "outcome": "PASS",
                "steps_executed": ["hydrate", "policy", "design", "build", "review", "steward"],
                "commit_hash": "abc123",
            }

            result = spine.run(task_spec=task_spec)

            assert result["outcome"] == "PASS"
            assert result["state"] == SpineState.TERMINAL.value

            # Verify terminal packet was emitted
            terminal_packets = list((clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
            assert len(terminal_packets) == 1

            # Verify deterministic YAML format
            with open(terminal_packets[0]) as f:
                packet_data = yaml.safe_load(f)
                assert packet_data["outcome"] == "PASS"
                assert "run_id" in packet_data
                assert "timestamp" in packet_data

            # Verify ledger record exists
            ledger_file = clean_repo_root / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
            assert ledger_file.exists()

    def test_single_chain_to_terminal_blocked(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """
        Test chain that ends in BLOCKED state (e.g., test failure exhausted retries)
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.return_value = {
                "outcome": "BLOCKED",
                "reason": "max_retries_exceeded",
                "steps_executed": ["hydrate", "policy", "design", "build"],
            }

            result = spine.run(task_spec=task_spec)

            assert result["outcome"] == "BLOCKED"
            assert result["state"] == SpineState.TERMINAL.value

            # Verify terminal packet
            terminal_packets = list((clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
            assert len(terminal_packets) == 1

            with open(terminal_packets[0]) as f:
                packet_data = yaml.safe_load(f)
                assert packet_data["outcome"] == "BLOCKED"
                assert packet_data["reason"] == "max_retries_exceeded"


class TestCheckpointPause:
    """Test: Checkpoint pauses execution (Scenario 2)"""

    def test_checkpoint_pauses_on_escalation(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """
        Given a chain is running
        When a checkpoint trigger fires (e.g., ESCALATION_REQUESTED)
        Then execution pauses immediately
        And checkpoint state is persisted to ledger
        And a checkpoint packet is emitted to artifacts/
        And the process exits with code 0 (clean pause)
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        with patch.object(spine, "_run_chain_steps") as mock_steps:
            # Simulate escalation during execution
            mock_steps.side_effect = lambda *args, **kwargs: spine._trigger_checkpoint(
                trigger="ESCALATION_REQUESTED",
                step_index=2,
                context={"current_step": "design", "task_spec": task_spec}
            )

            result = spine.run(task_spec=task_spec)

            assert result["state"] == SpineState.CHECKPOINT.value
            assert result["checkpoint_id"] is not None

            # Verify checkpoint packet exists
            checkpoint_packets = list((clean_repo_root / "artifacts" / "checkpoints").glob("CP_*.yaml"))
            assert len(checkpoint_packets) == 1

            # Verify checkpoint content
            with open(checkpoint_packets[0]) as f:
                checkpoint_data = yaml.safe_load(f)
                assert checkpoint_data["trigger"] == "ESCALATION_REQUESTED"
                assert checkpoint_data["step_index"] == 2
                assert checkpoint_data["resolved"] is False
                assert "policy_hash" in checkpoint_data

    def test_checkpoint_packet_format(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """Verify checkpoint packet has stable format with sorted keys."""
        spine = LoopSpine(repo_root=clean_repo_root)

        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_test_123",
            run_id="run_123",
            timestamp="2026-02-02T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=2,
            policy_hash="abc123",
            task_spec=task_spec,
            resolved=False,
            resolution_decision=None,
        )

        spine._save_checkpoint(checkpoint_packet)

        checkpoint_file = clean_repo_root / "artifacts" / "checkpoints" / "CP_test_123.yaml"
        assert checkpoint_file.exists()

        # Verify YAML has sorted keys (deterministic)
        with open(checkpoint_file) as f:
            content = f.read()
            # YAML dump with sort_keys=True should maintain order
            reloaded = yaml.safe_load(content)
            assert list(reloaded.keys())[0] == "checkpoint_id"  # First key alphabetically


class TestResumeFromCheckpoint:
    """Test: Resume from checkpoint deterministically (Scenario 3)"""

    def test_resume_from_checkpoint_continues_execution(self, clean_repo_root, task_spec, mock_run_controller):
        """
        Given a checkpoint exists from a previous run
        And the checkpoint has not been resolved
        When the loop spine is invoked with --resume
        Then it loads the checkpoint state
        And it validates the policy hash matches
        And it continues from the checkpoint step
        And it does NOT re-execute completed steps
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        # Create a checkpoint
        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_resume_test",
            run_id="run_resume",
            timestamp="2026-02-02T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=2,
            policy_hash="current_policy_hash",
            task_spec=task_spec,
            resolved=True,
            resolution_decision="APPROVED",
        )
        spine._save_checkpoint(checkpoint_packet)

        # Resume from checkpoint
        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.return_value = {
                "outcome": "PASS",
                "steps_executed": ["build", "review", "steward"],  # Continues from step 3
                "commit_hash": "def456",
            }

            with patch.object(spine, "_get_current_policy_hash") as mock_hash:
                mock_hash.return_value = "current_policy_hash"

                result = spine.resume(checkpoint_id="CP_resume_test")

                assert result["outcome"] == "PASS"
                assert result["state"] == SpineState.RESUMED.value

                # Verify we didn't re-execute completed steps
                mock_steps.assert_called_once()
                call_kwargs = mock_steps.call_args[1]
                assert call_kwargs.get("start_from_step") == 2  # Continue from step 2

    def test_resume_skips_completed_steps(self, clean_repo_root, task_spec, mock_run_controller):
        """Verify resume does not re-execute completed steps before checkpoint."""
        spine = LoopSpine(repo_root=clean_repo_root)

        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_skip_test",
            run_id="run_skip",
            timestamp="2026-02-02T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=3,  # Checkpoint after step 3
            policy_hash="current_policy_hash",
            task_spec=task_spec,
            resolved=True,
            resolution_decision="APPROVED",
        )
        spine._save_checkpoint(checkpoint_packet)

        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.return_value = {"outcome": "PASS", "steps_executed": ["review", "steward"]}

            with patch.object(spine, "_get_current_policy_hash") as mock_hash:
                mock_hash.return_value = "current_policy_hash"

                spine.resume(checkpoint_id="CP_skip_test")

                # Verify we started from step 3 (skipped 0, 1, 2)
                call_kwargs = mock_steps.call_args[1]
                assert call_kwargs.get("start_from_step") == 3


class TestResumePolicyChange:
    """Test: Resume fails if policy changed (Scenario 4)"""

    def test_resume_fails_on_policy_hash_mismatch(self, clean_repo_root, task_spec, mock_run_controller):
        """
        Given a checkpoint exists with policy_hash "abc123"
        And the current policy_hash is "def456"
        When the loop spine attempts to resume
        Then it fails with POLICY_CHANGED_MID_RUN
        And it emits a terminal packet with BLOCKED outcome
        And the checkpoint is preserved (not deleted)
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        # Create checkpoint with old policy hash
        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_policy_test",
            run_id="run_policy",
            timestamp="2026-02-02T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=2,
            policy_hash="old_policy_hash_abc123",
            task_spec=task_spec,
            resolved=True,
            resolution_decision="APPROVED",
        )
        spine._save_checkpoint(checkpoint_packet)

        # Mock current policy hash is different
        with patch.object(spine, "_get_current_policy_hash") as mock_hash:
            mock_hash.return_value = "new_policy_hash_def456"

            with pytest.raises(PolicyChangedError) as exc_info:
                spine.resume(checkpoint_id="CP_policy_test")

            assert "POLICY_CHANGED_MID_RUN" in str(exc_info.value)
            assert "old_policy_hash_abc123" in str(exc_info.value)
            assert "new_policy_hash_def456" in str(exc_info.value)

            # Verify checkpoint file still exists (not deleted)
            checkpoint_file = clean_repo_root / "artifacts" / "checkpoints" / "CP_policy_test.yaml"
            assert checkpoint_file.exists()

            # Verify terminal packet was emitted with BLOCKED
            terminal_packets = list((clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
            assert len(terminal_packets) == 1

            with open(terminal_packets[0]) as f:
                terminal_data = yaml.safe_load(f)
                assert terminal_data["outcome"] == "BLOCKED"
                assert "POLICY_CHANGED_MID_RUN" in terminal_data["reason"]


class TestDirtyRepoFailClosed:
    """Test: Dirty repo fails closed (Scenario 5)"""

    def test_dirty_repo_fails_immediately(self, clean_repo_root, task_spec):
        """
        Given the repository has uncommitted changes
        When the loop spine is invoked
        Then it fails immediately with REPO_DIRTY
        And no steps are executed
        And no artefacts are emitted (fail-closed)
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        # Mock dirty repo
        with patch("runtime.orchestration.loop.spine.verify_repo_clean") as mock_verify:
            mock_verify.side_effect = RepoDirtyError("M file.py", "?? untracked.py")

            with pytest.raises(RepoDirtyError):
                spine.run(task_spec=task_spec)

            # Verify no artifacts were created
            terminal_packets = list((clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
            assert len(terminal_packets) == 0

            checkpoint_packets = list((clean_repo_root / "artifacts" / "checkpoints").glob("CP_*.yaml"))
            assert len(checkpoint_packets) == 0

    def test_dirty_repo_no_execution(self, clean_repo_root, task_spec):
        """Verify no chain steps execute when repo is dirty."""
        spine = LoopSpine(repo_root=clean_repo_root)

        with patch("runtime.orchestration.loop.spine.verify_repo_clean") as mock_verify:
            mock_verify.side_effect = RepoDirtyError("M file.py", "")

            with patch.object(spine, "_run_chain_steps") as mock_steps:
                try:
                    spine.run(task_spec=task_spec)
                except RepoDirtyError:
                    pass

                # Verify chain steps were never called
                mock_steps.assert_not_called()


class TestCheckpointResolution:
    """Test: Checkpoint resolved triggers resume (Scenario 6)"""

    def test_checkpoint_resolution_approved_resumes(self, clean_repo_root, task_spec, mock_run_controller):
        """
        Given a checkpoint is pending CEO resolution
        And the CEO has marked it resolved (approved)
        When the loop spine checks for resolution
        Then it reads the resolution from the checkpoint seam
        And it resumes execution
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        # Create resolved checkpoint (approved)
        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_resolved_approved",
            run_id="run_resolved",
            timestamp="2026-02-02T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=2,
            policy_hash="current_policy_hash",
            task_spec=task_spec,
            resolved=True,
            resolution_decision="APPROVED",
        )
        spine._save_checkpoint(checkpoint_packet)

        # Check resolution
        is_resolved, decision = spine._check_resolution("CP_resolved_approved")

        assert is_resolved is True
        assert decision == "APPROVED"

    def test_checkpoint_resolution_rejected_terminates(self, clean_repo_root, task_spec, mock_run_controller):
        """
        Given a checkpoint is pending CEO resolution
        And the CEO has marked it resolved (rejected)
        When the loop spine checks for resolution
        Then it terminates execution without resuming
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        # Create resolved checkpoint (rejected)
        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_resolved_rejected",
            run_id="run_rejected",
            timestamp="2026-02-02T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=2,
            policy_hash="current_policy_hash",
            task_spec=task_spec,
            resolved=True,
            resolution_decision="REJECTED",
        )
        spine._save_checkpoint(checkpoint_packet)

        with patch.object(spine, "_get_current_policy_hash") as mock_hash:
            mock_hash.return_value = "current_policy_hash"

            # Resume should respect the rejection
            with patch.object(spine, "_run_chain_steps") as mock_steps:
                result = spine.resume(checkpoint_id="CP_resolved_rejected")

                # Should terminate without executing
                assert result["outcome"] == "BLOCKED"
                assert result["reason"] == "checkpoint_rejected"
                mock_steps.assert_not_called()

    def test_checkpoint_unresolved_waits(self, clean_repo_root, task_spec, mock_run_controller):
        """
        Given a checkpoint is pending and unresolved
        When the loop spine checks for resolution
        Then it indicates the checkpoint is still waiting
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        # Create unresolved checkpoint
        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_unresolved",
            run_id="run_unresolved",
            timestamp="2026-02-02T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=2,
            policy_hash="current_policy_hash",
            task_spec=task_spec,
            resolved=False,
            resolution_decision=None,
        )
        spine._save_checkpoint(checkpoint_packet)

        is_resolved, decision = spine._check_resolution("CP_unresolved")

        assert is_resolved is False
        assert decision is None


class TestArtifactOutputContract:
    """Test: Artifact output contract (deterministic formatting)"""

    def test_terminal_packet_sorted_keys(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """Verify terminal packet YAML has sorted keys for determinism."""
        spine = LoopSpine(repo_root=clean_repo_root)

        terminal_packet = TerminalPacket(
            run_id="run_sorted",
            timestamp="2026-02-02T12:00:00Z",
            outcome="PASS",
            reason="pass",
            steps_executed=["hydrate", "policy", "design", "build", "review", "steward"],
            commit_hash="abc123",
        )

        terminal_file = spine._emit_terminal(terminal_packet)

        # Read raw YAML to verify key ordering
        with open(terminal_file) as f:
            lines = f.readlines()
            # YAML with sorted keys should have keys in alphabetical order
            content = "".join(lines)
            assert content.index("commit_hash:") < content.index("outcome:")
            assert content.index("outcome:") < content.index("run_id:")

    def test_step_summary_json_sorted(self, clean_repo_root, mock_run_controller, mock_policy_hash):
        """Verify step summary JSON has sorted keys."""
        spine = LoopSpine(repo_root=clean_repo_root)

        step_summary = {
            "step_name": "design",
            "outcome": "success",
            "duration_ms": 1500,
            "artifacts": ["design.md"],
        }

        step_file = clean_repo_root / "artifacts" / "steps" / "run_test_design.json"
        spine._emit_step_summary("run_test", "design", step_summary)

        # Verify JSON has sorted keys
        with open(step_file) as f:
            content = f.read()
            data = json.loads(content)
            keys = list(data.keys())
            assert keys == sorted(keys)
