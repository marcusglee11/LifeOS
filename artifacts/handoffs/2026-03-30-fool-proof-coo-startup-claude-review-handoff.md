# Handoff Pack: Fool-Proof COO Startup Surface

## Metadata
- Reviewer target: Claude Code
- Branch: `fix/fool-proof-coo-startup`
- Worktree: `/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/fool-proof-coo-startup`
- Base: `main` (`86f64e476b7f7b6d745e83d61b3fc210f519be7f`)
- HEAD: `86f64e47`
- Commit state: uncommitted worktree diff only
- Scope: harden the operator-facing `coo` wrapper so startup follows `coo ensure -> coo doctor -> coo app|tui -> coo stop`

## Requested Review Focus
Please review the worktree diff for correctness, regression risk, and shell-safety. The highest-sensitivity areas are:

1. `runtime/tools/coo_worktree.sh`
   - `ensure_coo_shim()` bootstrap and stale-shim repair
   - `ensure --json` and `doctor --json` pure JSON behavior
   - `run_startup_probe_bundle()` timeout behavior and exit-code preservation
   - `run_doctor()` blocker classification and safe-fix dispatch
   - `start` / `app` / `tui` failure messaging and break-glass interaction
2. `config/openclaw/gate_reason_catalog.json`
   - remediation metadata completeness and action mapping
3. Tests
   - `runtime/tests/test_coo_worktree_ensure.py`
   - `runtime/tests/test_coo_worktree_doctor.py`

## Change Summary

### Operator surface
- `coo ensure` now bootstraps `~/.local/bin/coo` and `~/.local/bin/coo.real`.
- `coo doctor` now diagnoses gate failures and can apply bounded safe fixes.
- Startup failure paths now direct operators to `coo doctor`.
- `COO_STARTUP_TIMEOUT_SEC` adds an outer timeout around startup health probing.

### Entry-point cleanup
- Removed `coo = "runtime.cli:main"` from `pyproject.toml`.
- `coo` is now wrapper-only; Python orchestration remains under `lifeos`.

### Remediation catalog
- Added `remediation` metadata to every gate reason.
- Auto-fixable reasons are intentionally limited to:
  - `gateway_probe_failed` -> `gateway.ensure`
  - `model_ladder_policy_failed` -> `models.fix`

### Docs
- Updated wrapper/operator docs to point users at:
  - `coo ensure`
  - `coo doctor`
  - `coo doctor --apply-safe-fixes`

## Files In Scope
- `config/openclaw/gate_reason_catalog.json`
- `pyproject.toml`
- `runtime/tools/OPENCLAW_COO_RUNBOOK.md`
- `runtime/tools/coo_worktree.sh`
- `tools/windows/README.md`
- `runtime/tests/test_coo_worktree_doctor.py`
- `runtime/tests/test_coo_worktree_ensure.py`

## Review Findings Already Fixed In This Pass
These were found during local review and are already addressed in the current diff:

1. Probe exit status was being swallowed in shell negation paths.
   - Fix: `start` and `doctor` now capture the real return code from `run_startup_probe_bundle()` using an `if ...; then ...; else rc="$?"; fi` pattern.
2. Generated shim exported `LIFEOS_BUILD_REPO` without safe quoting.
   - Fix: shim generation now writes a quoted value via Python `json.dumps(repo)`.

## Reviewer Questions
Please pay special attention to these points:

1. Is `doctor --json` guaranteed to emit only JSON in all branches, including `--apply-safe-fixes` reprobe paths?
2. Is the safe-fix dispatcher sufficiently constrained now that it uses `action_id` allowlisting instead of `eval`?
3. Are there any shell edge cases around `set -e`, `timeout`, or `mktemp` cleanup that still need hardening?
4. Does `ensure_coo_shim()` correctly avoid clobbering valid operator-local shims while still repairing stale repo paths?
5. Are the startup timeout semantics acceptable for both `start` and `doctor`?

## Validation Evidence

### Syntax check
- Command:
  - `bash -n runtime/tools/coo_worktree.sh`
- Result:
  - passed

### Targeted tests
- Command:
  - `pytest runtime/tests/test_coo_worktree_ensure.py runtime/tests/test_coo_worktree_doctor.py -v`
- Result:
  - `22 passed`

### Full runtime suite
- Command:
  - `pytest runtime/tests -q`
- Result:
  - `2826 passed, 8 skipped, 6 warnings`

### Scoped quality gate
- Command:
  - `python3 scripts/workflow/quality_gate.py check --scope changed --json`
- Result:
  - `passed: true`
  - advisory-only tool-unavailable warnings for `ruff`, `mypy`, `biome`, and `shellcheck`

## Suggested Claude Review Commands
- `git status --short`
- `git diff -- runtime/tools/coo_worktree.sh`
- `git diff -- config/openclaw/gate_reason_catalog.json`
- `git diff -- runtime/tests/test_coo_worktree_doctor.py runtime/tests/test_coo_worktree_ensure.py`
- `pytest runtime/tests/test_coo_worktree_ensure.py runtime/tests/test_coo_worktree_doctor.py -v`
- `pytest runtime/tests -q`

## Notes
- There is no fix commit yet; review the live worktree diff.
- The implementation was done inside the scoped worktree only.
- Main had unrelated local untracked files outside this worktree; they were not modified as part of this task.
