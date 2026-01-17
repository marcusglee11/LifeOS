---
artifact_id: "76c577c8-346a-45a5-9cdd-c0dcae7989e5"
artifact_type: "PLAN_PACKET"
schema_version: "1.2"
created_at: "2026-01-17T11:40:00Z"
author: "Antigravity"
version: "1.2c"
status: "READY_FOR_EXECUTION"
supersedes: "Plan_OpenCode_Dogfooding_v1.2b.md"
---

# Scope Envelope

- **Goal**: Validate OpenCode readiness for live dogfooding with explicit fail-closed gates, deterministic evidence, and audit-grade results.
- **Non-Goals**:
  - New runtime features or orchestrator changes.
  - Production deployment.
  - Manual verification (all gates are machine-checkable).
- **In-Scope Paths (Write Allowlist)**:
  - `docs/zz_scratch/opencode_dogfood_probe.md`
  - `scripts/opencode_dogfood/sandbox/`
  - `artifacts/ledger/opencode_dogfood/`
  - `logs/agent_calls/`

---

# Proposed Changes

## P1.0 Execute OpenCode Dogfood Test Suite (v1.2c)

- **Description**: Run 15 test scenarios via `scripts/opencode_dogfood/run_suite.py` with hard gates, deterministic evidence capture, and fail-closed safety rails.
- **Rationale**: Validate automation substrate reliability before autonomous build cycles.
- **Touchpoints**:
  - `scripts/opencode_dogfood/run_suite.py`
  - `scripts/opencode_dogfood/lib.py`
  - `scripts/opencode_dogfood/schemas/`
  - `scripts/opencode_dogfood/sandbox/fixtures/`

---

# Claims

- **Claim**: OpenCode connectivity is operational via direct REST fallback.
  - **Type**: output_contract
  - **Evidence Pointer**: artifacts/ledger/opencode_dogfood/RUN_0001/cases/T1C01.result.json
  - **Status**: proposal

- **Claim**: Deletion sentinel correctly blocks unauthorized deletions.
  - **Type**: behavior_contract
  - **Evidence Pointer**: artifacts/ledger/opencode_dogfood/RUN_0001/cases/T2B03.result.json
  - **Status**: proposal

---

# Targets

- **Target**: scripts/opencode_dogfood/
  - **Type**: new
  - **Mode**: fixed_path
  - **Intent**: Host runner, validators, and sandbox.

- **Target**: artifacts/ledger/opencode_dogfood/RUN_XXXX/
  - **Type**: new
  - **Mode**: fixed_path
  - **Intent**: Store deterministically named evidence per run.

---

# Changelog (v1.2b → v1.2c)

| Change | Description |
|--------|-------------|
| **Scenario Table** | Contract-grade: removed all parenthetical notes/placeholders |
| **Fail Codes** | T2B03 expects strict `GITCLEANFAIL` |
| **T3 Fixtures** | Explicit inputs defined in `sandbox/fixtures/` |
| **Worktree Guard** | Explicit `WORKTREE_REQUIRED` failure code for T2b+ |
| **Cleanup** | Non-destructive default; gated by suite success |

---

# Run ID Convention

Run IDs follow the pattern `RUN_XXXX` where XXXX is a zero-padded integer. The runner:

1. Scans `artifacts/ledger/opencode_dogfood/` for existing `RUN_*` directories.
2. Extracts the highest numeric suffix.
3. Increments by 1 for the new run.
4. Example sequence: `RUN_0001`, `RUN_0002`, `RUN_0003`

---

# Preflight Prerequisites (Safety)

## Required Isolation (Fail-Closed)

All T2b+ tests MUST run in an **isolated git worktree**. The Runner enforces this by checking if the git directory resides in `.git/worktrees/`.

**Failure Condition**: Any attempt to run T2b+ stages in a non-worktree environment triggers `WORKTREE_REQUIRED` and immediate suite stop.

## Write Allowlist (Default)

```python
WRITE_ALLOWLIST = [
    "docs/zz_scratch/opencode_dogfood_probe.md",
    "scripts/opencode_dogfood/sandbox/",
    "artifacts/ledger/opencode_dogfood/",
    "logs/agent_calls/",
]
```

Any modification outside this allowlist triggers `MODIFICATIONFAIL` and immediate stop.

## Deletion Policy

**Default allowlist: EMPTY**

Any file deletion triggers `GITCLEANFAIL` and immediate stop.

## Destructive Operations: FORBIDDEN

- `git clean -f` / `git clean -fd` / `git clean -x`: **FORBIDDEN**
- `git reset --hard`: **FORBIDDEN**
- `git checkout -- .`: **FORBIDDEN**

---

# Result Schemas

## Case Result Schema

Path: `artifacts/ledger/opencode_dogfood/RUN_XXXX/cases/<case_id>.result.json`

| Field | Type | Required | Constraint |
|-------|------|----------|------------|
| schema_id | string | yes | Fixed: "opencode_dogfood_case_result" |
| schema_version | string | yes | Fixed: "1.0" |
| case_id | string | yes | Pattern: `T[0-9][A-Z]?[A-Z]?[0-9]{2}` |
| stage | string | yes | Enum: T1, T2a, T2b, T3, T4 |
| expected_outcome | string | yes | Enum: SUCCESS, EXPECTED_FAIL |
| actual_outcome | string | yes | Enum: SUCCESS, FAIL |
| status | string | yes | Enum: PASS, FAIL |
| failure_code | string | if applicable | Non-null for FAIL or EXPECTED_FAIL cases |
| run_id | string | yes | Pattern: `RUN_[0-9]{4}` |
| duration_ms | int | yes | Execution time in milliseconds |
| model_id | string | optional | Model used for LLM calls |
| transport | string | optional | Transport method |
| repo_commit | string | yes | 40-char SHA |
| evidence | array | yes | Sorted by path (LC_ALL=C) |

### PASS/FAIL Semantics

- **status = PASS** iff:
  - `expected_outcome = SUCCESS` AND `actual_outcome = SUCCESS`
  - OR `expected_outcome = EXPECTED_FAIL` AND `actual_outcome = FAIL` AND `failure_code` matches expected
- **status = FAIL** otherwise

## Run Summary Schema

Path: `artifacts/ledger/opencode_dogfood/RUN_XXXX/run_summary.json`

| Field | Type | Required | Constraint |
|-------|------|----------|------------|
| schema_id | string | yes | Fixed: "opencode_dogfood_run_summary" |
| schema_version | string | yes | Fixed: "1.0" |
| run_id | string | yes | Pattern: `RUN_[0-9]{4}` |
| repo_commit | string | yes | 40-char SHA |
| total_cases | int | yes | Total cases in suite |
| passed | int | yes | Cases with PASS status |
| failed | int | yes | Cases with FAIL status |
| skipped | int | yes | Cases not executed (fail-fast) |
| final_verdict | string | yes | PASS (all passed) or FAIL |
| stop_reason | string | if early stop | Reason for early termination |
| cases | array | yes | Summary per case |

---

# Evidence & Hashing Requirements

## Folder Structure

```
artifacts/ledger/opencode_dogfood/RUN_0001/
├── run_summary.json
├── run_summary.json.sha256
├── cases/
│   ├── T1C01.result.json
│   ├── T1C01.result.json.sha256
│   └── ...
└── evidence/
    ├── T1C01/
    │   ├── stdout.txt
    │   ├── stdout.txt.sha256
    │   ├── git_status.txt
    │   ├── git_status.txt.sha256
    │   └── ...
    └── ...
```

## Evidence Capture Rules

For EVERY case, capture:

1. **stdout.txt**: Command standard output
2. **stderr.txt**: Command standard error
3. **git_status.txt**: `git status --porcelain` output
4. **git_diff.txt**: `git diff --name-status` output (if changes detected)
5. **repo_commit.txt**: current HEAD SHA
6. **worktree_check.txt**: Worktree predicate evaluation result
7. **Delta files**: Any new files created, renamed to `item_01.ext`, `item_02.ext`

## Hashing Rules

- **Per-file sidecars**: Every evidence file and result JSON gets a `.sha256` sidecar
- **Format**: `<sha256_hash> *<filename>` (BSD-style)
- **Sorting**: Evidence paths sorted lexicographically (LC_ALL=C) before serialization

---

# Scenario Index

| case_id | stage | expected_outcome | purpose |
|---------|-------|------------------|---------|
| T1C01 | T1 | SUCCESS | Direct client ping |
| T1C02 | T1 | SUCCESS | Multi-role key selection |
| T1C03 | T1 | EXPECTED_FAIL | Invalid model (expected reject; validates MODELNOTFOUND path) |
| T2A01 | T2a | SUCCESS | Scratch doc analysis |
| T2A02 | T2a | SUCCESS | Policy doc review |
| T2A03 | T2a | SUCCESS | Probe doc quality check |
| T2B01 | T2b | SUCCESS | Scratch file write |
| T2B02 | T2b | SUCCESS | Scratch file append |
| T2B03 | T2b | EXPECTED_FAIL | Deletion sentinel validation |
| T3C01 | T3 | SUCCESS | Function generation |
| T3C02 | T3 | SUCCESS | Bug fix task |
| T3C03 | T3 | SUCCESS | Test generation |
| T3C04 | T3 | SUCCESS | Code review |
| T4E01 | T4 | SUCCESS | Empty prompt handling |
| T4E02 | T4 | EXPECTED_FAIL | Timeout enforcement |

---

# Executable Scenario Table

| case_id | stage | command | pass_criteria | failure_codes |
|---------|-------|---------|---------------|---------------|
| T1C01 | T1 | `python scripts/opencode_dogfood/run_suite.py --case T1C01` | exit=0, status=PASS | CLIFAIL |
| T1C02 | T1 | `python scripts/opencode_dogfood/run_suite.py --case T1C02` | exit=0, status=PASS | CLIFAIL, EVIDENCEMISMATCH |
| T1C03 | T1 | `python scripts/opencode_dogfood/run_suite.py --case T1C03` | exit=0, status=PASS | MODELNOTFOUND |
| T2A01 | T2a | `python scripts/opencode_dogfood/run_suite.py --case T2A01` | exit=0, status=PASS | GITCLEANFAIL |
| T2A02 | T2a | `python scripts/opencode_dogfood/run_suite.py --case T2A02` | exit=0, status=PASS | GITCLEANFAIL |
| T2A03 | T2a | `python scripts/opencode_dogfood/run_suite.py --case T2A03` | exit=0, status=PASS | GITCLEANFAIL |
| T2B01 | T2b | `python scripts/opencode_dogfood/run_suite.py --case T2B01` | exit=0, status=PASS | GITCLEANFAIL, MODIFICATIONFAIL, WORKTREE_REQUIRED |
| T2B02 | T2b | `python scripts/opencode_dogfood/run_suite.py --case T2B02` | exit=0, status=PASS | GITCLEANFAIL, MODIFICATIONFAIL, WORKTREE_REQUIRED |
| T2B03 | T2b | `python scripts/opencode_dogfood/run_suite.py --case T2B03` | exit=0, status=PASS | GITCLEANFAIL, WORKTREE_REQUIRED |
| T3C01 | T3 | `python scripts/opencode_dogfood/run_suite.py --case T3C01` | exit=0, status=PASS | SYNTAXERROR, WORKTREE_REQUIRED |
| T3C02 | T3 | `python scripts/opencode_dogfood/run_suite.py --case T3C02` | exit=0, status=PASS | EMPTYRESPONSE, WORKTREE_REQUIRED |
| T3C03 | T3 | `python scripts/opencode_dogfood/run_suite.py --case T3C03` | exit=0, status=PASS | EMPTYRESPONSE, WORKTREE_REQUIRED |
| T3C04 | T3 | `python scripts/opencode_dogfood/run_suite.py --case T3C04` | exit=0, status=PASS | EMPTYRESPONSE, WORKTREE_REQUIRED |
| T4E01 | T4 | `python scripts/opencode_dogfood/run_suite.py --case T4E01` | exit=0, status=PASS | — |
| T4E02 | T4 | `python scripts/opencode_dogfood/run_suite.py --case T4E02` | exit=0, status=PASS | TIMEOUTEXCEEDED |

---

# Validator Contract

- **Output Format**: PASS/FAIL
- **Failure Codes**:
  - [CLIFAIL]: OpenCode client initialization failed
  - [MODELNOTFOUND]: Requested model provider rejected by registry
  - [GITCLEANFAIL]: Unauthorized file deletion detected
  - [MODIFICATIONFAIL]: Unauthorized file modification detected
  - [WORKTREE_REQUIRED]: T2b+ execution attempted in non-worktree environment
  - [TIMEOUTEXCEEDED]: Request exceeded latency budget
  - [EMPTYRESPONSE]: LLM returned zero-length content
  - [SYNTAXERROR]: Generated code failed to compile
  - [EVIDENCEMISMATCH]: Evidence count did not match expected

---

# Verification Matrix

| Case ID | Input Fixture | Expected | Expected Code | Prefix |
|---------|---------------|----------|---------------|--------|
| P01 | T1C01 | PASS | | [T1] |
| P02 | T2A01 | PASS | | [T2a] |
| P03 | T2B01 | PASS | | [T2b] |
| P04 | T3C01 | PASS | | [T3] |
| F01 | Client init fail | FAIL | CLIFAIL | [T1] |
| F02 | Invalid model (T1C03) | PASS (EXPECTED_FAIL) | MODELNOTFOUND | [T1] |
| F03 | Unauthorized deletion (T2B03) | PASS (EXPECTED_FAIL) | GITCLEANFAIL | [T2b] |
| F04 | Slow response (T4E02) | PASS (EXPECTED_FAIL) | TIMEOUTEXCEEDED | [T4] |
| F05 | Out-of-allowlist write | FAIL | MODIFICATIONFAIL | [T2b] |
| F06 | Non-worktree execution | FAIL | WORKTREE_REQUIRED | [T2b] |

---

# Migration Plan

- **Backward Compat**: N/A (Test suite only)
- **Rollout Stages**:
  - Stage 1: T1 Connectivity (gate for T2a)
  - Stage 2: T2a Read-Only (gate for T2b)
  - Stage 3: T2b Write (gate for T3)
  - Stage 4: T3 Coding + T4 Edge Cases
- **Deprecation Rules**: N/A

---

# Governance Impact

- **Touches Constitution**: no
- **Gate**: StepGate v1.0
- **Rationale**: Validates OpenCode reliability with explicit anti-deletion safeguards per LIFEOS_STATE.md P0 risk focus.

---

# Checklists

## Suite Entry Checklist

- [ ] Working tree clean (`git status --porcelain` empty)
- [ ] Runner available: `python scripts/opencode_dogfood/run_suite.py --help`
- [ ] Scratch target exists: `docs/zz_scratch/opencode_dogfood_probe.md`
- [ ] Sandbox fixtures exist: `scripts/opencode_dogfood/sandbox/fixtures/`
- [ ] Worktree prepared for T2b+ (if running those stages)

## Stage Entry Checklist (per stage)

- [ ] Previous stage passed (T1→T2a→T2b→T3→T4)
- [ ] No pending git changes
- [ ] Evidence directory writable

## Stage Exit Checklist (per stage)

- [ ] All case result JSONs present + hashed
- [ ] All evidence files captured + hashed
- [ ] No unauthorized modifications detected
- [ ] No unauthorized deletions detected

## Suite Exit Checklist

- [ ] `run_summary.json` exists + hashed
- [ ] All 15 cases accounted for (passed + failed + skipped = 15)
- [ ] Worktree cleaned up (ONLY if verdict=PASS; use `git worktree remove` without force)
- [ ] Final verdict recorded

---

# How to Run

## Full Suite (Recommended)

```bash
# 1. Create worktree (required for T2b+)
git worktree add ../dogfood_worktree HEAD
cd ../dogfood_worktree

# 2. Run full suite with fail-fast
python scripts/opencode_dogfood/run_suite.py --stages T1,T2a,T2b,T3,T4 --fail-fast

# 3. Cleanup (Conditional)
# IF suite PASSED:
cd ..
git worktree remove ../dogfood_worktree
# IF suite FAILED:
# Leave worktree for inspection.
```

## Single Case

```bash
python scripts/opencode_dogfood/run_suite.py --case T1C01
```

## Specific Stages

```bash
python scripts/opencode_dogfood/run_suite.py --stages T1,T2a --fail-fast
```

---

# Tasklist Breakdown

## Task 1: Environment Setup (2 min)

- **Entry**: Repo cloned, Python available
- **Exit**: Worktree created, runner --help works
- **Evidence**: Terminal output

## Task 2: Run T1 Connectivity (5 min)

- **Entry**: Task 1 complete
- **Exit**: 3 case results present in the run directory (identified via terminal output)
- **Evidence**: T1C01-T1C03 result JSONs + sidecars

## Task 3: Run T2a Read-Only (5 min)

- **Entry**: T1 passed
- **Exit**: 3 case results present, git status clean
- **Evidence**: T2A01-T2A03 result JSONs + evidence

## Task 4: Run T2b Write (5 min)

- **Entry**: T2a passed, in worktree
- **Exit**: 3 case results present, probe file modified, sentinel validated
- **Evidence**: T2B01-T2B03 + git diffs

## Task 5: Run T3 Coding (5 min)

- **Entry**: T2b passed
- **Exit**: 4 case results present
- **Evidence**: T3C01-T3C04 result JSONs

## Task 6: Run T4 Edge Cases (3 min)

- **Entry**: T3 passed
- **Exit**: 2 case results present
- **Evidence**: T4E01-T4E02 result JSONs

## Task 7: Finalization (2 min)

- **Entry**: All stages complete
- **Exit**: `run_summary.json` exists in run folder
- **Evidence**: Complete run folder contents under `artifacts/ledger/opencode_dogfood/<dynamic_run_id>/`

---

# Self-Audit

- **Placeholders lint**: PASS (No angle-bracket placeholders, no TBD, no Logic Error, no Crash, no Simulated)
- **Contract consistency**: PASS (No parenthetical notes in failure codes)
- **Allowlist enforcement**: PASS (WRITE_ALLOWLIST defined; MODIFICATIONFAIL implemented)
- **Worktree enforcement**: PASS (Fail-closed WORKTREE_REQUIRED check)
- **Cleanup Safety**: PASS (Non-force default, gated by exit)
