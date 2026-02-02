"""
FSM Checkpoint Edge Case Tests

Tests for checkpoint corruption, signature verification failures,
and invalid state transition scenarios in RuntimeFSM.

Per Edge Case Testing Implementation Plan - Phase 1.1
"""
import pytest
import os
import json
import tempfile
from pathlib import Path
from runtime.engine import RuntimeFSM, RuntimeState, GovernanceError


class TestCheckpointCorruption:
    """Tests for corrupted checkpoint JSON scenarios."""

    def test_checkpoint_truncated_json(self):
        """Truncated JSON in checkpoint triggers GovernanceError."""
        with tempfile.TemporaryDirectory() as tmp_amu0:
            # Create pinned_context.json
            context_path = os.path.join(tmp_amu0, "pinned_context.json")
            with open(context_path, "w") as f:
                json.dump({"mock_time": "2025-12-09T12:00:00Z"}, f)

            # Create checkpoint and corrupt it
            fsm = RuntimeFSM(strict_mode=True)
            fsm.transition_to(RuntimeState.AMENDMENT_PREP)
            fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
            fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
            fsm.transition_to(RuntimeState.CEO_REVIEW)
            fsm.transition_to(RuntimeState.FREEZE_PREP)
            fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
            fsm.transition_to(RuntimeState.CAPTURE_AMU0)

            checkpoint_path = fsm.checkpoint_state("test", tmp_amu0)

            # Truncate checkpoint file
            with open(checkpoint_path, 'rb') as f:
                data = f.read()
            with open(checkpoint_path, 'wb') as f:
                f.write(data[:len(data)//2])  # Write only half

            # Try to load truncated checkpoint
            fsm2 = RuntimeFSM(strict_mode=True)
            with pytest.raises(GovernanceError) as exc_info:
                fsm2.load_checkpoint("test", tmp_amu0)

            assert "Signature Invalid" in str(exc_info.value)

    def test_checkpoint_invalid_json_escapes(self):
        """Invalid JSON escapes in checkpoint trigger GovernanceError."""
        with tempfile.TemporaryDirectory() as tmp_amu0:
            context_path = os.path.join(tmp_amu0, "pinned_context.json")
            with open(context_path, "w") as f:
                json.dump({"mock_time": "2025-12-09T12:00:00Z"}, f)

            checkpoints_dir = os.path.join(tmp_amu0, "checkpoints")
            os.makedirs(checkpoints_dir, exist_ok=True)

            # Write invalid JSON with bad escape
            checkpoint_path = os.path.join(checkpoints_dir, "fsm_checkpoint_bad.json")
            with open(checkpoint_path, 'w') as f:
                f.write('{"state": "INIT", "history": ["\\x"]}\n')

            # Create dummy signature
            sig_path = f"{checkpoint_path}.sig"
            with open(sig_path, 'wb') as f:
                f.write(b"dummy_sig")

            fsm = RuntimeFSM(strict_mode=True)
            with pytest.raises(GovernanceError):
                fsm.load_checkpoint("bad", tmp_amu0)

    def test_checkpoint_empty_file(self):
        """Empty checkpoint file (0 bytes) triggers GovernanceError."""
        with tempfile.TemporaryDirectory() as tmp_amu0:
            checkpoints_dir = os.path.join(tmp_amu0, "checkpoints")
            os.makedirs(checkpoints_dir, exist_ok=True)

            # Create empty checkpoint
            checkpoint_path = os.path.join(checkpoints_dir, "fsm_checkpoint_empty.json")
            Path(checkpoint_path).touch()

            # Create dummy signature
            sig_path = f"{checkpoint_path}.sig"
            Path(sig_path).touch()

            fsm = RuntimeFSM(strict_mode=True)
            with pytest.raises(GovernanceError):
                fsm.load_checkpoint("empty", tmp_amu0)

    def test_checkpoint_unmatched_braces(self):
        """Unmatched braces in checkpoint JSON trigger GovernanceError."""
        with tempfile.TemporaryDirectory() as tmp_amu0:
            checkpoints_dir = os.path.join(tmp_amu0, "checkpoints")
            os.makedirs(checkpoints_dir, exist_ok=True)

            checkpoint_path = os.path.join(checkpoints_dir, "fsm_checkpoint_braces.json")
            with open(checkpoint_path, 'w') as f:
                f.write('{"state": "INIT", "history": ["INIT"')  # Missing closing braces

            sig_path = f"{checkpoint_path}.sig"
            with open(sig_path, 'wb') as f:
                f.write(b"dummy_sig")

            fsm = RuntimeFSM(strict_mode=True)
            with pytest.raises(GovernanceError):
                fsm.load_checkpoint("braces", tmp_amu0)


class TestSignatureVerification:
    """Tests for signature verification failures."""

    def test_missing_signature_file(self):
        """Missing signature file triggers GovernanceError."""
        with tempfile.TemporaryDirectory() as tmp_amu0:
            context_path = os.path.join(tmp_amu0, "pinned_context.json")
            with open(context_path, "w") as f:
                json.dump({"mock_time": "2025-12-09T12:00:00Z"}, f)

            fsm = RuntimeFSM(strict_mode=True)
            fsm.transition_to(RuntimeState.AMENDMENT_PREP)
            fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
            fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
            fsm.transition_to(RuntimeState.CEO_REVIEW)
            fsm.transition_to(RuntimeState.FREEZE_PREP)
            fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
            fsm.transition_to(RuntimeState.CAPTURE_AMU0)

            checkpoint_path = fsm.checkpoint_state("test", tmp_amu0)

            # Delete signature file
            sig_path = f"{checkpoint_path}.sig"
            os.remove(sig_path)

            fsm2 = RuntimeFSM(strict_mode=True)
            with pytest.raises(GovernanceError) as exc_info:
                fsm2.load_checkpoint("test", tmp_amu0)

            assert "missing" in str(exc_info.value).lower()

    def test_checkpoint_modified_after_signature(self):
        """Checkpoint modified after signature creation fails verification."""
        with tempfile.TemporaryDirectory() as tmp_amu0:
            context_path = os.path.join(tmp_amu0, "pinned_context.json")
            with open(context_path, "w") as f:
                json.dump({"mock_time": "2025-12-09T12:00:00Z"}, f)

            fsm = RuntimeFSM(strict_mode=True)
            fsm.transition_to(RuntimeState.AMENDMENT_PREP)
            fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
            fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
            fsm.transition_to(RuntimeState.CEO_REVIEW)
            fsm.transition_to(RuntimeState.FREEZE_PREP)
            fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
            fsm.transition_to(RuntimeState.CAPTURE_AMU0)

            checkpoint_path = fsm.checkpoint_state("test", tmp_amu0)

            # Modify checkpoint after signature
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            data['tampered'] = True
            with open(checkpoint_path, 'w') as f:
                json.dump(data, f)

            fsm2 = RuntimeFSM(strict_mode=True)
            with pytest.raises(GovernanceError) as exc_info:
                fsm2.load_checkpoint("test", tmp_amu0)

            assert "Signature Invalid" in str(exc_info.value)

    def test_corrupted_signature_file(self):
        """Corrupted signature file fails verification."""
        with tempfile.TemporaryDirectory() as tmp_amu0:
            context_path = os.path.join(tmp_amu0, "pinned_context.json")
            with open(context_path, "w") as f:
                json.dump({"mock_time": "2025-12-09T12:00:00Z"}, f)

            fsm = RuntimeFSM(strict_mode=True)
            fsm.transition_to(RuntimeState.AMENDMENT_PREP)
            fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
            fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
            fsm.transition_to(RuntimeState.CEO_REVIEW)
            fsm.transition_to(RuntimeState.FREEZE_PREP)
            fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
            fsm.transition_to(RuntimeState.CAPTURE_AMU0)

            checkpoint_path = fsm.checkpoint_state("test", tmp_amu0)

            # Corrupt signature
            sig_path = f"{checkpoint_path}.sig"
            with open(sig_path, 'wb') as f:
                f.write(b"corrupted_signature_data_12345")

            fsm2 = RuntimeFSM(strict_mode=True)
            with pytest.raises(GovernanceError) as exc_info:
                fsm2.load_checkpoint("test", tmp_amu0)

            assert "Signature Invalid" in str(exc_info.value)


class TestInvalidStateHistory:
    """Tests for invalid state transitions in history."""

    def test_invalid_state_transition_in_history(self):
        """Manually injected invalid transition in history triggers GovernanceError."""
        fsm = RuntimeFSM(strict_mode=True)

        # Manually inject invalid history (INIT -> GATES is not allowed)
        fsm._history = [RuntimeState.INIT, RuntimeState.GATES]

        with pytest.raises(GovernanceError) as exc_info:
            fsm._validate_history()

        assert fsm.current_state == RuntimeState.ERROR
        assert "not allowed" in str(exc_info.value).lower()

    def test_empty_history_validation(self):
        """Empty history triggers GovernanceError."""
        fsm = RuntimeFSM(strict_mode=True)
        fsm._history = []

        with pytest.raises(GovernanceError) as exc_info:
            fsm._validate_history()

        assert "empty" in str(exc_info.value).lower()


class TestStrictModeHandling:
    """Tests for strict_mode mismatches and edge cases."""

    def test_checkpoint_strict_mode_mismatch(self):
        """Loading checkpoint with different strict_mode still validates history."""
        with tempfile.TemporaryDirectory() as tmp_amu0:
            context_path = os.path.join(tmp_amu0, "pinned_context.json")
            with open(context_path, "w") as f:
                json.dump({"mock_time": "2025-12-09T12:00:00Z"}, f)

            # Create checkpoint with strict_mode=True
            fsm = RuntimeFSM(strict_mode=True)
            fsm.transition_to(RuntimeState.AMENDMENT_PREP)
            fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
            fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
            fsm.transition_to(RuntimeState.CEO_REVIEW)
            fsm.transition_to(RuntimeState.FREEZE_PREP)
            fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
            fsm.transition_to(RuntimeState.CAPTURE_AMU0)

            fsm.checkpoint_state("test", tmp_amu0)

            # Load with strict_mode=False - should still work if history is valid
            fsm2 = RuntimeFSM(strict_mode=False)
            fsm2.load_checkpoint("test", tmp_amu0)

            # Verify state loaded correctly
            assert fsm2.current_state == RuntimeState.CAPTURE_AMU0


class TestTerminalStateAssertions:
    """Tests for state assertions on terminal states."""

    def test_assert_state_on_error_state(self):
        """State assertion when FSM is in ERROR state."""
        fsm = RuntimeFSM(strict_mode=False)

        # Force into ERROR state
        with pytest.raises(GovernanceError):
            fsm.transition_to(RuntimeState.GATES)

        assert fsm.current_state == RuntimeState.ERROR

        # Assert on ERROR state should fail
        with pytest.raises(GovernanceError) as exc_info:
            fsm.assert_state(RuntimeState.INIT)

        assert "assertion failed" in str(exc_info.value).lower()

    def test_assert_state_on_complete_state(self):
        """State assertion when FSM is in COMPLETE state."""
        fsm = RuntimeFSM(strict_mode=True)

        # Navigate to COMPLETE
        fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        fsm.transition_to(RuntimeState.CEO_REVIEW)
        fsm.transition_to(RuntimeState.FREEZE_PREP)
        fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        fsm.transition_to(RuntimeState.CAPTURE_AMU0)
        fsm.transition_to(RuntimeState.MIGRATION_SEQUENCE)
        fsm.transition_to(RuntimeState.GATES)
        fsm.transition_to(RuntimeState.CEO_FINAL_REVIEW)
        fsm.transition_to(RuntimeState.COMPLETE)

        assert fsm.current_state == RuntimeState.COMPLETE

        # Correct assertion should pass
        fsm.assert_state(RuntimeState.COMPLETE)

        # Wrong assertion should fail
        with pytest.raises(GovernanceError) as exc_info:
            fsm.assert_state(RuntimeState.INIT)

        assert "assertion failed" in str(exc_info.value).lower()
