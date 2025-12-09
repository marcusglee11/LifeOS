import pytest
import os
import json
import tempfile
from runtime.engine import RuntimeFSM, RuntimeState, GovernanceError

def test_fsm_determinism():
    # 1. Verification of identical execution
    # Set up environ if needed (strict mode off for test ease unless testing strict)
    os.environ["COO_STRICT_MODE"] = "0"
    
    fsm1 = RuntimeFSM()
    fsm1.transition_to(RuntimeState.AMENDMENT_PREP)
    fsm1.transition_to(RuntimeState.AMENDMENT_EXEC)
    
    fsm2 = RuntimeFSM()
    fsm2.transition_to(RuntimeState.AMENDMENT_PREP)
    fsm2.transition_to(RuntimeState.AMENDMENT_EXEC)
    
    assert fsm1.current_state == fsm2.current_state
    assert fsm1.history == fsm2.history
    assert fsm1.current_state == RuntimeState.AMENDMENT_EXEC

def test_fsm_invalid_transition():
    fsm = RuntimeFSM()
    # INIT -> GATES is invalid
    with pytest.raises(GovernanceError):
        fsm.transition_to(RuntimeState.GATES)
    
    # check that it entered ERROR state
    assert fsm.current_state == RuntimeState.ERROR


# ============ FP-001 Tests ============

def test_fp001_strict_mode_explicit_true():
    """FP-001: Construct FSM with explicit strict_mode=True and verify strict transitions succeed."""
    fsm = RuntimeFSM(strict_mode=True)
    
    # Navigate to CEO_REVIEW (strict state) - should succeed with strict_mode=True
    fsm.transition_to(RuntimeState.AMENDMENT_PREP)
    fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
    fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
    fsm.transition_to(RuntimeState.CEO_REVIEW)  # Strict state
    
    assert fsm.current_state == RuntimeState.CEO_REVIEW
    assert fsm._strict_mode == True

def test_fp001_strict_mode_explicit_false():
    """FP-001: Construct FSM with strict_mode=False - transition to strict states should fail."""
    fsm = RuntimeFSM(strict_mode=False)
    
    # Navigate toward CEO_REVIEW
    fsm.transition_to(RuntimeState.AMENDMENT_PREP)
    fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
    fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
    
    # CEO_REVIEW is a strict state - should trigger _force_error and raise GovernanceError
    with pytest.raises(GovernanceError):
        fsm.transition_to(RuntimeState.CEO_REVIEW)
    
    assert fsm.current_state == RuntimeState.ERROR
    assert fsm._strict_mode == False

def test_fp001_strict_mode_from_env():
    """FP-001: Verify strict_mode defaults to environment variable when not specified."""
    os.environ["COO_STRICT_MODE"] = "1"
    fsm = RuntimeFSM()  # No explicit strict_mode
    assert fsm._strict_mode == True
    
    os.environ["COO_STRICT_MODE"] = "0"
    fsm2 = RuntimeFSM()
    assert fsm2._strict_mode == False

def test_fp001_force_error_raises_governance_error():
    """FP-001: Verify _force_error raises GovernanceError after calling raise_question."""
    fsm = RuntimeFSM(strict_mode=False)
    
    with pytest.raises(GovernanceError) as excinfo:
        fsm._force_error("Test error reason")
    
    assert fsm.current_state == RuntimeState.ERROR
    assert "Test error reason" in str(excinfo.value)

def test_fp001_validate_history_valid():
    """FP-001: Verify _validate_history passes for valid history."""
    fsm = RuntimeFSM(strict_mode=True)
    fsm.transition_to(RuntimeState.AMENDMENT_PREP)
    fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
    
    # Should not raise - history is valid
    fsm._validate_history()
    assert fsm.current_state == RuntimeState.AMENDMENT_EXEC

def test_fp001_validate_history_invalid():
    """FP-001: Verify _validate_history fails for invalid history."""
    fsm = RuntimeFSM(strict_mode=True)
    
    # Manually set invalid history (INIT -> GATES is not allowed)
    fsm._history = [RuntimeState.INIT, RuntimeState.GATES]
    
    with pytest.raises(GovernanceError) as excinfo:
        fsm._validate_history()
    
    assert fsm.current_state == RuntimeState.ERROR
    assert "not allowed" in str(excinfo.value)


# ============ H-002 Tests ============

def test_h002_checkpoint_round_trip():
    """H-002: Verify checkpoint save/load round-trip with coherent paths."""
    with tempfile.TemporaryDirectory() as tmp_amu0:
        # Create pinned_context.json required by checkpoint_state
        context_path = os.path.join(tmp_amu0, "pinned_context.json")
        with open(context_path, "w") as f:
            json.dump({"mock_time": "2025-12-09T12:00:00Z"}, f)
        
        # Create FSM and transition to a checkpointable state
        fsm = RuntimeFSM(strict_mode=True)
        fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        fsm.transition_to(RuntimeState.CEO_REVIEW)
        fsm.transition_to(RuntimeState.FREEZE_PREP)
        fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        fsm.transition_to(RuntimeState.CAPTURE_AMU0)  # Checkpointable state
        
        saved_state = fsm.current_state
        saved_history = fsm.history
        
        # Checkpoint
        fsm.checkpoint_state("test_checkpoint", tmp_amu0)
        
        # Verify files were created in the right location
        checkpoints_dir = os.path.join(tmp_amu0, "checkpoints")
        checkpoint_file = os.path.join(checkpoints_dir, "fsm_checkpoint_test_checkpoint.json")
        sig_file = f"{checkpoint_file}.sig"
        
        assert os.path.exists(checkpoint_file), "Checkpoint file should exist under amu0_path/checkpoints/"
        assert os.path.exists(sig_file), "Signature file should exist"
        
        # Create a new FSM and load the checkpoint
        fsm2 = RuntimeFSM(strict_mode=True)
        fsm2.load_checkpoint("test_checkpoint", tmp_amu0)
        
        # Verify state and history match
        assert fsm2.current_state == saved_state
        assert fsm2.history == saved_history
