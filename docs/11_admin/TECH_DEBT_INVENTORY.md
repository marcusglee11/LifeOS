# Tech Debt Inventory

<!-- markdownlint-disable MD013 MD032 MD060 -->

**Created:** 2026-02-27
**Source:** 3-Pass Audit (build/audit-3pass)
**Status:** Living document — update trigger conditions as items are resolved.

This inventory documents known structural debt with explicit **trigger conditions** for when each item becomes urgent. The goal is to track without over-engineering — fix things when they become obstacles, not before.

---

## Audit References

- 2026-03-28: [QUALITY_AUDIT_BASELINE_v1.0.md](./QUALITY_AUDIT_BASELINE_v1.0.md) — repo-wide quality baseline audit. Cross-reference Item 4 (Logging Inconsistency) and Item 5 (Validation Pattern Fragmentation) when triaging follow-up cleanup.

## 1. Orchestration Module Sprawl

**Location:** `runtime/orchestration/` (65+ files)
**Issue:** Single flat package containing functionally distinct subsystems: council (11 files), dispatch, loop, missions, receipts, transforms.
**Risk:** Naming collisions, slow imports, hard to onboard new contributors.

**Trigger:** _"If adding a new orchestration subsystem, extract `council/` or `dispatch/` to a peer module (`runtime/council/`, `runtime/dispatch/`) first."_

---

## 2. God Functions

**Issue:** Several functions exceed 100 lines. Functions this long are harder to test and modify safely.

| File | Function | Approx Lines |
|------|----------|-------------|
| `runtime/cli.py` | `main()` | ~167 |
| `runtime/cli.py` | `cmd_mission_run()` | ~140 |
| `runtime/orchestration/engine.py` | `run_workflow()` | ~130 |
| `runtime/orchestration/engine.py` | `_execute_mission()` | ~129 |
| `runtime/orchestration/council/fsm.py` | 2 methods | >100 each |

**Trigger:** _"If a function exceeds 200 lines OR gains new conditional branches, split it before adding more code."_

---

## 3. spine.py Complexity

**Location:** `runtime/orchestration/loop/spine.py` (~1,390 lines)
**Issue:** Single file handling the full autonomous build loop spine. Growing toward maintenance risk threshold.

**Trigger:** _"If `spine.py` exceeds 1,500 lines, split into `spine_core.py` + `spine_phases.py` before adding new phases."_

---

## 4. Logging Inconsistency

**Issue:** Mixed use of `print()` (~268 occurrences) and `logging` calls (~108 occurrences) across the codebase.
**Note:** CLI `print()` calls may be intentional (user-facing output). The inconsistency is in internal modules.

**Trigger:** _"If adding observability, monitoring, or structured log ingestion, unify all internal `print()` to `logger.*()` first."_

---

## 5. Validation Pattern Fragmentation

**Issue:** ~125 `validate_*` functions scattered across the codebase with no central registry. Similar validation logic is sometimes duplicated.

**Trigger:** _"If adding a new validation type that would be the 3rd+ similar validator in a module, consider a registry pattern first."_

---

## 6. Workspace Root Detection — Partial Consolidation

**Canonical:** `runtime/util/workspace.py:resolve_workspace_root()` (exported via `runtime.util`)
**Duplicates:**
- `runtime/governance/tool_policy.py:resolve_workspace_root()` — module-internal; raises `GovernanceUnavailable` (not `RuntimeError`). Safe consolidation requires exception wrapping — deferred.
- `runtime/config/repo_root.py:detect_repo_root()` — different semantics (walks `.git` markers, used by CLI). Not a duplicate; separate utility.

**Completed:** `runtime/governance/policy_loader.py` already delegates to `runtime.util.workspace`.

**Trigger:** _"If modifying `tool_policy.py:resolve_workspace_root()`, migrate it to delegate to `runtime.util.workspace` with `GovernanceUnavailable` wrapping at that time."_

---

## 7. Dual Steward Configs

**Location:** `config/Antigrav_DocSteward_Config_v0.1.yaml` + `config/steward_runner.yaml`
**Issue:** Two steward config files with potentially overlapping settings.

**Trigger:** _"Consolidate during the next steward feature work cycle."_

---

## 8. Closure Manifest Schema v1 vs v1.1

**Issue:** Schema v1 may be deprecated in favor of v1.1. Unclear if any code paths still reference v1.

**Action:** _"Verify no code references v1 exclusively, then remove v1 schema artifacts."_

---

## Resolved Items (from this audit)

The following items were **fixed** during the 2026-02-27 audit rather than documented:

| Item | Fix |
|------|-----|
| API key prefix in trace logs (`opencode_client.py:626`) | Replaced `or_key[:10]` with `***masked***` |
| Temp auth.json cleanup on abnormal exit | Added `atexit.register(self._cleanup_config)` in `_create_isolated_config()` |
| Full HTTP response body in debug logs | Truncated to 200 chars in 3 REST failure paths |
| `EnvelopeViolation` defined in 4 places | Consolidated to `runtime/errors.py`; 3 duplicates removed |
| Duplicate imports in `mission/__init__.py` | Removed duplicate `MissionSynthesisRequest` + `synthesize_mission` entries |

<!-- markdownlint-enable MD013 MD032 MD060 -->
