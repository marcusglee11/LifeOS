# Review_Packet_Hardening_Pass_v0.3

**Title:** Review_Packet_Hardening_Pass_v0.3  
**Version:** v0.3  
**Author:** Antigravity Agent  
**Date:** 2025-12-09  
**Source Packet:** Runtime_Hardening_Fix_Pack_v0.2 (Comprehensive)  
**Scope:** Includes all files listed in Appendix.

---

## Summary

This packet applies the comprehensive hardening corrections from Fix Pack v0.2:

| Issue | Status | Key Change |
|-------|--------|------------|
| H-001 | ✅ Confirmed | FSM strict_mode deterministic, _force_error, _validate_history |
| H-002 | ✅ Fixed | `load_checkpoint` now requires `amu0_path` param for path coherence |
| H-003 | ✅ Fixed | `changed_files` references `docs/INDEX_v1.1.md` |
| H-004 | ✅ Fixed | Builder rolled back to docs-only, INDEX_v1.1.md, .md files only |
| H-005 | ✅ Confirmed | Verifier cwd param works |
| H-006 | ✅ Confirmed | effective_decision in logs |
| H-007 | ✅ Complete | H-002 round-trip test added (only this test was added; no docs index equivalence test) |

**Key Corrections from v0.2 Candidate:**
- Removed out-of-scope domains (config, artifacts, system, docsteward)
- Removed daily_summary task type
- Restored INDEX_v1.1.md filename (was INDEX.md)
- Restored .md-only indexing (was all files)
- Fixed load_checkpoint path coherence

---

## Verification Results

- **27 tests passed** (including new H-002 round-trip test)
- `python -m recursive_kernel.runner` → SUCCESS
- `docs/INDEX_v1.1.md` regenerated with .md files only
- Log shows `effective_decision: AUTO_MERGE_ALLOWED`

---

## Post-Conditions Met

✅ **FSM**: Strict-mode deterministic, checkpoints coherent under `amu0_path/checkpoints/`  
✅ **Recursive Kernel**: Repo root cwd-independent, pinned timestamps, effective_decision  
✅ **Builder**: Only docs domain, INDEX_v1.1.md, .md files only  
✅ **Verifier**: Optional cwd param preserved  
✅ **No scope creep**: No new domains or tasks introduced

---

## Appendix — Flattened Code

### File: runtime/engine.py
```python
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
            RuntimeState.CEO_FINAL_REVIEW: [RuntimeState.COMPLETE, RuntimeState.ERROR],
            RuntimeState.COMPLETE: [],
            RuntimeState.ERROR: [],
        }

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
            self._force_error(f"Invalid transition attempted: {self.__current_state} -> {next_state}")
            return

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
            pass
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
        
        if self.__current_state not in allowed_states:
            self._force_error(f"Checkpointing not allowed in state {self.__current_state}")
            return

        context_path = os.path.join(amu0_path, "pinned_context.json")
        if not os.path.exists(context_path):
            self._force_error("pinned_context.json missing. Cannot checkpoint with pinned time.")
            return
            
        with open(context_path, "r") as f:
            context = json.load(f)
        
        if "mock_time" not in context:
            self._force_error("mock_time missing in pinned_context.json")
            return
            
        timestamp = context["mock_time"]

        data = {
            "checkpoint_name": checkpoint_name,
            "current_state": self.__current_state.name,
            "history": [s.name for s in self._history],
            "timestamp": timestamp
        }
        
        payload_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        
        from .util.crypto import Signature
        try:
            signature = Signature.sign_data(payload_bytes)
        except Exception as e:
            self._force_error(f"Signing failed: {e}")
            return
        
        checkpoints_dir = os.path.join(amu0_path, "checkpoints")
        os.makedirs(checkpoints_dir, exist_ok=True)
        
        filename = os.path.join(checkpoints_dir, f"fsm_checkpoint_{checkpoint_name}.json")
        sig_filename = f"{filename}.sig"
        
        with open(filename, "w") as f:
            json.dump(data, f, sort_keys=True)
            
        with open(sig_filename, "wb") as f:
            f.write(signature)

    def load_checkpoint(self, checkpoint_name: str, amu0_path: str) -> None:
        """
        Loads a signed FSM checkpoint.
        
        H-002: Must be called with the same amu0_path used in checkpoint_state
        to ensure path coherence.
        
        Args:
            checkpoint_name: Name of the checkpoint to load.
            amu0_path: Path to AMU0 directory (same as used in checkpoint_state).
        """
        checkpoints_dir = os.path.join(amu0_path, "checkpoints")
        filename = os.path.join(checkpoints_dir, f"fsm_checkpoint_{checkpoint_name}.json")
        sig_filename = f"{filename}.sig"
        
        if not os.path.exists(filename) or not os.path.exists(sig_filename):
            self._force_error(f"Checkpoint {checkpoint_name} missing at {checkpoints_dir}")
            return
            
        from .util.crypto import Signature
        
        with open(filename, "rb") as f:
            payload_bytes = f.read()
        with open(sig_filename, "rb") as f:
            signature = f.read()

        if not Signature.verify_data(payload_bytes, signature):
            self._force_error(f"FSM Checkpoint {checkpoint_name} Signature Invalid!")
            return
            
        data = json.loads(payload_bytes.decode("utf-8"))
        self.__current_state = RuntimeState[data["current_state"]]
        self._history = [RuntimeState[s] for s in data["history"]]
        
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
        
        if self._history[0] != RuntimeState.INIT:
            self._force_error(f"Invalid history: must start with INIT, got {self._history[0]}")
            return
        
        for i in range(len(self._history) - 1):
            from_state = self._history[i]
            to_state = self._history[i + 1]
            
            if to_state not in self._transitions.get(from_state, []):
                self._force_error(f"Invalid history path: {from_state.name} → {to_state.name} not allowed")
                return
```

---

### File: recursive_kernel/runner.py
```python
import os
import json
import datetime
import sys
from .planner import Planner, Task
from .builder import Builder
from .verifier import Verifier
from .autogate import AutoGate, GateDecision

# FP-003: Derive repo root from module location for cwd-independence
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class RecursiveRunner:
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.config_path = os.path.join(repo_root, "config", "recursive_kernel_config.yaml")
        self.backlog_path = os.path.join(repo_root, "config", "backlog.yaml")
        self.planner = Planner(self.config_path, self.backlog_path)
        self.builder = Builder(repo_root)
        self.config = self.planner.config
        self.verifier = Verifier(self.config.get("test_command", "pytest"))
        self.gate = AutoGate(self.config)
        self.logs_dir = os.path.join(repo_root, "logs", "recursive_runs")
        os.makedirs(self.logs_dir, exist_ok=True)

    def run(self):
        print("Recursive Kernel Runner v0.1")
        
        try:
            task = self.planner.plan_next_task()
        except Exception as e:
            print(f"Planning failed: {e}")
            return

        if not task:
            print("No eligible tasks found.")
            return

        print(f"Selected task: {task.id} - {task.description} ({task.domain})")
        
        run_ts = datetime.datetime.now()

        success = self.builder.build(task)
        
        if not success:
            print(f"Builder fail or no builder for tasks of type {task.type}")
            self._log_result(task, applied=False, verified=False, decision="NONE", reason="Builder failed", run_ts=run_ts)
            return

        print("Build step complete. Verifying...")

        verified = self.verifier.verify()
        print(f"Verification result: {'PASS' if verified else 'FAIL'}")

        changed_files = []
        if task.domain == 'docs' and task.type == 'rebuild_index':
            changed_files = ["docs/INDEX_v1.1.md"]
        
        diff_lines = 10
        
        decision = self.gate.evaluate(changed_files, diff_lines)
        print(f"Gate Decision: {decision.name}")

        self._log_result(task, applied=True, verified=verified, decision=decision.name, run_ts=run_ts)
        
        if decision == GateDecision.AUTO_MERGE and verified:
            print("Change is safe to merge. (Simulation: Committed)")
        else:
            print("Change requires human review.")

    def _log_result(self, task: Task, applied: bool, verified: bool, decision: str, run_ts: datetime.datetime, reason: str = ""):
        """
        Log the result of a task execution.
        
        FP-003: Uses pinned run_ts for both timestamp field and filename.
        FP-006: Includes effective_decision field.
        """
        if decision == "AUTO_MERGE" and verified:
            effective_decision = "AUTO_MERGE_ALLOWED"
        elif decision == "AUTO_MERGE" and not verified:
            effective_decision = "AUTO_MERGE_BLOCKED_BY_TESTS"
        else:
            effective_decision = "HUMAN_REVIEW"
        
        log_entry = {
            "timestamp": run_ts.isoformat(),
            "task_id": task.id,
            "domain": task.domain,
            "applied": applied,
            "verified": verified,
            "gate_decision": decision,
            "effective_decision": effective_decision,
            "reason": reason
        }
        filename = f"run_{run_ts.strftime('%Y%m%d_%H%M%S')}_{task.id}.json"
        path = os.path.join(self.logs_dir, filename)
        with open(path, "w") as f:
            json.dump(log_entry, f, indent=2)
        print(f"Log written to {path}")

if __name__ == "__main__":
    runner = RecursiveRunner(REPO_ROOT)
    runner.run()
```

---

### File: recursive_kernel/builder.py
```python
import os
from .planner import Task
from typing import Optional, List

class Builder:
    """
    Builder for recursive kernel tasks.
    
    H-004: Explicitly accepts repo_root to eliminate cwd dependence.
    Only handles docs index rebuilding in this pass.
    """
    
    def __init__(self, repo_root: str):
        """
        Initialize the Builder.
        
        Args:
            repo_root: Absolute path to the repository root.
        """
        self.repo_root = repo_root
    
    def build(self, task: Task) -> bool:
        """
        Execute a build task.
        
        H-004: Only docs domain is supported in this pass.
        """
        if task.domain == "docs" and task.type == "rebuild_index":
            return self._rebuild_docs_index()
        return False

    def _rebuild_docs_index(self, exclude_paths: Optional[List[str]] = None) -> bool:
        """
        Rebuild the docs/INDEX_v1.1.md file.
        
        H-004 Invariants:
        - Only .md files are indexed
        - INDEX_v1.1.md itself is excluded
        - Paths are relative from docs/, normalized to /
        - List is sorted lexicographically
        
        Args:
            exclude_paths: Optional list of relative paths to exclude (future extension).
        
        Returns:
            True if successful, False otherwise.
        """
        if exclude_paths is None:
            exclude_paths = []
        
        docs_root = os.path.join(self.repo_root, "docs")
        index_filename = "INDEX_v1.1.md"
        index_path = os.path.join(docs_root, index_filename)
        
        if not os.path.exists(docs_root):
            return False

        files_to_index = []
        for root, dirs, files in os.walk(docs_root):
            for file in files:
                if file.endswith(".md") and file != index_filename:
                    rel_path = os.path.relpath(os.path.join(root, file), docs_root).replace('\\', '/')
                    
                    excluded = any(rel_path.startswith(ep) for ep in exclude_paths)
                    if not excluded:
                        files_to_index.append(rel_path)
        
        files_to_index.sort()
        
        content = "# Documentation Index v1.1\n\n"
        for f in files_to_index:
            content += f"- [{f}](./{f})\n"
            
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return True
```

---

### File: recursive_kernel/verifier.py
```python
import subprocess
import shlex
import os
import sys
from typing import Optional

class Verifier:
    """
    Verifier for recursive kernel tasks.
    
    FP-005: Supports optional cwd parameter for explicit working directory control.
    """
    
    def __init__(self, test_command: str, cwd: Optional[str] = None):
        """
        Initialize the Verifier.
        
        Args:
            test_command: The command to run for verification.
                         Preferred default is "python -m pytest" for cross-platform determinism.
            cwd: Optional working directory. If None, uses current process cwd.
        """
        self.test_command = test_command
        self.cwd = cwd

    def verify(self) -> bool:
        try:
            print(f"Running verification command: {self.test_command}")
            if sys.platform == "win32":
                args = self.test_command
                u_shell = True
            else:
                args = shlex.split(self.test_command)
                u_shell = False
                
            result = subprocess.run(args, shell=u_shell, capture_output=True, text=True, cwd=self.cwd)
            if result.returncode != 0:
                print(f"Verification failed:\n{result.stdout}\n{result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"Verification failed with exception: {e}")
            return False
```

---

### File: config/recursive_kernel_config.yaml
```yaml
safe_domains:
  - docs
  - tests_doc

test_command: "pytest"

max_diff_lines_auto_merge: 200

risk_rules:
  low_risk_paths:
    - "docs/"
    - "tests_doc/"
```

---

### File: config/backlog.yaml
```yaml
tasks:
  - id: "TASK-001"
    domain: "docs"
    type: "rebuild_index"
    status: "todo"
    description: "Rebuild the documentation index (docs/INDEX_v1.1.md)."
```

---

### File: runtime/tests/test_engine.py
```python
import pytest
import os
import json
import tempfile
from runtime.engine import RuntimeFSM, RuntimeState, GovernanceError

def test_fsm_determinism():
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
    with pytest.raises(GovernanceError):
        fsm.transition_to(RuntimeState.GATES)
    
    assert fsm.current_state == RuntimeState.ERROR


# ============ FP-001 Tests ============

def test_fp001_strict_mode_explicit_true():
    """FP-001: Construct FSM with explicit strict_mode=True and verify strict transitions succeed."""
    fsm = RuntimeFSM(strict_mode=True)
    
    fsm.transition_to(RuntimeState.AMENDMENT_PREP)
    fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
    fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
    fsm.transition_to(RuntimeState.CEO_REVIEW)
    
    assert fsm.current_state == RuntimeState.CEO_REVIEW
    assert fsm._strict_mode == True

def test_fp001_strict_mode_explicit_false():
    """FP-001: Construct FSM with strict_mode=False - transition to strict states should fail."""
    fsm = RuntimeFSM(strict_mode=False)
    
    fsm.transition_to(RuntimeState.AMENDMENT_PREP)
    fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
    fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
    
    with pytest.raises(GovernanceError):
        fsm.transition_to(RuntimeState.CEO_REVIEW)
    
    assert fsm.current_state == RuntimeState.ERROR
    assert fsm._strict_mode == False

def test_fp001_strict_mode_from_env():
    """FP-001: Verify strict_mode defaults to environment variable when not specified."""
    os.environ["COO_STRICT_MODE"] = "1"
    fsm = RuntimeFSM()
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
    
    fsm._validate_history()
    assert fsm.current_state == RuntimeState.AMENDMENT_EXEC

def test_fp001_validate_history_invalid():
    """FP-001: Verify _validate_history fails for invalid history."""
    fsm = RuntimeFSM(strict_mode=True)
    
    fsm._history = [RuntimeState.INIT, RuntimeState.GATES]
    
    with pytest.raises(GovernanceError) as excinfo:
        fsm._validate_history()
    
    assert fsm.current_state == RuntimeState.ERROR
    assert "not allowed" in str(excinfo.value)


# ============ H-002 Tests ============

def test_h002_checkpoint_round_trip():
    """H-002: Verify checkpoint save/load round-trip with coherent paths."""
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
        
        saved_state = fsm.current_state
        saved_history = fsm.history
        
        fsm.checkpoint_state("test_checkpoint", tmp_amu0)
        
        checkpoints_dir = os.path.join(tmp_amu0, "checkpoints")
        checkpoint_file = os.path.join(checkpoints_dir, "fsm_checkpoint_test_checkpoint.json")
        sig_file = f"{checkpoint_file}.sig"
        
        assert os.path.exists(checkpoint_file), "Checkpoint file should exist under amu0_path/checkpoints/"
        assert os.path.exists(sig_file), "Signature file should exist"
        
        fsm2 = RuntimeFSM(strict_mode=True)
        fsm2.load_checkpoint("test_checkpoint", tmp_amu0)
        
        assert fsm2.current_state == saved_state
        assert fsm2.history == saved_history
```

