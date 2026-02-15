# Implementation Plan — Build Loop v0.3 Phase 2 (Execution-Grade)

**Version**: 1.0
**Date**: 2026-01-08
**Scope**: Phase 2 (Operations + Run Controller). No structural operations.
**Status**: Execution-grade — all schemas and contracts defined.

> [!IMPORTANT]
> Governance baseline exists from Phase 1. No baseline update required for Phase 2.
> Phase 2 adds new code modules but no new governance surfaces.

---

## Appendix A: Canonical Schemas

### A.1 ExecutionContext
```python
@dataclass
class ExecutionContext:
    run_id: str                    # Deterministic run ID (sha256:...)
    run_id_audit: str              # UUID for audit only
    mission_id: str
    mission_type: str
    step_id: str
    repo_root: Path
    baseline_commit: str
    envelope: Envelope
    journal: Optional[MissionJournal]
```

### A.2 Operation
```python
@dataclass
class Operation:
    operation_id: str
    type: str  # llm_call, tool_invoke, packet_route, gate_check
    params: dict
    compensation_type: CompensationType
    compensation_command: str
```

### A.3 OperationReceipt (per spec §5.2)
```python
@dataclass
class OperationReceipt:
    operation_id: str
    timestamp: str
    pre_state_hash: str
    post_state_hash: str
    compensation_type: CompensationType
    compensation_command: str
    idempotency_key: str
    compensation_verified: bool
```

### A.4 CompensationType (per spec §5.2)
```python
class CompensationType(Enum):
    NONE = "none"
    GIT_CHECKOUT = "git_checkout"
    GIT_RESET_HEAD = "git_reset_head"
    GIT_RESET_SOFT = "git_reset_soft"
    GIT_RESET_HARD = "git_reset_hard"
    GIT_CLEAN = "git_clean"
    FILESYSTEM_DELETE = "fs_delete"
    FILESYSTEM_RESTORE = "fs_restore"
    CUSTOM_VALIDATED = "custom"
```

### A.5 ValidationResult (per spec §5.2.1)
```python
@dataclass
class ValidationResult:
    allowed: bool
    reason: str
    evidence: dict
```

### A.6 Envelope (per spec §5.2.1)
```python
@dataclass
class Envelope:
    allowed_paths: List[str]
    denied_paths: List[str]
    allowed_tools: List[str]
    allowed_roles: List[str]
    reject_symlinks: bool
    max_budget_usd: float
    timeout_seconds: int
```

### A.7 StepRecord
```python
@dataclass
class StepRecord:
    step_id: str
    operation_type: str
    status: str
    started_at: str
    completed_at: Optional[str]
    pre_state_hash: str
    post_state_hash: Optional[str]
    error_message: Optional[str]
    compensation_status: str
    prev_entry_hash: str
    entry_hash: str
```

---

## Appendix B: Canonical Serialization

- **SHA-256**: Hex-encoded, prefixed `sha256:`
- **Canonical JSON**: `json.dumps(obj, separators=(",",":"), sort_keys=True, ensure_ascii=False, allow_nan=False)`
- **Paths**: Forward slashes, relative to repo root

---

## Implementation Files

| File | Description |
|------|-------------|
| `runtime/orchestration/operations.py` | OperationExecutor, receipts, state hashing |
| `runtime/orchestration/mission_journal.py` | Hash-chained journal, integrity verification |
| `runtime/governance/envelope_enforcer.py` | Path containment, symlink rejection |
| `runtime/governance/self_mod_protection.py` | Protected paths per §2.4 |

## Tests

| File | Coverage |
|------|----------|
| `runtime/tests/test_operations.py` | Compensation, state hash, executor |
| `runtime/tests/test_mission_journal.py` | Hash chain, integrity, export |
| `runtime/tests/test_envelope_enforcer.py` | Traversal, symlink, deny/allow |
| `runtime/tests/test_self_mod_protection.py` | Protected paths, role checks |

---

## Verification

```bash
pytest runtime/tests/test_operations.py runtime/tests/test_mission_journal.py runtime/tests/test_envelope_enforcer.py runtime/tests/test_self_mod_protection.py -v
```

**Result**: 56 passed, 2 skipped (symlink tests on Windows)
