# COO Doc Management Manual v1.0

**Purpose:** Executable runbook for COO Runtime documentation maintenance operations.

**Scope:** This manual defines deterministic, testable procedures for doc stewardship operations that the COO Runtime can execute autonomously or as delegated tasks.

**Authority:** This is a **procedural manual**, not a governance document. Governance boundaries are defined in `docs/01_governance/` and enforced by validators.

**Last Updated:** 2026-02-14

---

## Table of Contents

1. [Tools Reference](#tools-reference)
2. [Standard Operations](#standard-operations)
3. [Governance Boundaries](#governance-boundaries)
4. [Validation Checklist](#validation-checklist)
5. [Failure Modes & Escalation](#failure-modes--escalation)

---

## Tools Reference

### Doc Steward CLI Tools

| Command | Purpose | Blocking Behavior | Source of Truth |
|---------|---------|-------------------|----------------|
| `doc_steward.cli admin-structure-check` | Validate docs/11_admin/ file/dir allowlist | Always blocking | `doc_steward/admin_structure_validator.py` |
| `doc_steward.cli admin-archive-link-ban-check` | Prevent links from active docs to archive | Always blocking | `doc_steward/admin_archive_link_ban_validator.py` |
| `doc_steward.cli freshness-check` | Check runtime status age + contradictions | Mode-gated (off/warn/block) | `doc_steward/freshness_validator.py` |
| `doc_steward.cli index-check` | Validate INDEX.md consistency | Always blocking | `doc_steward/index_checker.py` |
| `doc_steward.cli link-check` | Check for broken markdown links | Always blocking | `doc_steward/link_checker.py` |
| `doc_steward.cli dap-validate` | Validate DAP naming compliance | Always blocking | `doc_steward/dap_validator.py` |

**Freshness Mode Control:**
- Env var: `LIFEOS_DOC_FRESHNESS_MODE` ∈ {`off`, `warn`, `block`}
- Default: `off` (local/dev)
- CI: `warn` until 2026-02-26, then `block`

### Runtime Workflow Tools

| Tool | Purpose | Integration Point | Source of Truth |
|------|---------|-------------------|----------------|
| `workflow_pack.check_doc_stewardship()` | Orchestrate doc validation when docs change | Called by mission closures, git hooks | `runtime/tools/workflow_pack.py` |
| `workflow_pack.update_state_and_backlog()` | Auto-update LIFEOS_STATE.md and BACKLOG.md | Called during build closure | `runtime/tools/workflow_pack.py` |

### Legacy Scripts (Transitional)

| Script | Purpose | Status | Migration Path |
|--------|---------|--------|---------------|
| `scripts/claude_doc_stewardship_gate.py` | Claude-specific doc stewardship gate | Active (legacy) | Refactor to `coo gate run-all` (backlog item) |

---

## Standard Operations

### SO-1: Validate Admin Doc Structure

**When to use:** Before/after modifying any file in `docs/11_admin/`

**Preconditions:**
- Repository is on a valid branch (not detached HEAD)
- No uncommitted changes that would conflict with validation

**Command:**
```bash
python3 -m doc_steward.cli admin-structure-check .
```

**Expected Output (success):**
```
[PASSED] Admin structure check passed.
```

**Exit Code:** `0` = pass, `1` = fail

**Evidence:**
- STDOUT contains `[PASSED]` message
- Exit code 0

**Failure Modes:**
1. **Missing required file** (e.g., `DECISIONS.md`)
   - **Symptom:** Error message: `Missing required file: docs/11_admin/DECISIONS.md`
   - **Action:** Create the missing file following the admin README template
   - **Escalation:** If file was deleted, check git history and restore from last known good state

2. **Unexpected file at root**
   - **Symptom:** Error message: `Unexpected file at root: docs/11_admin/<filename> (not in allowlist)`
   - **Action:** Either (a) move file to appropriate subdir, (b) archive file, or (c) update allowlist if legitimately needed
   - **Escalation:** If adding to allowlist, must create DECISIONS.md entry + update INDEX.md

3. **Invalid archive subdir name**
   - **Symptom:** Error message: `Invalid archive subdir name: docs/11_admin/archive/<name>/ (must match: YYYY-MM-DD_<topic>)`
   - **Action:** Rename archive subdir to match pattern `YYYY-MM-DD_<topic>`
   - **Escalation:** None (mechanical fix)

4. **Archive subdir missing README.md**
   - **Symptom:** Error message: `Missing README.md in archive subdir: docs/11_admin/archive/<name>/`
   - **Action:** Create archive README with disposition table (see archive template)
   - **Escalation:** If disposition unclear, halt and request human review

---

### SO-2: Validate Archive Link Hygiene

**When to use:** Before/after modifying any markdown file in `docs/`

**Preconditions:**
- Repository docs/ directory exists

**Command:**
```bash
python3 -m doc_steward.cli admin-archive-link-ban-check .
```

**Expected Output (success):**
```
[PASSED] Admin archive link ban check passed.
```

**Exit Code:** `0` = pass, `1` = fail

**Evidence:**
- STDOUT contains `[PASSED]` message
- Exit code 0

**Failure Modes:**
1. **Active doc links to archived file**
   - **Symptom:** Error message: `<file>:<position> links to archive: <url> (active docs must not link to archived files)`
   - **Action:** Remove or replace the link; if reference is needed, rephrase as text mention without hyperlink
   - **Escalation:** If link is essential, file must be un-archived (requires DECISIONS.md entry + restore from archive)

2. **Admin README links to individual archived file**
   - **Symptom:** Error in `docs/11_admin/README.md` linking to non-README archived file
   - **Action:** Change link to point only to the archive subdir README.md, not individual files
   - **Escalation:** None (mechanical fix)

---

### SO-3: Check Doc Freshness

**When to use:** During CI runs, before merges, or on-demand health checks

**Preconditions:**
- `artifacts/status/runtime_status.json` exists (generated by runtime)
- Freshness mode is set appropriately for context (off/warn/block)

**Command:**
```bash
# Local/dev (default off)
python3 -m doc_steward.cli freshness-check .

# CI warn mode
LIFEOS_DOC_FRESHNESS_MODE=warn python3 -m doc_steward.cli freshness-check .

# CI block mode (after 2026-02-26)
LIFEOS_DOC_FRESHNESS_MODE=block python3 -m doc_steward.cli freshness-check .
```

**Expected Output (success, block mode):**
```
[PASSED] Freshness check passed (mode: block).
```

**Expected Output (success with warnings, warn mode):**
```
[WARNINGS] Freshness check warnings (N):
  * <warning details>

[PASSED] Freshness check passed with warnings (mode: warn).
```

**Exit Code:** `0` = pass (or pass with warnings in warn mode), `1` = fail (block mode only)

**Evidence:**
- STDOUT contains `[PASSED]` or `[SKIPPED]` message
- Exit code 0 (or 0 with warnings in warn mode)
- If warnings present, stdout lists them

**Failure Modes:**
1. **Runtime status file missing**
   - **Symptom:** Warning/error: `Runtime status file missing: artifacts/status/runtime_status.json`
   - **Action:** Regenerate runtime status:
     ```bash
     # Option 1: Run status generator directly
     python3 -m runtime.tools.status_generator

     # Option 2: Trigger via workflow
     python3 -m runtime.orchestration.missions.steward_mission
     ```
   - **Escalation:** If status generator fails, check runtime logs for underlying issue

2. **Runtime status file stale (>24h)**
   - **Symptom:** Warning/error: `Runtime status file is stale: ... (age: Xh, SLA: 24h)`
   - **Action:** Same as "missing file" — regenerate status
   - **Escalation:** If status generator is not running on schedule, check cron/systemd timers

3. **Contradictions present (severity: block)**
   - **Symptom:** Error: `Contradiction [<id>]: <message> (refs: <files>)`
   - **Action:** Investigate referenced files for conflicting claims; resolve conflict by:
     - Updating stale file to match current reality
     - Correcting error in referenced file
     - Adding DECISIONS.md entry to establish precedence
   - **Escalation:** If contradiction is a design decision (not an error), escalate to Council

4. **Invalid JSON in status file**
   - **Symptom:** Warning/error: `Failed to parse runtime status JSON: ...`
   - **Action:** Check `artifacts/status/runtime_status.json` for syntax errors; regenerate if corrupted
   - **Escalation:** If regeneration produces invalid JSON, file bug against status generator

---

### SO-4: Full Doc Stewardship Gate

**When to use:** Before merging, during build closure, or when docs/ is modified

**Preconditions:**
- Working tree is clean or only contains doc changes
- On a valid feature branch (build/, fix/, hotfix/, spike/)

**Command (automated):**
```python
from runtime.tools.workflow_pack import check_doc_stewardship
result = check_doc_stewardship(repo_root=Path("."), changed_files=["docs/11_admin/BACKLOG.md"], auto_fix=True)
# result["passed"] == True means gate passed
```

**Command (manual):**
```bash
# Full gate (includes admin validators when docs/11_admin/ changed)
python3 scripts/claude_doc_stewardship_gate.py --auto-fix

# Individual checks
python3 -m doc_steward.cli admin-structure-check .
python3 -m doc_steward.cli admin-archive-link-ban-check .
python3 -m doc_steward.cli freshness-check .
python3 -m doc_steward.cli index-check . docs/INDEX.md
python3 -m doc_steward.cli link-check .
```

**Expected Output:**
```json
{
  "passed": true,
  "errors": [],
  "auto_fix_applied": false
}
```

**Evidence:**
- JSON output with `"passed": true`
- All individual validator exit codes = 0
- If auto-fix applied, `"auto_fix_applied": true` and diff shows fixes

**Failure Modes:**
- See individual validator failure modes (SO-1, SO-2, SO-3)
- If auto-fix fails, manual intervention required

---

### SO-5: Update STATE and BACKLOG (Auto)

**When to use:** Automatically during build closure (via workflow_pack)

**Preconditions:**
- Build has evidence (commits, test results)
- `docs/11_admin/LIFEOS_STATE.md` and `BACKLOG.md` exist

**Command (programmatic):**
```python
from runtime.tools.workflow_pack import update_state_and_backlog
update_state_and_backlog(
    repo_root=Path("."),
    new_focus="W7-T01 Ledger hash-chain hardening",
    completed_items=["W5-T01 E2E Spine proof"],
    evidence_pointer="commit 195bd4d"
)
```

**Expected Output:**
- `LIFEOS_STATE.md` updated with new focus/recent wins
- `BACKLOG.md` items marked done with evidence pointers
- Git diff shows changes

**Evidence:**
- Modified STATE/BACKLOG files
- Atomic writes (no partial updates)

**Failure Modes:**
1. **Parse error in BACKLOG.md**
   - **Symptom:** Exception during backlog parsing
   - **Action:** Check BACKLOG.md format; fix syntax errors
   - **Escalation:** If format is valid but parser fails, file bug

2. **Concurrent modification conflict**
   - **Symptom:** File modified between read and write
   - **Action:** Retry with fresh read
   - **Escalation:** If retry fails, halt and request manual review

---

## Governance Boundaries

### Protected Paths (Hands Off)

These paths require **Council approval** to modify. Do NOT edit without explicit governance decision:

- `docs/00_foundations/` — Core principles, constitution, invariants
- `docs/01_governance/` — Governance protocols, council rulings, policies
- `config/governance/protected_artefacts.json` — Governance configuration

**Enforcement:** DAP validator + policy engine

### Append-Only Files

These files use **append-only** semantics. Do NOT edit existing entries:

- `docs/11_admin/DECISIONS.md` — Append new decisions only; never modify existing entries

**Enforcement:** Policy engine + diff budget validator

### Immutable Archives

Files in `docs/11_admin/archive/` are **immutable**. Only allowed modifications:

- Typo fixes in archive README itself
- Mechanical path corrections if repo structure changes (rare)

**Enforcement:** Admin structure validator + archive link ban validator

### Diff Budget Limits

Some operations have **diff budget constraints** (if enforced by StewardMission):

- Large diffs may trigger review requirements
- Check mission config for current limits

---

## Validation Checklist

### Pre-Modification Checklist

Run **before** modifying docs:

```bash
git status
python3 -m doc_steward.cli admin-structure-check .
python3 -m doc_steward.cli admin-archive-link-ban-check .
```

### Post-Modification Checklist

Run **after** modifying docs (machine-executable; copy-paste-safe):

```bash
# 1. Admin structure enforcement
python3 -m doc_steward.cli admin-structure-check .

# 2. Archive link hygiene
python3 -m doc_steward.cli admin-archive-link-ban-check .

# 3. Freshness check (mode-gated)
python3 -m doc_steward.cli freshness-check .

# 4. Index consistency
python3 -m doc_steward.cli index-check . docs/INDEX.md

# 5. Link validation
python3 -m doc_steward.cli link-check .

# 6. Test suite (doc validators)
pytest tests_doc/ -q

# 7. Verify working tree
git status --porcelain=v1
```

**Expected result:** All commands exit 0, git status shows only expected changes.

### Pre-Merge Checklist

Run **before** merging to main:

```bash
# Full test suite
pytest runtime/tests -q

# Full doc validation
python3 -m doc_steward.cli admin-structure-check .
python3 -m doc_steward.cli admin-archive-link-ban-check .
LIFEOS_DOC_FRESHNESS_MODE=warn python3 -m doc_steward.cli freshness-check .
python3 -m doc_steward.cli index-check . docs/INDEX.md
python3 -m doc_steward.cli link-check .

# Verify clean state
git status --porcelain=v1
```

---

## Failure Modes & Escalation

### Escalation Tiers

**Tier 1: Mechanical Fix** — Deterministic resolution, no judgment required
- Examples: Rename file to match pattern, fix link syntax, add missing README
- **Owner:** COO Runtime (autonomous) or delegate agent
- **SLA:** Immediate

**Tier 2: Context-Dependent Fix** — Requires understanding intent or history
- Examples: Resolve contradiction between docs, decide archive disposition
- **Owner:** Antigravity (primary builder) or CSO
- **SLA:** Within current sprint

**Tier 3: Governance Decision** — Requires policy judgment or architectural choice
- Examples: Modify protected paths, change governance boundaries, update allowlist with new semantic category
- **Owner:** Council (via Council Protocol v1.3)
- **SLA:** Next council session (typically 3-5 days)

### Common Escalation Triggers

| Trigger | Tier | Owner | Next Action |
|---------|------|-------|-------------|
| Validator fails with clear fix (e.g., rename file) | 1 | COO/Agent | Apply fix, re-validate |
| Contradiction between docs, unclear precedence | 2 | Antigravity/CSO | Review authority hierarchy, update stale doc |
| Need to modify protected path (00_foundations, 01_governance) | 3 | Council | Create review packet, invoke council |
| Auto-update fails due to parse error | 2 | Antigravity | Fix format, re-run update |
| Freshness gate blocking in CI, status generator broken | 2 | Antigravity | Debug status generator, temporary mode=warn override if needed |
| Archive policy violation requires un-archiving file | 3 | Council | Create DECISIONS.md entry, restore file with rationale |

---

## Appendix: Quick Reference

### Validator Exit Codes

- `0` = Pass
- `1` = Fail (blocking)

### Freshness Modes

| Mode | Local/Dev | CI (before 2026-02-26) | CI (after 2026-02-26) |
|------|-----------|------------------------|------------------------|
| `off` | ✓ (default) | ✗ | ✗ |
| `warn` | ✗ | ✓ (default) | ✗ |
| `block` | ✗ | ✗ | ✓ (default) |

### File Patterns

- Build summary: `*_Build_Summary_YYYY-MM-DD.md`
- Archive subdir: `YYYY-MM-DD_<topic>/`

### Authority Hierarchy (Conflict Resolution)

1. LIFEOS_STATE.md + BACKLOG.md (auto-updated canonical)
2. DECISIONS.md (append-only decisions)
3. Plan_Supersession_Register.md + referenced plan
4. Specs in docs/11_admin/
5. Derived views (AUTONOMY_STATUS.md, etc.)
6. Strategic context (lifeos-master-operating-manual-v2.1.md)
7. Archive (historical reference only)

---

**Version:** 1.0
**Effective Date:** 2026-02-14
**Next Review:** On demand (triggered by validator changes or governance updates)
**Maintainer:** Antigravity (primary builder), COO Runtime (executor)
