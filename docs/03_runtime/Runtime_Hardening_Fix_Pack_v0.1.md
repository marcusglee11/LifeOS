# Runtime_Hardening_Fix_Pack_v0.1

**Title:** Runtime_Hardening_Fix_Pack_v0.1  
**Version:** v0.1  
**Author:** Runtime Architect (for Antigravity implementation)  
**Date:** 2025-12-09  
**Scope:** `runtime/`, `recursive_kernel/`, `config/`, `docs/INDEX.md`  
**Source Packet:** Review_Packet_Hardening_Pass_v0.1  

---

## A. Mission Context

This Fix Pack refines the initial Hardening Pass v0.1 for:

- Determinism (time, environment, filesystem)  
- Safety (clearer error semantics, safer paths)  
- Log quality (replayable, audit-friendly)  
- Future recursion extension  

It **must** be implemented by Antigravity under GEMINI v2.2 and reported in a new Review Packet:

> `Review_Packet_Hardening_Pass_v0.2`

All created or amended modules **must** be flattened in that packet automatically.

---

## B. Invariants & Non-Goals

### B.1 Invariants

These must remain true after implementation:

1. `RuntimeFSM` semantics and state graph are unchanged (no new states, no removed states).  
2. `recursive_kernel.runner` continues to:
   - Plan → Build → Verify → Gate → Log
   - Run end-to-end with `python -m recursive_kernel.runner` from repo root.
3. `docs/INDEX.md` remains deterministically generated from `docs/`.  
4. AUTO_MERGE behaviour remains:
   - Docs-only + within diff-size threshold + low-risk paths → eligible for AUTO_MERGE.
5. All tests must remain green (or be extended) under `pytest`.

### B.2 Non-Goals

This Fix Pack **does not**:

- Introduce real git/merge operations (AUTO_MERGE remains simulated / receipt-based).  
- Change the set of FSM states or transitions.  
- Implement new recursion domains beyond `docs` / `tests_doc`.  
- Replace the test harness or introduce new frameworks.

---

## C. Issue List (Hardening-Level, Not Bugs)

**FP-001 — FSM strict-mode & history validation**  
**FP-002 — FSM checkpoint path & signature integrity**  
**FP-003 — Runner repo-root handling & timestamp pinning**  
**FP-004 — Builder dependency on `cwd` & index scope**  
**FP-005 — Verifier command determinism & cwd**  
**FP-006 — Gate decision semantics in logs**  

---

## D. Fix Specifications

### FP-001 — FSM strict-mode & history validation

**Target files:** `runtime/engine.py`

**Required changes:**
1. Strict-mode captured at construction (optional `strict_mode` param)
2. Error semantics consistent with docstring (`_force_error` raises `GovernanceError`)
3. History validation on checkpoint load (`_validate_history()`)

**Acceptance criteria:**
- Tests for strict_mode=True/False behavior
- Tests for invalid history detection

---

### FP-002 — FSM checkpoint path & signature integrity

**Target files:** `runtime/engine.py`

**Required changes:**
1. Anchor checkpoints under `amu0_path/checkpoints/`
2. Single-read signature verification
3. Error on disallowed checkpoint state

**Acceptance criteria:**
- Checkpoints written to correct path
- Single-read verification
- Governance error on illegal state

---

### FP-003 — Runner repo-root handling & timestamp pinning

**Target files:** `recursive_kernel/runner.py`, `recursive_kernel/builder.py`

**Required changes:**
1. Derive repo root from module location (REPO_ROOT constant)
2. Inject repo_root into Builder
3. Pinned run timestamp for logging

**Acceptance criteria:**
- Works from any cwd
- Timestamp consistency in logs

---

### FP-004 — Builder dependency on `cwd` & index scope

**Target files:** `recursive_kernel/builder.py`

**Required changes:**
1. Make Builder repo-root explicit (constructor param)
2. Optional index scoping extension point

**Acceptance criteria:**
- No cwd dependence
- Backwards compatible output

---

### FP-005 — Verifier command determinism & cwd

**Target files:** `recursive_kernel/verifier.py`

**Required changes:**
1. Comment noting preferred default command
2. Optional cwd parameter (non-breaking)

**Acceptance criteria:**
- cwd parameter works
- Default behavior preserved

---

### FP-006 — Gate decision semantics in logs

**Target files:** `recursive_kernel/runner.py`

**Required changes:**
1. Add `effective_decision` field in logs
2. Keep `gate_decision` as-is

**Acceptance criteria:**
- Three effective_decision values tested

---

## E. Post-conditions

Once implemented, `Review_Packet_Hardening_Pass_v0.2` must guarantee all fixes applied and flattened.
