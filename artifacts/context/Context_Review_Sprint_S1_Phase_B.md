# Context Packet: Review of Sprint S1 Phase B

**Plan:** [Plan_Sprint_S1_Phase_B_v1.0.md](file:///C:/Users/cabra/Projects/LifeOS/artifacts/plans/Plan_Sprint_S1_Phase_B_v1.0.md)
**Date:** 2026-01-28
**Purpose:** Provide all necessary context for an AI reviewer to validate the implementation plan against the current codebase.

---

## 1. System State (LIFEOS_STATE.md)

```markdown
# LifeOS State

**Current Focus:** Phase 4 Preparation (Autonomous Construction)
**Active WIP:** Phase 3 Acceptance Fix (DONE)
**Last Updated:** 2026-01-26

---

## 🟥 IMMEDIATE NEXT STEP (The "One Thing")

**Complete Phase 3 Closure:**

1. Enter Phase 4 (Planning Stage).

---

## 🟧 Active Workstreams (WIP)

| Status | Workstream | Owner | Deliverable |
|--------|------------|-------|-------------|
| **CLOSED** | **Trusted Builder Mode v1.1** | Antigravity | `Council_Ruling_Trusted_Builder_Mode_v1.1.md` (RATIFIED) |
| **CLOSED** | **Policy Engine Authoritative Gating** | Antigravity | `Closure_Record_Policy_Engine_FixPass_v1.0.md` |

| **CLOSED** | **CSO Role Constitution** | Antigravity | `CSO_Role_Constitution_v1.0.md` (Finalized) |
| **WAITING** | OpenCode Deletion Logic | Council | Review Ruling |

---

## 🟦 Roadmap Context

- **Phase 1 (Foundation):** DONE
- **Phase 2 (Governance):** DONE
- **Phase 3 (Optimization):** **RATIFIED (APPROVE_WITH_CONDITIONS)** — Council Ruling Phase3 Closure v1.0
  - **Condition C1:** CSO Role Constitution v1.0 (RESOLVED 2026-01-23)
  - **Condition C2:** F3/F4/F7 evidence deferred (RESOLVED 2026-01-27) — Review packets: `artifacts/review_packets/Review_Packet_F3_Tier2.5_Activation_v1.0.md`, `artifacts/review_packets/Review_Packet_F4_Tier2.5_Deactivation_v1.0.md`, `artifacts/review_packets/Review_Packet_F7_Runtime_Antigrav_Protocol_v1.0.md`
- **Phase 4 (Autonomous Construction):** NEXT
  - **P0 Pre-req:** Trusted Builder Mode v1.1 (RATIFIED 2026-01-26)

---

## ⚠️ System Blockers (Top 3)

1. **Recursive Builder Integration** (P1) — **CLOSED** (Hardened v0.4 Bundle)

---

## 🟩 Recent Wins

- **2026-01-26:** Trusted Builder Mode v1.1 Ratified (Council Ruling).
- **2026-01-23:** Policy Engine Authoritative Gating — FixPass v1.0 (Council PASS).
- **2026-01-18:** Raw Capture Primitive Standardized (Evidence Capture v0.1).
- **2026-01-17:** Git Workflow v1.1 Accepted (Fail-Closed, Evidence-True).
- **2026-01-16:** Phase 3 technical deliverables complete (Council ratification pending).
```

---

## 2. Task B1: Strengthen smoke_check Failure-Path Evidence Assertions

**Target File:** `runtime/tests/test_build_with_validation_mission.py`

```python
import pytest
import itertools
import json
import hashlib
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
from runtime.orchestration.missions.build_with_validation import BuildWithValidationMission
from runtime.orchestration.missions.base import MissionContext, MissionValidationError, MissionType # Added MissionType for P0.2

def test_mission_context_semantics(tmp_path):
    """
    P0.1: Semantic regression test for MissionContext.
    Asserts that repo_root is a valid directory with pyproject.toml,
    and baseline_commit is a valid commit-ish string (not a path).
    """
    # 1. Setup valid context
    repo = tmp_path / "valid_repo"
    repo.mkdir()
    (repo / "pyproject.toml").touch()
    
    valid_ctx = MissionContext(
        repo_root=repo,
        baseline_commit="a" * 40, # Valid SHA (40 chars)
        run_id="test_run",
        metadata={}
    )
    
    # Assert types
    assert isinstance(valid_ctx.repo_root, Path)
    assert isinstance(valid_ctx.baseline_commit, str)
    
    # Assert semantics
    assert valid_ctx.repo_root.exists()
    assert (valid_ctx.repo_root / "pyproject.toml").exists()
    
    # P0.2: Stricter Baseline Commit Checks
    assert os.sep not in valid_ctx.baseline_commit
    assert "/" not in valid_ctx.baseline_commit
    assert "\\" not in valid_ctx.baseline_commit
    assert ":" not in valid_ctx.baseline_commit  # Win drive letter
    assert valid_ctx.baseline_commit != str(valid_ctx.repo_root)

def test_mission_context_runtime_failures(tmp_path, mission):
    """
    P0.2: Test actual runtime behavior when MissionContext is invalid.
    Instead of asserting on artificial types, we assert the mission behaves robustly (fails closed).
    
    P0.1 Fix: No swallowed exceptions. We expect controlled failure (MissionResult(success=False) or MissionExecutionError).
    Since build_with_validation uses filesystem ops heavily, passing a file as repo_root leads to OSError during mkdir 
    or check_pyproject. The mission relies on OS calls.
    Ideally, we'd want MissionExecutionError, but purely from a "fail-closed" perspective, 
    an exception raising out IS fail-closed (engine catches it).
    However, the prompt asks to "Prefer (b) [raise controlled exception] only if engine is the fail-closed boundary."
    """
    # Case A: Repo root is valid path but not a directory
    non_dir_repo = tmp_path / "file_repo"
    non_dir_repo.touch()
    
    ctx_bad_repo = MissionContext(
        repo_root=non_dir_repo,
        baseline_commit=None,
        run_id="test_run",
        metadata={}
    )
    
    # Expect failure. Since evidence_dir creation does mkdir(parents=True), it will fail with NotADirectoryError (OSError)
    # The mission does not wrap this in try/except, so it raises.
    # We assert strict exception type compliance so we know exactly HOW it fails.
    with pytest.raises(OSError):
        mission.run(ctx_bad_repo, {"mode": "smoke"})

    # Case B: Repo root valid, but missing pyproject.toml -> SMOKE-1 fails
    empty_repo = tmp_path / "empty_repo"
    empty_repo.mkdir()
    
    ctx_empty = MissionContext(
        repo_root=empty_repo,
        baseline_commit=None,
        run_id="test_run",
        metadata={}
    )
    
    res_empty = mission.run(ctx_empty, {"mode": "smoke"})
    assert not res_empty.success
    assert res_empty.outputs["smoke"]["exit_code"] != 0
    
    # Refinement P1.1: Strengthen failure evidence assertions
    # Verify failure evidence exists on disk
    fail_evidence_path = Path(res_empty.outputs["evidence_dir"])
    assert fail_evidence_path.exists()
    assert (fail_evidence_path / "smoke_check.stdout").exists()
    assert (fail_evidence_path / "smoke_check.stderr").exists()
    assert (fail_evidence_path / "smoke_check.exitcode").exists()
    
    # Verify content match (empty stdout, non-empty stderr usually)
    # Just verify hashes match what's in outputs
    real_stdout = (fail_evidence_path / "smoke_check.stdout").read_bytes()
    real_stdout_sha = hashlib.sha256(real_stdout).hexdigest()
    assert res_empty.outputs["smoke"]["stdout_sha256"] == real_stdout_sha
    
    # Case C: Baseline commit is invalid format (Option A: Fail Closed)
    # Refinement P0.1: Enforce regex validation (Option A)
    
    ctx_invalid_commit = MissionContext(
        repo_root=empty_repo,
        baseline_commit="invalid-commit-format", # Not 7-40 hex chars
        run_id="test_run",
        metadata={}
    )
    # Should raise MissionValidationError now
    with pytest.raises(MissionValidationError) as excinfo:
        mission.run(ctx_invalid_commit, {"mode": "smoke"})
    assert "Invalid baseline_commit format" in str(excinfo.value)


def test_run_inputs_none(mission, context):
    """P0.1: Ensure inputs=None is handled deterministically."""
    # Mock subprocess
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"OK", stderr=b"")
        
        # 1. None inputs -> defaults
        res = mission.run(context, None)
        assert res.success
        assert res.outputs["run_token"] is not None
        
        # 2. Verify it matches empty dict inputs (determinism)
        # Clear evidence_dir to avoid collision rule failure
        import shutil
        shutil.rmtree(res.outputs["evidence_dir"])
        
        res_empty = mission.run(context, {})
        assert res.outputs["run_token"] == res_empty.outputs["run_token"]

def test_run_inputs_invalid_type(mission, context):
    """P0.1: Ensure inputs must be dict."""
    with pytest.raises(MissionValidationError):
        mission.run(context, "not-a-dict")


@pytest.fixture
def mission():
    return BuildWithValidationMission()

@pytest.fixture
def context(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").touch()
    return MissionContext(
        repo_root=repo,
        baseline_commit="a" * 40,
        run_id="test_run",
        metadata={}
    )

def test_mission_type(mission):
    assert mission.mission_type == MissionType.BUILD_WITH_VALIDATION

def test_validate_inputs_valid(mission):
    valid_inputs = {
        "mode": "smoke",
        "pytest_args": ["-v"],
        "pytest_targets": ["foo"]
    }
    # Should not raise
    mission.validate_inputs(valid_inputs)

def test_validate_inputs_invalid_key(mission):
    with pytest.raises(Exception):
        mission.validate_inputs({"invalid_key": "val"})

def test_validate_inputs_invalid_type(mission):
    with pytest.raises(Exception):
        mission.validate_inputs({"mode": 123})

def test_run_determinism(mission, context):
    """Test that run_token is deterministic based on params and commit. Uses real FS."""
    inputs = {"mode": "smoke"}
    
    # Mock subprocess only
    mock_res = MagicMock(returncode=0, stdout=b"OK", stderr=b"")
    
    with patch("subprocess.run", return_value=mock_res):
        
        res1 = mission.run(context, inputs)
        assert res1.success, f"Run 1 failed: {res1.error}"
        
        # Clear evidence_dir to avoid collision rule failure
        import shutil
        shutil.rmtree(res1.outputs["evidence_dir"])
        
        res2 = mission.run(context, inputs)
        assert res2.success, f"Run 2 failed: {res2.error}"
        
        assert res1.outputs["run_token"] == res2.outputs["run_token"]
        assert res1.outputs["repo_root"] == str(context.repo_root)
        
        # Explicit defaults
        explicit_defaults = {
            "mode": "smoke",
            "pytest_args": ["-q"],
            "pytest_targets": [],
            "capture_root_rel": "artifacts/evidence/mission_runs"
        }
        # Clear again
        shutil.rmtree(res2.outputs["evidence_dir"])
        res3 = mission.run(context, explicit_defaults)
        assert res3.success
        assert res1.outputs["run_token"] == res3.outputs["run_token"]

def test_run_evidence_capture(mission, context):
    """Test evidence files are written and hashes computed. Uses real FS."""
    inputs = {"mode": "smoke"}
    
    def mock_run_with_files(*args, **kwargs):
        stdout_file = kwargs.get("stdout")
        stderr_file = kwargs.get("stderr")
        if stdout_file:
            stdout_file.write(b"OUT")
        if stderr_file:
            stderr_file.write(b"ERR")
        return MagicMock(returncode=0)
    
    with patch("subprocess.run", side_effect=mock_run_with_files):
        
        res = mission.run(context, inputs)
        
        assert res.success
        assert res.outputs["smoke"]["exit_code"] == 0
        # Corrected: we used b"OUT" and b"ERR" in the mock writer
        assert res.outputs["smoke"]["stdout_sha256"] == hashlib.sha256(b"OUT").hexdigest()
        assert res.outputs["smoke"]["stderr_sha256"] == hashlib.sha256(b"ERR").hexdigest()
        
        # P1.2: Compute sha256 from evidence files on disk and assert equality
        evidence_path = Path(res.outputs["evidence_dir"])
        assert evidence_path.exists()
        
        real_stdout = (evidence_path / "smoke_compile.stdout").read_bytes()
        real_stderr = (evidence_path / "smoke_compile.stderr").read_bytes()
        
        assert real_stdout == b"OUT"
        assert real_stderr == b"ERR"

        real_stdout_sha = hashlib.sha256(real_stdout).hexdigest()
        real_stderr_sha = hashlib.sha256(real_stderr).hexdigest()

        assert res.outputs["smoke"]["stdout_sha256"] == real_stdout_sha
        assert res.outputs["smoke"]["stderr_sha256"] == real_stderr_sha

        # P0.2: Assert Evidence Equality (Canonical vs Output Mirror)
        assert res.evidence is not None
        assert res.evidence == res.outputs["evidence"]

def test_run_full_mode_trigger(mission, context):
    """Test full mode triggers pytest."""
    inputs = {"mode": "full", "pytest_targets": ["tests/"]}
    
    mock_sub_res = MagicMock(returncode=0, stdout=b"", stderr=b"")
    
    with patch("subprocess.run", return_value=mock_sub_res):
         
        res = mission.run(context, inputs)
        assert res.success
        
        assert "full:pytest" in res.executed_steps
        assert res.outputs["pytest"] is not None

def test_run_failure_propagation(mission, context):
    """Test failure in smoke stops execution."""
    inputs = {"mode": "full", "pytest_targets": ["tests/"]}
    
    # Smoke fails
    mock_sub_res = MagicMock(returncode=1, stdout=b"", stderr=b"FAIL")
    
    with patch("subprocess.run", return_value=mock_sub_res):
        
        res = mission.run(context, inputs)
        
        assert not res.success
        assert "full:pytest" not in res.executed_steps
        assert res.outputs["smoke"]["exit_code"] == 1



def test_full_mode_fail_closed_audit(mission, context):
    """
    P0.4 & P1.1: Fail closed if no targets provided in full mode (no defaults).
    Returns audit-grade receipt with partial outputs.
    """
    inputs = {"mode": "full", "pytest_targets": []}
    
    # Smoke passes
    mock_sub_res = MagicMock(returncode=0, stdout=b"", stderr=b"")
    
    with patch("subprocess.run", return_value=mock_sub_res): 
        # No Path mock needed if we don't hit the default branch
         
        res = mission.run(context, inputs)
        
        assert not res.success
        assert "Full mode requires explicit pytest_targets" in res.error
        assert "no defaults allowed" in res.error
        
        # P1.1: Audit receipt
        assert res.outputs is not None
        assert res.outputs["smoke"] is not None
        assert res.evidence is not None
        assert res.evidence == res.outputs["evidence"]
```

---

## 3. Task B2: Tighten Validation Exception Specificity

**Target File:** `runtime/tests/test_mission_registry/test_mission_registry_v0_2.py`
*Relevant excerpt typically around line 226:*

```python
    def test_rejects_invalid_metadata_type(self):
        """Non-string metadata value raises error."""
        # Metadata values must be strings for deterministic JSON serialization
        req = MissionSynthesisRequest(
            id="valid-id",
            name="Valid Name",
            metadata={"key": 123},  # Not a string
        )
        with pytest.raises((MissionBoundaryViolation, TypeError, ValueError)):
            synthesize_mission(req)
```

**Target File:** `runtime/tests/test_budget_txn.py`
*Relevant excerpt typically around line 63-71:*

```python
    def charge_worker(cost):
        try:
            with sqlite3.connect(db_path, timeout=10.0) as c:
                c.execute("PRAGMA busy_timeout = 10000")
                try_charge_budget(c, "m1", None, cost, False)
        except sqlite3.OperationalError:
            pass
        except Exception:
            pass
```

**Target File:** `runtime/tests/test_tier2_orchestrator.py`
*Relevant excerpt typically around line 280-285:*

```python
        try:
            from runtime.orchestration.missions import get_mission_class
            get_mission_class("echo")
            mission_available = True
        except:
            pass
```

---

## 4. Task B3: Standardize Fail-Closed Filesystem Error Boundaries

**Target File:** `runtime/state_store.py`

```python
import json
import os
import hashlib
from typing import Dict, Any

class StateStore:
    def __init__(self, storage_path: str = "persistence"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def write_state(self, key: str, state: Dict[str, Any]):
        path = os.path.join(self.storage_path, f"{key}.json")
        with open(path, "w") as f:
            json.dump(state, f, sort_keys=True)

    def read_state(self, key: str) -> Dict[str, Any]:
        path = os.path.join(self.storage_path, f"{key}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"State key {key} not found")
        with open(path, "r") as f:
            return json.load(f)

    def create_snapshot(self, key: str) -> str:
        # returns hash of state
        state = self.read_state(key)
        serialized = json.dumps(state, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()
```

**Target File:** `runtime/tools/filesystem.py`
*Referencing module docstrings / error handling patterns. See repo file for full content.*

**Target File:** `runtime/orchestration/run_controller.py`
*Referencing module docstrings / error handling patterns. See repo file for full content.*

**Target File:** `runtime/orchestration/loop/ledger.py`
*Referencing module docstrings / error handling patterns. See repo file for full content.*
