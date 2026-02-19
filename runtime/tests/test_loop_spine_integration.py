"""
W5-T02: Checkpoint/Resume E2E Integration Proof

Proves the full cycle: run → escalation → checkpoint YAML on disk →
resolution seam → resume → terminal packet with ledger continuity.

DoD: "Resume proceeds from correct state with policy integrity checks."
"""
import json
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from runtime.orchestration.loop.spine import (
    LoopSpine,
    SpineState,
    CheckpointPacket,
    TerminalPacket,
    SpineError,
    PolicyChangedError,
)
from runtime.orchestration.run_controller import RepoDirtyError
from runtime.cli import main


# ── Fixtures (reused from test_loop_spine.py:25-63) ──────────────────────────


@pytest.fixture
def clean_repo_root(tmp_path):
    """Create a clean test repo structure."""
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()
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
        mock_verify.return_value = None
        yield mock_verify


@pytest.fixture
def mock_policy_hash():
    """Mock policy hash computation for tests."""
    with patch.object(LoopSpine, "_get_current_policy_hash") as mock_hash:
        mock_hash.return_value = "test_policy_hash_abc123"
        yield mock_hash


@pytest.fixture
def temp_repo(tmp_path):
    """Create a mock repo structure for CLI tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo


# ── Test Class 1: Full Checkpoint/Resume E2E Cycle ──────────────────────────


class TestCheckpointResumeE2ECycle:
    """Prove: run → escalation → checkpoint YAML → resolve → resume → terminal."""

    def test_checkpoint_written_to_disk_on_escalation(
        self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash
    ):
        """
        Given a LoopSpine with standard artifact dirs
        When _run_chain_steps triggers ESCALATION_REQUESTED at step 2
        Then result state is CHECKPOINT
        And YAML exists at artifacts/checkpoints/CP_<run_id>_2.yaml
        And YAML contains trigger, step_index=2, resolved=False, policy_hash, task_spec
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        with patch.object(spine, "_run_chain_steps") as mock_steps:
            mock_steps.side_effect = lambda *args, **kwargs: spine._trigger_checkpoint(
                trigger="ESCALATION_REQUESTED",
                step_index=2,
                context={"task_spec": task_spec},
            )

            result = spine.run(task_spec=task_spec)

        assert result["state"] == SpineState.CHECKPOINT.value
        assert result["checkpoint_id"] is not None

        run_id = result["run_id"]
        checkpoint_id = result["checkpoint_id"]
        assert checkpoint_id == f"CP_{run_id}_2"

        # Verify YAML on disk
        cp_file = clean_repo_root / "artifacts" / "checkpoints" / f"{checkpoint_id}.yaml"
        assert cp_file.exists()

        with open(cp_file) as f:
            data = yaml.safe_load(f)

        assert data["trigger"] == "ESCALATION_REQUESTED"
        assert data["step_index"] == 2
        assert data["resolved"] is False
        assert data["policy_hash"] == "test_policy_hash_abc123"
        # task_spec round-trips
        assert data["task_spec"]["task"] == task_spec["task"]
        assert data["task_spec"]["context_refs"] == task_spec["context_refs"]

    def test_resolve_checkpoint_yaml_and_resume(
        self, clean_repo_root, task_spec, mock_run_controller, mock_policy_hash
    ):
        """
        Given a checkpoint from escalation
        When the checkpoint YAML is edited to resolved=True, APPROVED
        And a new LoopSpine instance calls resume()
        Then result has outcome=PASS, state=RESUMED, resumed=True
        And start_from_step=2 was passed to _run_chain_steps
        And terminal packet has ledger_chain_tip (64-char hex) and ledger_schema_version v1.1
        """
        # Phase 1: trigger checkpoint
        spine1 = LoopSpine(repo_root=clean_repo_root)

        with patch.object(spine1, "_run_chain_steps") as mock_steps:
            mock_steps.side_effect = lambda *args, **kwargs: spine1._trigger_checkpoint(
                trigger="ESCALATION_REQUESTED",
                step_index=2,
                context={"task_spec": task_spec},
            )
            result1 = spine1.run(task_spec=task_spec)

        checkpoint_id = result1["checkpoint_id"]
        cp_file = clean_repo_root / "artifacts" / "checkpoints" / f"{checkpoint_id}.yaml"

        # Phase 2: programmatic resolution (simulate CEO approval)
        with open(cp_file) as f:
            cp_data = yaml.safe_load(f)
        cp_data["resolved"] = True
        cp_data["resolution_decision"] = "APPROVED"
        with open(cp_file, "w") as f:
            yaml.dump(cp_data, f, sort_keys=True, default_flow_style=False)

        # Phase 3: new LoopSpine instance resumes
        spine2 = LoopSpine(repo_root=clean_repo_root)

        with patch.object(spine2, "_run_chain_steps") as mock_steps2:
            mock_steps2.return_value = {
                "outcome": "PASS",
                "steps_executed": ["design", "build", "review", "steward"],
                "commit_hash": None,
            }

            result2 = spine2.resume(checkpoint_id=checkpoint_id)

        # Assertions on resume result
        assert result2["outcome"] == "PASS"
        assert result2["state"] == SpineState.RESUMED.value
        assert result2["resumed"] is True

        # Verify start_from_step=2 was passed
        mock_steps2.assert_called_once()
        call_kwargs = mock_steps2.call_args[1]
        assert call_kwargs["start_from_step"] == 2

        # Verify terminal packet with ledger anchor
        terminal_packets = list(
            (clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml")
        )
        assert len(terminal_packets) >= 1

        with open(terminal_packets[-1]) as f:
            tp_data = yaml.safe_load(f)

        assert "ledger_chain_tip" in tp_data
        assert tp_data["ledger_chain_tip"] is not None
        assert len(tp_data["ledger_chain_tip"]) == 64  # SHA-256 hex
        assert tp_data["ledger_schema_version"] == "v1.1"


# ── Test Class 2: Policy Change Rejection ────────────────────────────────────


class TestPolicyChangeRejection:
    """Prove: resume is blocked when policy hash changes between checkpoint and resume."""

    def test_resume_blocked_on_policy_hash_mismatch(
        self, clean_repo_root, task_spec, mock_run_controller
    ):
        """
        Given a resolved checkpoint with policy_hash="hash_at_checkpoint_time"
        And current policy hash is "hash_now_different"
        When spine.resume() is called
        Then PolicyChangedError is raised
        And a BLOCKED terminal packet is emitted
        And checkpoint YAML still exists (not deleted)
        """
        spine = LoopSpine(repo_root=clean_repo_root)

        # Create resolved checkpoint with known hash
        checkpoint_packet = CheckpointPacket(
            checkpoint_id="CP_policy_e2e_test",
            run_id="run_policy_e2e",
            timestamp="2026-02-19T12:00:00Z",
            trigger="ESCALATION_REQUESTED",
            step_index=2,
            policy_hash="hash_at_checkpoint_time",
            task_spec=task_spec,
            resolved=True,
            resolution_decision="APPROVED",
        )
        spine._save_checkpoint(checkpoint_packet)

        # Current hash is different
        with patch.object(spine, "_get_current_policy_hash") as mock_hash:
            mock_hash.return_value = "hash_now_different"

            with pytest.raises(PolicyChangedError) as exc_info:
                spine.resume(checkpoint_id="CP_policy_e2e_test")

            assert "hash_at_checkpoint_time" in str(exc_info.value)
            assert "hash_now_different" in str(exc_info.value)

        # BLOCKED terminal packet emitted
        terminal_packets = list(
            (clean_repo_root / "artifacts" / "terminal").glob("TP_*.yaml")
        )
        assert len(terminal_packets) == 1

        with open(terminal_packets[0]) as f:
            tp_data = yaml.safe_load(f)
        assert tp_data["outcome"] == "BLOCKED"
        assert "POLICY_CHANGED_MID_RUN" in tp_data["reason"]

        # Checkpoint YAML still exists
        cp_file = clean_repo_root / "artifacts" / "checkpoints" / "CP_policy_e2e_test.yaml"
        assert cp_file.exists()


# ── Test Class 3: CLI resume Command ─────────────────────────────────────────


class TestCLIResumeCommand:
    """Prove: CLI `spine resume` routes correctly and returns proper exit codes."""

    def test_cmd_spine_resume_approved_exits_0(self, temp_repo, capsys):
        """spine resume with PASS outcome exits 0."""
        mocked_result = {
            "outcome": "PASS",
            "state": "RESUMED",
            "run_id": "run_resume_1",
            "commit_hash": "abc123def456",
            "resumed": True,
        }

        with patch("runtime.cli.detect_repo_root", return_value=temp_repo):
            with patch(
                "runtime.orchestration.loop.spine.LoopSpine.resume",
                return_value=mocked_result,
            ):
                with patch(
                    "sys.argv",
                    ["runtime", "spine", "resume", "CP_run_resume_1_2"],
                ):
                    assert main() == 0

    def test_cmd_spine_resume_policy_changed_exits_1(self, temp_repo, capsys):
        """spine resume with PolicyChangedError exits 1."""
        with patch("runtime.cli.detect_repo_root", return_value=temp_repo):
            with patch(
                "runtime.orchestration.loop.spine.LoopSpine.resume",
                side_effect=PolicyChangedError(
                    checkpoint_hash="old_hash",
                    current_hash="new_hash",
                ),
            ):
                with patch(
                    "sys.argv",
                    ["runtime", "spine", "resume", "CP_run_policy_1_2"],
                ):
                    assert main() == 1
                    captured = capsys.readouterr()
                    assert "Policy changed" in captured.err

    def test_cmd_spine_resume_rejected_exits_1(self, temp_repo, capsys):
        """spine resume with BLOCKED/rejected outcome exits 1."""
        mocked_result = {
            "outcome": "BLOCKED",
            "reason": "checkpoint_rejected",
            "state": "TERMINAL",
            "run_id": "run_rejected_1",
        }

        with patch("runtime.cli.detect_repo_root", return_value=temp_repo):
            with patch(
                "runtime.orchestration.loop.spine.LoopSpine.resume",
                return_value=mocked_result,
            ):
                with patch(
                    "sys.argv",
                    ["runtime", "spine", "resume", "CP_run_rejected_1_2"],
                ):
                    assert main() == 1
