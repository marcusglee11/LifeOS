# Sprint Acceptance Validator Checklist: Sprint S1 Phase B

**Version:** 1.0
**Status:** Active
**Sprint:** S1 Phase B (Refinement)

---

## 1. Cleanliness & Scope

### D1: Identity & Cleanliness (Preflight)

Run in repo root (BEFORE applying Phase B changes, or after stashing):

```bash
git rev-parse HEAD
git status --porcelain=v1
git diff --name-only
```

**Pass Criteria:**

- `git status` output is EMPTY (or contains only ignored/untracked files explictly allowed by policy).
- `git diff` output is EMPTY.

### D3: Scope Containment (Pending Commit)

Run:

```bash
git diff --name-only <BASELINE_COMMIT> HEAD
```

*(Baseline Commit: `1c7a772863da67372497b634452c97d8c0ce59c5`)*

**Intended Files (Allowlist):**

```text
docs/02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md
docs/INDEX.md
runtime/orchestration/loop/ledger.py
runtime/orchestration/missions/build_with_validation.py
runtime/orchestration/missions/schemas/build_with_validation_result_v0_1.json
runtime/orchestration/run_controller.py
runtime/state_store.py
runtime/tests/test_budget_txn.py
runtime/tests/test_build_with_validation_mission.py
runtime/tests/test_mission_registry/test_mission_registry_v0_2.py
runtime/tests/test_tier2_orchestrator.py
runtime/tools/filesystem.py
artifacts/Implementation_Report_Sprint_S1_Phase_B_v1.0.md
artifacts/Sprint_Acceptance_Validator_Checklist_S1_Phase_B.md
artifacts/review_packets/Review_Packet_Sprint_S1_Phase_B_v1.0.md
```

**Pass Criteria:**

- Output of `git diff` must be exactly the set above (or a subset).
- **CRITICAL:** `artifacts/logs_verbatim.txt` MUST NOT be present.
- Any extra files = **BLOCKED**.

---

## 2. Test Truth

### D2: Baseline Comparison

**Baseline State:** 22 Failures (Known Pre-existing)
See `Implementation_Report_Sprint_S1_Phase_B_v1.0.md` for exact list.

### D3: Current Test State

Run:

```bash
pytest runtime/tests -q
```

**Pass Criteria:**

- Total Passed >= 980
- Total Failed <= 22
- **NO NEW FAILURES:** Every failing nodeid in Current output MUST appear in Baseline failure list.
- If Total Failed > 22 -> **BLOCKED**.
- If New Failure Nodeid -> **BLOCKED**.

---

## 3. Targeted Verification

### B1: Evidence Integrity

Run:

```bash
pytest runtime/tests/test_build_with_validation_mission.py::test_mission_context_runtime_failures -v
```

**Pass Criteria:**

- Result: `PASSED`
- Log verifies assertions for `stderr_sha256` and `exitcode_sha256`.

### B2: Exception Specificity

Run:

```bash
pytest runtime/tests/test_mission_registry/test_mission_registry_v0_2.py -v -k "invalid_metadata_type"
pytest runtime/tests/test_budget_txn.py -v
pytest runtime/tests/test_tier2_orchestrator.py -v
```

**Pass Criteria:**

- All `PASSED`.

### B3: Filesystem Boundaries

Run:

```bash
pytest runtime/tests/test_state_store.py -v
```

**Pass Criteria:**

- All `PASSED`.

---

## 4. Documentation Lifecycle

### E5: Doc Labels

Check `docs/02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md`:

- Status should be `Draft` or `Proposed` (Not `Ratified` without council).
- Verify `docs/INDEX.md` contains entry for this protocol.

**Pass Criteria:**

- Status correct.
- Index updated.

---

## 5. Final Verdict

- **ACCEPT:** All criteria met.
- **GO-WITH-FIXES:** Minor doc-only misses.
- **BLOCKED:** Scope violation or new test failure.
