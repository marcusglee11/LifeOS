# Review Packet: OpenCode Phase 3 Envelope Broadening

**Mode**: Standard Mission  
**Date**: 2026-01-09  
**Files Changed**: 3

## Summary

Broadened OpenCode's doc-steward envelope to match Antigravity capabilities per CEO waiver recorded 2026-01-09. The Phase 2 restrictions have been removed: denylist roots cleared, extension restrictions removed, structural operations (delete/rename/move/copy) enabled with audit logging. Path security checks retained (traversal, symlink, repo containment).

## Authority

- **CEO Waiver**: [DECISIONS.md](file:///c:/Users/cabra/Projects/LifeOS/docs/11_admin/DECISIONS.md) entry dated 2026-01-09

## Changes

| File | Change Type |
|------|-------------|
| scripts/opencode_gate_policy.py | MODIFIED → Phase 3 v2.0 |
| scripts/opencode_ci_runner.py | MODIFIED → Phase 3 v2.0 |
| tests_recursive/test_opencode_gate_policy.py | MODIFIED → Phase 3 expectations |

## Key Policy Changes

### What's Now Allowed (Previously Blocked)

- Governance paths: `docs/00_foundations/`, `docs/01_governance/`
- Scripts and config paths
- All file extensions (not just `.md`)
- Structural operations: delete, rename, move, copy
- Review packet modifications (previously add-only)

### What Remains Enforced (Security)

- Path traversal protection (`../` blocked)
- Absolute path blocking
- Symlink defense (git index + filesystem)
- Repo containment checks
- Out-of-allowlist paths blocked

### New Audit Logging

- Governance-sensitive paths logged (not blocked)
- `detect_auditable_ops()` for structural operation tracking
- `check_governance_sensitive()` for sensitive path detection

## Verification

```
87 passed, 2 skipped in 0.58s
```

Skipped tests: Symlink creation tests (Windows limitation)

## Diff Summary

### [opencode_gate_policy.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_gate_policy.py)

- Version: CT-2 Phase 2 v1.3 → Phase 3 v2.0
- `ALLOWLIST_ROOTS`: Expanded to include full repo (artifacts/, docs/, runtime/, scripts/, config/, tests/, etc.)
- `DENYLIST_ROOTS`: Cleared (was: config/, docs/00_foundations/, docs/01_governance/, scripts/)
- `DENYLIST_EXTENSIONS`: Cleared (was: [".py"])
- `ALLOWED_EXTENSIONS_DOCS`: Set to None (no restrictions)
- New: `GOVERNANCE_SENSITIVE_ROOTS` for audit logging
- New: `detect_auditable_ops()` function
- New: `check_governance_sensitive()` function
- `detect_blocked_ops()`: Now returns empty list (all ops allowed)

### [opencode_ci_runner.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_ci_runner.py)

- Version: CT-2 Phase 2 v2.0 → Phase 3 v2.0
- `valid_actions`: Expanded to include delete, rename, move, copy
- `validate_diff_entry()`: Updated to skip denylist/extension checks, allow all ops
- Path security checks retained

### [test_opencode_gate_policy.py](file:///c:/Users/cabra/Projects/LifeOS/tests_recursive/test_opencode_gate_policy.py)

- Updated test expectations for Phase 3 behavior
- Denylist tests: Now expect `not matched` for cleared roots
- Extension tests: Now expect `ok` for non-.md files
- Structural ops tests: Now expect empty blocked list
- Runner envelope tests: Now expect allowed for governance paths, scripts, all ops
