# Implementation Plan — Build Loop v0.3 Phase 2 (Execution-Grade)

## Goal Description

Finalize the Phase 2 deliverable: a self-validating bundle that can be extracted and validated via an audit gate + pytest. The outcome is a clean, portable Phase 2 workspace with deterministic manifests and an execution loop that proves integrity and correctness.

## Scope Boundaries

IN SCOPE:
- Phase 2 self-validating bundle packaging
- Audit gate for Phase 2 bundle validation
- Pytest suite for Phase 2 bundle
- Deterministic manifest generation and verification

OUT OF SCOPE:
- Repo structural operations (moves/renames/deletes)
- Governance baseline creation/update
- Scope expansion beyond Phase 2 validation + packaging

## Success Criteria

- Audit gate passes on the provided bundle
- Pytest passes (`python -m pytest -q`)
- Bundle includes required scripts/tests/docs for Phase 2
- Deterministic manifest verification is enforced
- Deliverable ZIP of extracted workspace is clean (no caches/byproducts)

---

## Architecture Summary

Phase 2 delivers a minimal runtime + validation harness:
- `runtime/` contains core modules for operations, journaling, and envelope enforcement.
- `scripts/audit_gate_build_loop_phase2.py` provides a machine-checkable validation gate.
- `runtime/tests/` provides the test suite for Phase 2.

The bundle is self-contained and designed to be extracted and validated without external repo context.

---

## Implementation Steps

### 1) Bundle Layout

Bundle must contain:
- `scripts/audit_gate_build_loop_phase2.py`
- `runtime/` package:
  - `runtime/__init__.py`
  - `runtime/orchestration/operations.py`
  - `runtime/orchestration/mission_journal.py`
  - `runtime/governance/envelope_enforcer.py`
  - `runtime/governance/self_mod_protection.py`
- `runtime/tests/`:
  - `test_operations.py`
  - `test_mission_journal.py`
  - `test_envelope_enforcer.py`
  - `test_self_mod_protection.py`
- `pytest.ini`
- `docs/03_runtime/Implementation_Plan_Build_Loop_Phase2_v1.1.md`
- `manifest.txt` (hashes for tracked files; may exclude itself)

### 2) Deterministic Manifest

- Generate `manifest.txt` with lines:
  - `<sha256>  <relative_path>`
- Paths must be forward-slash (`/`) even on Windows.
- Entries must be stable and sorted.

### 3) Audit Gate (Phase 2)

Audit gate responsibilities:
- Confirm ZIP portability and path hygiene:
  - no absolute paths
  - no backslashes
  - no traversal (`..`)
- Extract to a fresh workspace
- Verify manifest format and hashes for listed files
- Enforce Python import sanity
- Run pytest
- Fail-closed on any anomaly

### 4) Runtime Components

#### 4.1 ExecutionContext

The bundle uses a structured execution context to record and audit Phase 2 actions.

```python
@dataclass(frozen=True)
class ExecutionContext:
    repo_root: str
    baseline_commit: str
    run_id: str  # Deterministic run ID (sha256:...)
    run_id_audit: UUID
    started_at: str
```

#### 4.2 Envelope Enforcer

- Validates operation requests against an allowlist
- Enforces path containment and “no-modification” protections for restricted files

#### 4.3 MissionJournal

- Records a chain of steps with hash chaining
- Provides integrity evidence for execution progression

---

## Verification

Run the Phase 2 bundle validation loop exactly as:

```bash
python scripts/audit_gate_build_loop_phase2.py --zip artifacts/bundles/Bundle_Build_Loop_Phase2_v1.1.zip
python -m pytest -q
```

**Verification Evidence Rule (binding)**: Do not record numeric test counts in this plan. The authoritative outcome is the verbatim stdout/stderr captured in the Phase 2 PASS report and the raw logs produced by the validation run.

**Platform note**: On Windows, symlink-related tests may be skipped depending on privileges and platform markers; rely on the captured pytest output for the run.

**Journal hash semantics**: MissionJournal entry hashes include timestamps (started_at/completed_at) and therefore provide integrity evidence, not run-replay determinism.

---

## Packaging

- **Type**: Standalone self-validating bundle
- **Includes**: Audit gate script, minimal `__init__.py` files, pytest.ini
- **Validation**: `python scripts/audit_gate_build_loop_phase2.py --zip artifacts/bundles/Bundle_Build_Loop_Phase2_v1.1.zip`

---

## Appendices

### Appendix A — MissionJournal Data Model (excerpt)

```python
@dataclass(frozen=True)
class StepRecord:
    step_id: str
    name: str
    status: str
    started_at: str
    completed_at: Optional[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    prev_hash: Optional[str]
    entry_hash: str
```

**Canonical bytes**:
- JSON canonicalization: sorted keys, compact separators, allow_nan=False
- UTF-8 encoding
- SHA256 digest

### Appendix B — Envelope (excerpt)

```python
@dataclass(frozen=True)
class Envelope:
    allow_ops: List[str]
    allow_paths: List[str]
    deny_paths: List[str]
    max_budget_usd: float
```
