import pytest
import os
from runtime.engine import RuntimeFSM, RuntimeState

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
    with pytest.raises(Exception) as excinfo: # helper raises generic Exception or GovernanceError
        fsm.transition_to(RuntimeState.GATES)
    
    # check that it entered ERROR state
    assert fsm.current_state == RuntimeState.ERROR
