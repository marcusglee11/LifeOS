# Implementation Plan — Build Loop v0.3 Phase 1a Scaffold

**Scope**: Phase 1a scaffold-only. No structural operations (no rename/move/delete).

> [!IMPORTANT]
> **Phase 2 prohibits structural ops; this plan complies.**
> If governance baseline is missing or mismatched => HALT (no autonomous operation proceeds).

---

## Proposed Changes

### Governance & Stewardship

#### [CREATE] docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md
Create canonical copy at runtime location. Content identical to existing docs-root file.

#### [MODIFY] docs/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md
Convert existing docs-root file to deprecation stub pointing to canonical path. **No deletion.**

#### [CREATE] docs/01_governance/Council_Ruling_Build_Loop_Architecture_v1.0.md
Record PASS (GO) verdict with full SHA256 hashes (no truncation).

#### [MODIFY] docs/INDEX.md
Add repo-relative entries for spec and ruling.

---

### Phase 1a Implementation

#### runtime/agents/api.py
- `canonical_json()` with `allow_nan=False` (fail-closed)
- `compute_run_id_deterministic()` per spec section 5.1.3
- `compute_call_id_deterministic()` per spec section 5.1.3

#### runtime/agents/logging.py
Canonical agent call logging per spec section 5.1.4:
- Hash chain with `HASH_CHAIN_GENESIS`
- Append-only log entries with `prev_log_hash`

#### runtime/agents/fixtures.py
Replay cache per spec section 5.1.2. `ReplayMissError` on cache miss in replay mode.

#### runtime/orchestration/run_controller.py
- `check_kill_switch()`, `mission_startup_sequence()` per spec section 5.6.1
- `acquire_run_lock()`, `release_run_lock()` per spec section 5.6.2
- `verify_repo_clean()` per spec section 5.6.3
- **Fail-closed**: git missing or non-zero returncode => `GitCommandError` and HALT

#### runtime/governance/baseline_checker.py
- `verify_governance_baseline()` per spec section 2.5
- Missing => `BaselineMissingError` (HALT)
- Mismatch => `BaselineMismatchError` with full SHA256 (HALT)

---

### Scripts

#### scripts/audit_gate_build_loop_phase1a.py
Deterministic audit gate with G1-G7 checks. Exit 0=PASS, 2=FAIL, 3=BLOCKED.

#### scripts/build_bundle_build_loop_phase1a.py
Bundler that runs audit gate as final step. Fail-closed delivery.

---

### Tests

#### runtime/tests/test_run_controller.py
Kill switch ordering, lock, repo clean, git fail-closed.

#### runtime/tests/test_agent_api.py
Deterministic IDs, hash chain, NaN/Infinity rejection.

#### runtime/tests/test_baseline_governance.py
Missing/mismatch => HALT, full hashes in error.

---

## Verification

```bash
python scripts/build_bundle_build_loop_phase1a.py
```
