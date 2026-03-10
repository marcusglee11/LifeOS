"""
Test Loop Spine (A1 Chain Controller)

TDD acceptance tests for Phase 4A0 Loop Spine.
Tests checkpoint/resume semantics, deterministic execution, and fail-closed behavior.
"""
import pytest
import json
import hashlib
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
from runtime.orchestration.loop.run_lock import RunLockError
from runtime.orchestration.workflow_runtime import build_task_context, build_workflow_instance


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

    def test_terminal_packet_hash_and_contract_fields(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """Terminal packet includes gate_results/receipt_index and verifiable packet_hash."""
        spine = LoopSpine(repo_root=clean_repo_root)

        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.return_value = {
                "outcome": "PASS",
                "steps_executed": ["hydrate", "policy", "design", "build", "review", "steward"],
                "commit_hash": "abc123",
            }

            result = spine.run(task_spec=task_spec)
            assert result["outcome"] == "PASS"

        terminal_packets = list((clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
        assert len(terminal_packets) == 1
        packet_data = yaml.safe_load(terminal_packets[0].read_text("utf-8"))
        assert isinstance(packet_data.get("gate_results"), list)
        assert packet_data["receipt_index"] == f"artifacts/receipts/{packet_data['run_id']}/index.json"

        receipt_index_path = clean_repo_root / packet_data["receipt_index"]
        assert receipt_index_path.exists()

        packet_hash = packet_data["packet_hash"]
        packet_data["packet_hash"] = None
        serialized_without_hash = yaml.dump(packet_data, sort_keys=True, default_flow_style=False)
        expected_hash = f"sha256:{hashlib.sha256(serialized_without_hash.encode('utf-8')).hexdigest()}"
        assert packet_hash == expected_hash

    def test_concurrent_run_emits_terminal_packet(self, clean_repo_root, task_spec, mock_run_controller):
        """Run-lock contention returns BLOCKED and emits a terminal packet."""
        spine = LoopSpine(repo_root=clean_repo_root)
        with patch("runtime.orchestration.loop.run_lock.acquire_run_lock") as mock_acquire:
            mock_acquire.side_effect = RunLockError(
                "CONCURRENT_RUN_DETECTED",
                "Run lock held by pid=1 run_id=other",
            )
            result = spine.run(task_spec=task_spec)

        assert result["outcome"] == "BLOCKED"
        assert result["reason"] == "concurrent_run_detected"
        terminal_packets = list((clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
        assert len(terminal_packets) == 1
        packet_data = yaml.safe_load(terminal_packets[0].read_text("utf-8"))
        assert packet_data["reason"] == "concurrent_run_detected"
        assert packet_data["outcome"] == "BLOCKED"
        assert isinstance(packet_data.get("gate_results"), list)


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

    def test_typed_review_checkpoint_propagates_to_spine_handler(self, clean_repo_root, mock_run_controller, mock_policy_hash):
        spine = LoopSpine(repo_root=clean_repo_root)
        instance = build_workflow_instance(
            workflow_id="spec_creation.v1",
            task_ref="T-123",
            order_id="ORD-T-123-20260310000000",
            task_context=build_task_context(None, objective="Write a spec"),
        )
        instance.current_step_id = "architect_review"
        instance.next_step_id = "revise_spec"
        instance.artifact_refs["design_spec.v1"] = {
            "artifact_id": "wf:ORD-T-123-20260310000000:design_spec.v1:draft_spec",
            "artifact_type": "design_spec.v1",
            "schema_version": "design_spec.v1",
            "producer_role": "designer",
            "workflow_instance_id": instance.instance_id,
            "created_at": "2026-03-10T00:00:00Z",
            "payload": {"body": "draft"},
            "sha256": "abc123",
        }

        review_result = MagicMock()
        review_result.success = True
        review_result.outputs = {"verdict": "escalate", "rationale": "needs CEO"}

        mission = MagicMock()
        mission.run.return_value = review_result

        with patch("runtime.orchestration.missions.get_mission_class", return_value=lambda: mission), patch(
            "runtime.orchestration.loop.spine.ShadowCouncilRunner"
        ) as mock_shadow:
            mock_shadow.return_value.run_shadow.return_value = None
            result = spine.run(task_spec={"workflow_instance": instance.to_dict()})

        assert result["state"] == SpineState.CHECKPOINT.value
        assert result["checkpoint_id"] is not None
        checkpoint_packets = list((clean_repo_root / "artifacts" / "checkpoints").glob("CP_*.yaml"))
        assert len(checkpoint_packets) == 1


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

    def test_resume_acquires_and_releases_run_lock(self, clean_repo_root, task_spec, mock_run_controller):
        """resume() uses run lock with the checkpoint run_id and releases it."""
        spine = LoopSpine(repo_root=clean_repo_root)
        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_lock_resume",
            run_id="run_resume_lock",
            timestamp="2026-02-02T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=2,
            policy_hash="current_policy_hash",
            task_spec=task_spec,
            resolved=True,
            resolution_decision="APPROVED",
        )
        spine._save_checkpoint(checkpoint_packet)

        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.return_value = {
                "outcome": "PASS",
                "steps_executed": ["build", "review", "steward"],
                "commit_hash": "def456",
            }
            with patch.object(spine, "_get_current_policy_hash", return_value="current_policy_hash"), \
                 patch("runtime.orchestration.loop.run_lock.acquire_run_lock") as mock_acquire, \
                 patch("runtime.orchestration.loop.run_lock.release_run_lock") as mock_release:
                mock_acquire.return_value = object()
                result = spine.resume(checkpoint_id="CP_lock_resume")

        assert result["outcome"] == "PASS"
        mock_acquire.assert_called_once_with(clean_repo_root, "run_resume_lock")
        mock_release.assert_called_once()


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

    def test_hydrate_workflow_instance_voids_running_invocations_on_resume(self, clean_repo_root):
        spine = LoopSpine(repo_root=clean_repo_root)
        instance = build_workflow_instance(
            workflow_id="spec_creation.v1",
            task_ref="T-123",
            order_id="ORD-T-123-20260310000000",
            task_context=build_task_context(None, objective="Write a spec"),
        )
        instance.state = "CHECKPOINTED"
        instance.invocation_records["invocation-1"] = {
            "invocation_key": "invocation-1",
            "workflow_instance_ref": instance.instance_id,
            "workflow_def_hash": instance.workflow_def_hash,
            "step_id": "architect_review",
            "attempt_index": 0,
            "instance_state_hash_before": instance.instance_state_hash,
            "executor_identity": "reviewer_architect",
            "lease_status": "RUNNING",
            "started_at": "2026-03-10T00:00:00Z",
            "completed_at": None,
            "result_ref": None,
            "result_status": None,
            "error_code": None,
        }

        hydrated = spine._hydrate_workflow_instance(
            {
                "workflow_instance": instance.to_dict(),
                "ceo_resolution": {
                    "workflow_instance_ref": instance.instance_id,
                    "expected_prior_state": "CHECKPOINTED",
                    "expected_workflow_def_hash": instance.workflow_def_hash,
                    "resolution_action": "RESUME_CURRENT_STEP",
                    "actor": "ceo",
                    "issued_at": "2026-03-10T00:10:00Z",
                    "note": "resume",
                },
            },
            start_from_step=0,
        )

        assert hydrated.state == "READY"
        assert hydrated.invocation_records["invocation-1"]["lease_status"] == "VOID"


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


class TestTerminalPacketLedgerAnchor:
    """Test: Terminal packet includes ledger chain anchor fields (W7-T01)"""

    def test_terminal_packet_includes_anchor_fields(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """Terminal packet YAML contains ledger_chain_tip, ledger_attempt_count, ledger_schema_version."""
        spine = LoopSpine(repo_root=clean_repo_root)

        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.return_value = {
                "outcome": "PASS",
                "steps_executed": ["hydrate", "policy", "design", "build", "review", "steward"],
                "commit_hash": "abc123",
            }

            result = spine.run(task_spec=task_spec)

            # Read the terminal packet
            terminal_packets = list((clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
            assert len(terminal_packets) == 1

            with open(terminal_packets[0]) as f:
                packet_data = yaml.safe_load(f)

            # Anchor fields must be present
            assert "ledger_chain_tip" in packet_data
            assert "ledger_attempt_count" in packet_data
            assert "ledger_schema_version" in packet_data

            # Validate values
            assert packet_data["ledger_chain_tip"] is not None
            assert len(packet_data["ledger_chain_tip"]) == 64  # SHA-256 hex
            assert packet_data["ledger_attempt_count"] == 1  # One record written
            assert packet_data["ledger_schema_version"] == "v1.1"

    def test_terminal_packet_anchor_matches_ledger_state(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """Terminal packet anchor values match actual ledger state at completion."""
        spine = LoopSpine(repo_root=clean_repo_root)

        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.return_value = {
                "outcome": "PASS",
                "steps_executed": ["hydrate", "policy", "design", "build", "review", "steward"],
                "commit_hash": "def456",
            }

            spine.run(task_spec=task_spec)

            # Read ledger directly
            from runtime.orchestration.loop.ledger import AttemptLedger
            ledger = AttemptLedger(clean_repo_root / "artifacts" / "loop_state" / "attempt_ledger.jsonl")
            ledger.hydrate()

            # Read terminal packet
            terminal_packets = list((clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml"))
            with open(terminal_packets[0]) as f:
                packet_data = yaml.safe_load(f)

            # Verify anchor matches actual ledger
            assert packet_data["ledger_chain_tip"] == ledger.get_chain_tip()
            assert packet_data["ledger_attempt_count"] == len(ledger.history)
            assert packet_data["ledger_schema_version"] == ledger.header.get("schema_version")


class TestShadowCouncilWiring:
    """Tests that ShadowCouncilRunner is called from the review phase of _run_chain_steps."""

    def _make_mock_mission(self, outputs=None):
        """Return a mock mission that produces given outputs."""
        m = MagicMock()
        result = MagicMock()
        result.success = True
        result.outputs = outputs or {}
        m.return_value.run.return_value = result
        return m

    def test_shadow_runner_called_after_review(self, clean_repo_root, task_spec):
        """Shadow runner is invoked once, after the review step, never raising."""
        spine = LoopSpine(repo_root=clean_repo_root)
        spine.run_id = "run_shadow_wiring_test"

        review_outputs = {"reviewer_packet_parsed": {"verdict": "accept"}}
        mock_mission = self._make_mock_mission(outputs=review_outputs)

        shadow_calls = []

        def fake_run_shadow(run_id, ccp, **_kw):
            shadow_calls.append({"run_id": run_id, "ccp": ccp})
            return {"status": "shadow_ok"}

        with patch(
            "runtime.orchestration.missions.get_mission_class",
            return_value=mock_mission,
        ), patch(
            "runtime.orchestration.council.shadow_runner.ShadowCouncilRunner.run_shadow",
            side_effect=fake_run_shadow,
        ), patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout="deadbeef"),
        ):
            spine._run_chain_steps(task_spec)

        assert len(shadow_calls) == 1, "run_shadow must be called exactly once"
        assert shadow_calls[0]["run_id"] == "run_shadow_wiring_test"
        assert "sections" in shadow_calls[0]["ccp"]

    def test_shadow_runner_not_called_if_review_not_reached(self, clean_repo_root, task_spec):
        """If review step errors out, shadow is still not called for that failure path."""
        spine = LoopSpine(repo_root=clean_repo_root)
        spine.run_id = "run_shadow_no_review"

        # Make every mission blow up (simulates build failure)
        def boom_mission(*_a, **_kw):
            raise RuntimeError("mission exploded")

        bad_mission = MagicMock()
        bad_mission.return_value.run.side_effect = RuntimeError("mission exploded")

        shadow_calls = []

        with patch(
            "runtime.orchestration.missions.get_mission_class",
            return_value=bad_mission,
        ), patch(
            "runtime.orchestration.council.shadow_runner.ShadowCouncilRunner.run_shadow",
            side_effect=lambda **kw: shadow_calls.append(kw),
        ), patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout="deadbeef"),
        ):
            result = spine._run_chain_steps(task_spec)

        assert result["outcome"] == "BLOCKED"
        assert len(shadow_calls) == 0


class TestBatch2Fixes:
    """Regression tests for the three Batch 1 procedure fixes (B2-F2, B2-F3, B2-F5)."""

    def test_steward_inputs_include_max_diff_lines_default(self, clean_repo_root, task_spec):
        """B2-F5: Spine threads max_diff_lines=500 default into steward inputs (≥400 for Batch-1 Run-6 safety)."""
        spine = LoopSpine(repo_root=clean_repo_root)
        spine.run_id = "run_fix5_default"

        all_inputs_seen = []

        mock_mission = MagicMock()
        result_ok = MagicMock()
        result_ok.success = True
        result_ok.outputs = {"review_packet": {}, "verdict": "approved"}

        def capture_run(context, inputs):
            all_inputs_seen.append(dict(inputs))
            return result_ok

        mock_mission.return_value.run.side_effect = capture_run

        with patch("runtime.orchestration.missions.get_mission_class", return_value=mock_mission), \
             patch("runtime.orchestration.council.shadow_runner.ShadowCouncilRunner.run_shadow"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="deadbeef")):
            spine._run_chain_steps(task_spec)

        # Steward inputs are identifiable by "review_packet" + "approval" keys
        steward_inputs = [i for i in all_inputs_seen if "approval" in i and "review_packet" in i]
        assert steward_inputs, "Steward inputs not captured"
        assert "max_diff_lines" in steward_inputs[0], f"max_diff_lines missing: {steward_inputs[0]}"
        assert steward_inputs[0]["max_diff_lines"] == 500
        assert steward_inputs[0]["max_diff_lines"] >= 400, "default must cover Batch-1 Run-6 high-water mark (340 lines)"

    def test_steward_inputs_max_diff_lines_from_task_spec(self, clean_repo_root, task_spec):
        """B2-F5: Task spec constraints.max_diff_lines overrides default 300."""
        task_spec_with_budget = dict(task_spec)
        task_spec_with_budget["constraints"] = {"max_diff_lines": 500}

        spine = LoopSpine(repo_root=clean_repo_root)
        spine.run_id = "run_fix5_override"

        all_inputs_seen = []

        mock_mission = MagicMock()
        result_ok = MagicMock()
        result_ok.success = True
        result_ok.outputs = {"review_packet": {}, "verdict": "approved"}

        def capture_run(context, inputs):
            all_inputs_seen.append(dict(inputs))
            return result_ok

        mock_mission.return_value.run.side_effect = capture_run

        with patch("runtime.orchestration.missions.get_mission_class", return_value=mock_mission), \
             patch("runtime.orchestration.council.shadow_runner.ShadowCouncilRunner.run_shadow"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="deadbeef")):
            spine._run_chain_steps(task_spec_with_budget)

        steward_inputs = [i for i in all_inputs_seen if "approval" in i and "review_packet" in i]
        assert steward_inputs, "Steward inputs not captured"
        assert steward_inputs[0].get("max_diff_lines") == 500

    def test_default_allowed_paths_includes_docs_and_config(self, clean_repo_root, task_spec):
        """B2-F2: Default allowed_paths now includes docs/** and config/**."""
        spine = LoopSpine(repo_root=clean_repo_root)
        spine.current_policy_hash = "testhash"

        task_spec_no_constraints = dict(task_spec)
        task_spec_no_constraints.pop("constraints", None)

        hook_kwargs = spine._build_hook_kwargs(task_spec_no_constraints)
        allowed = hook_kwargs["allowed_paths"]

        assert "docs/**" in allowed, f"docs/** missing from defaults: {allowed}"
        assert "config/**" in allowed, f"config/** missing from defaults: {allowed}"

    def test_ledger_autocommit_calls_git_commit(self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash):
        """B2-F3: After successful ledger write, spine calls git commit on the ledger file.

        Regression guard: the auto-commit block uses a local `import subprocess as _sp`
        so this test patches `subprocess.run` at module level to verify the calls reach git.
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        git_commit_calls = []

        def capture_subprocess(cmd, **kwargs):
            if isinstance(cmd, (list, tuple)) and len(cmd) >= 2 and cmd[0] == "git":
                git_commit_calls.append(cmd)
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b"ok"
            return mock_result

        with patch.object(spine, "_run_chain_steps") as mock_steps, \
             patch("subprocess.run", side_effect=capture_subprocess):
            mock_steps.return_value = {
                "outcome": "PASS",
                "steps_executed": ["hydrate", "policy", "design", "build", "review", "steward"],
                "commit_hash": "deadbeef",
            }
            spine.run(task_spec=task_spec)

        commit_calls = [c for c in git_commit_calls if "commit" in c]
        assert commit_calls, (
            "Expected at least one 'git commit' call for ledger auto-commit, "
            f"got git calls: {git_commit_calls}"
        )
        # The commit message must reference the run_id
        commit_msg_call = next((c for c in commit_calls if any("chore(ledger)" in str(a) for a in c)), None)
        assert commit_msg_call is not None, (
            f"Expected 'chore(ledger)' in commit message, git commit calls: {commit_calls}"
        )
