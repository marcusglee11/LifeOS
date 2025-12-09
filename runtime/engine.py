from enum import Enum, auto
from typing import Optional, List, Dict, Any
import os
import json
from .util.questions import raise_question, QuestionType

class RuntimeState(Enum):
    """
    Canonical FSM States for COO Runtime v1.0.
    Strictly defined in COO_RUNTIME_SPECIFICATION_v1.0.md.
    """
    INIT = auto()
    AMENDMENT_PREP = auto()
    AMENDMENT_EXEC = auto()
    AMENDMENT_VERIFY = auto()
    CEO_REVIEW = auto()
    FREEZE_PREP = auto()
    FREEZE_ACTIVATED = auto()
    CAPTURE_AMU0 = auto()
    MIGRATION_SEQUENCE = auto()
    GATES = auto()
    # REPLAY state removed (B6) - Gate F runs in GATES, then transitions to CEO_FINAL_REVIEW
    CEO_FINAL_REVIEW = auto()
    COMPLETE = auto()
    ERROR = auto()

class GovernanceError(Exception):
    """Raised when a governance invariant is violated."""
    pass

class RuntimeFSM:
    """
    Deterministic Finite State Machine for the COO Runtime.
    Enforces strict linear progression and halts on ambiguity.
    """

    def __init__(self, strict_mode: Optional[bool] = None):
        """
        Initialize the FSM.
        
        Args:
            strict_mode: If None, reads from COO_STRICT_MODE env var (default False).
                        If provided, uses that value directly for deterministic config.
        """
        self.__current_state = RuntimeState.INIT
        self._history: List[RuntimeState] = [RuntimeState.INIT]
        
        # FP-001: Strict-mode captured at construction for determinism
        if strict_mode is None:
            self._strict_mode = (os.environ.get("COO_STRICT_MODE", "0") == "1")
        else:
            self._strict_mode = strict_mode
        
        # Define allowed transitions (Strict Linear Progression)
        self._transitions: Dict[RuntimeState, List[RuntimeState]] = {
            RuntimeState.INIT: [RuntimeState.AMENDMENT_PREP, RuntimeState.ERROR],
            RuntimeState.AMENDMENT_PREP: [RuntimeState.AMENDMENT_EXEC, RuntimeState.ERROR],
            RuntimeState.AMENDMENT_EXEC: [RuntimeState.AMENDMENT_VERIFY, RuntimeState.ERROR],
            RuntimeState.AMENDMENT_VERIFY: [RuntimeState.CEO_REVIEW, RuntimeState.ERROR],
            RuntimeState.CEO_REVIEW: [RuntimeState.FREEZE_PREP, RuntimeState.ERROR],
            RuntimeState.FREEZE_PREP: [RuntimeState.FREEZE_ACTIVATED, RuntimeState.ERROR],
            RuntimeState.FREEZE_ACTIVATED: [RuntimeState.CAPTURE_AMU0, RuntimeState.ERROR],
            RuntimeState.CAPTURE_AMU0: [RuntimeState.MIGRATION_SEQUENCE, RuntimeState.ERROR],
            RuntimeState.MIGRATION_SEQUENCE: [RuntimeState.GATES, RuntimeState.ERROR, RuntimeState.CAPTURE_AMU0],
            RuntimeState.GATES: [RuntimeState.CEO_FINAL_REVIEW, RuntimeState.ERROR, RuntimeState.CAPTURE_AMU0],
            # RuntimeState.REPLAY removed
            RuntimeState.CEO_FINAL_REVIEW: [RuntimeState.COMPLETE, RuntimeState.ERROR],
            RuntimeState.COMPLETE: [], # Terminal state
            RuntimeState.ERROR: [],    # Terminal state (requires manual intervention/restart)
        }
        
        # Attempt to load state from disk - REMOVED (A.3)
        # self.load_state()

    @property
    def current_state(self) -> RuntimeState:
        return self.__current_state

    @property
    def history(self) -> List[RuntimeState]:
        return list(self._history)

    def transition_to(self, next_state: RuntimeState) -> None:
        """
        Executes a state transition.
        Raises GovernanceError if the transition is invalid.
        """
        if next_state not in self._transitions[self.__current_state]:
            # Invalid transition attempt -> Immediate Halt & Error
            self._force_error(f"Invalid transition attempted: {self.__current_state} -> {next_state}")
            return

        # Governance State Hardening (R3)
        strict_states = [
            RuntimeState.FREEZE_ACTIVATED,
            RuntimeState.CEO_REVIEW,
            RuntimeState.CEO_FINAL_REVIEW
        ]
        
        if next_state in strict_states:
            if not self._strict_mode:
                self._force_error(f"Strict Mode Required for transition to {next_state}")
                return

        self.__current_state = next_state
        self._history.append(next_state)
        # Legacy fsm_state.json persistence is removed entirely. (A.3)
        # Checkpoints are now explicit via checkpoint_state().

    def _force_error(self, reason: str) -> None:
        """
        Forces the FSM into the ERROR state.
        
        FP-001: Calls raise_question for logging/alerting, then raises GovernanceError.
        Since raise_question itself raises, we catch it and re-raise as GovernanceError.
        """
        self.__current_state = RuntimeState.ERROR
        self._history.append(RuntimeState.ERROR)
        try:
            raise_question(QuestionType.FSM_STATE_ERROR, f"RUNTIME HALT: {reason}. Please raise a QUESTION to the CEO.")
        except Exception:
            pass  # Logged/alerted, now raise GovernanceError
        raise GovernanceError(reason)

    def assert_state(self, expected_state: RuntimeState) -> None:
        """
        Verifies that the FSM is in the expected state.
        """
        if self.__current_state != expected_state:
            self._force_error(f"State assertion failed. Expected {expected_state}, got {self.__current_state}")

    def checkpoint_state(self, checkpoint_name: str, amu0_path: str) -> None:
        """
        Creates a signed checkpoint of the FSM state (A.3).
        Allowed only at constitutional boundaries:
        - After CAPTURE_AMU0
        - After GATES
        - Before CEO_FINAL_REVIEW (which is effectively after GATES transition)
        
        FP-002: Checkpoints are anchored under amu0_path/checkpoints/ for determinism.
        """
        allowed_states = [
            RuntimeState.CAPTURE_AMU0,
            RuntimeState.GATES,
            RuntimeState.CEO_FINAL_REVIEW
        ]
        
        # FP-002: Use _force_error for illegal checkpoint state (governance error)
        if self.__current_state not in allowed_states:
            self._force_error(f"Checkpointing not allowed in state {self.__current_state}")
            return

        # Get Pinned Time (A.3)
        context_path = os.path.join(amu0_path, "pinned_context.json")
        if not os.path.exists(context_path):
            self._force_error("pinned_context.json missing. Cannot checkpoint with pinned time.")
    def checkpoint_state(self, label: str, amu0_path: str) -> str:
        """
        Save current state to a checkpoint file.
        
        Args:
            label: Label for the checkpoint
            amu0_path: Path to AMU0 root explicitly passed in
            
        Returns:
            Path to the created checkpoint file.
        """
        # Load pinned context for deterministic timestamp
        # In strict mode, we rely purely on inputs, no internal time generation
        timestamp = None
        pinned_context_path = os.path.join(amu0_path, "pinned_context.json")
        if os.path.exists(pinned_context_path):
            with open(pinned_context_path, 'r') as f:
                context = json.load(f)
                timestamp = context.get('mock_time')
        
        checkpoint_data = {
            "state": self.current_state.name,
            "history": [s.name for s in self.history],
            "strict_mode": self._strict_mode
        }
        
        # Only add timestamp if found in deterministic context
        # If no pinned context exists, we deliberately omit the timestamp
        # to ensure the checkpoint file remains deterministic (no wall-clock drift).
        if timestamp:
            checkpoint_data["timestamp"] = timestamp
            
        # Ensure checkpoints directory exists within AMU0
        checkpoints_dir = os.path.join(amu0_path, "checkpoints")
        os.makedirs(checkpoints_dir, exist_ok=True)
            
        filename = f"fsm_checkpoint_{label}.json"
        filepath = os.path.join(checkpoints_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, sort_keys=True)
            
        return filepath

    def load_checkpoint(self, checkpoint_name: str, amu0_path: str) -> None:
        """
        Loads a signed FSM checkpoint.
        
        H-002: Must be called with the same amu0_path used in checkpoint_state
        to ensure path coherence.
        
        Args:
            checkpoint_name: Name of the checkpoint to load.
            amu0_path: Path to AMU0 directory (same as used in checkpoint_state).
        """
        # H-002: Use same checkpoints_dir as checkpoint_state
        checkpoints_dir = os.path.join(amu0_path, "checkpoints")
        filename = os.path.join(checkpoints_dir, f"fsm_checkpoint_{checkpoint_name}.json")
        sig_filename = f"{filename}.sig"
        
        if not os.path.exists(filename) or not os.path.exists(sig_filename):
            self._force_error(f"Checkpoint {checkpoint_name} missing at {checkpoints_dir}")
            return
            
        # R6.4 G1: Verify using unified Signature protocol
        from .util.crypto import Signature
        
        # Single-read verification
        with open(filename, "rb") as f:
            payload_bytes = f.read()
        with open(sig_filename, "rb") as f:
            signature = f.read()

        if not Signature.verify_data(payload_bytes, signature):
            self._force_error(f"FSM Checkpoint {checkpoint_name} Signature Invalid!")
            return
            
        # H-002: Single-read - decode JSON from verified bytes
        data = json.loads(payload_bytes.decode("utf-8"))
        self.__current_state = RuntimeState[data["current_state"]]
        self._history = [RuntimeState[s] for s in data["history"]]
        
        # FP-001: Validate history after load
        self._validate_history()

    def _validate_history(self) -> None:
        """
        FP-001: Validates that the loaded history is a valid path in the transition graph.
        
        Ensures:
        - History is non-empty
        - Each transition in history is allowed by the transitions table
        
        Raises GovernanceError if history is invalid.
        """
        if not self._history:
            self._force_error("Invalid history: empty history list")
            return
        
        # Check that first state is INIT
        if self._history[0] != RuntimeState.INIT:
            self._force_error(f"Invalid history: must start with INIT, got {self._history[0]}")
            return
        
        # Replay transitions to validate path
        for i in range(len(self._history) - 1):
            from_state = self._history[i]
            to_state = self._history[i + 1]
            
            if to_state not in self._transitions.get(from_state, []):
                self._force_error(f"Invalid history path: {from_state.name} → {to_state.name} not allowed")
                return
