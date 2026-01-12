# Review_Packet_Stewardship_Fix_Pack_v0.5

**Mission**: Implement Council P1 Conditions (Stewardship Runner Delta)  
**Date**: 2026-01-02  
**Author**: Antigravity Agent  
**Status**: COMPLETE — All Tests Passed (AT-13 to AT-18)

---

## 1. Summary

Implemented all 5 Council P1 conditions and 3 P2 hardenings from `Fix_Pack_Stewardship_Runner_v0.5_Delta.md`.
The Stewardship Runner now enforces strict determinism, race-condition safety, and explicit commit control.

---

## 2. Implemented Fixes

### P1 (Required)
| Issue | Fix | Verification |
|-------|-----|--------------|
| **P1-A Dirty Race** | `run_commit` re-checks `git status` before staging | AT-14 ✅ |
| **P1-B Determinism** | Logs use ISO8601 UTC and enforce sorting of all lists | AT-15 ✅ |
| **P1-C Platform** | Created `PLATFORM_POLICY.md` (Windows rejected) | Manual ✅ |
| **P1-D Commits** | `--commit` flag required. Default is dry-run. | AT-16, 17, 18 ✅ |
| **P1-E Retention** | Created `LOG_RETENTION.md` | Manual ✅ |

### P2 (Hardenings)
| Issue | Fix | Verification |
|-------|-----|--------------|
| **P2-A Empty Path** | `run_commit` validation | Config Logic |
| **P2-B Encoding** | `normalize_commit_path` rejects `%` chars | AT-13 Update ✅ |
| **P2-C Errors** | `normalize_commit_path` returns original path on error | Code Review |

---

## 3. Documentation Created

- **[PLATFORM_POLICY.md](file:///c:/Users/cabra/Projects/LifeOS/docs/01_governance/PLATFORM_POLICY.md)**: Defines Linux/macOS support and Windows rejection rationale.
- **[LOG_RETENTION.md](file:///c:/Users/cabra/Projects/LifeOS/docs/01_governance/LOG_RETENTION.md)**: Defines 30d/90d/Indefinite retention tiers.

---

## 4. Verification

### Acceptance Tests (`tests_recursive/test_steward_runner.py`)
Executed new tests covering the delta scope:
- **AT-14**: changes appearing mid-run are detected and rejected.
- **AT-15**: log file lists are always sorted.
- **AT-16**: running without flags results in dry-run (no commit).
- **AT-17**: running with `--commit` passes commit stage.
- **AT-18**: running with `--dry-run` skips commit stage.
- **AT-13**: updated to verify URL-encoded path rejection.

### Full Suite
Full regression test suite (`runtime/tests`, `tests_doc`, `tests_recursive`) **PASSED**.

---

## Appendix — Flattened Code Snapshots

### File: `docs/01_governance/PLATFORM_POLICY.md`
```markdown
# Platform Policy

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux | ✅ Primary | CI target, production |
| macOS | ✅ Supported | Development |
| Windows (native) | ❌ Unsupported | Use WSL2 |

## Path Handling

The Stewardship Runner rejects Windows-style paths at config validation:
- `C:\path` → rejected (`absolute_path_windows`)
- `\\server\share` → rejected (`absolute_path_unc`)

This is a **safety net**, not runtime support. The runner is not tested on Windows.

## Contributors on Windows

Use WSL2 with Ubuntu. The LifeOS toolchain assumes POSIX semantics.

## Rationale

Maintaining cross-platform compatibility adds complexity without benefit.
LifeOS targets server/CI environments (Linux) and developer machines (Linux/macOS).
```

### File: `docs/01_governance/LOG_RETENTION.md`
```markdown
# Log Retention Policy

## Stewardship Runner Logs

Location: `logs/steward_runner/<run-id>.jsonl`

### Retention by Context

| Context | Location | Retention | Owner |
|---------|----------|-----------|-------|
| Local development | `logs/steward_runner/` | 30 days | Developer |
| CI pipeline | Build artifacts | 90 days | CI system |
| Governance audit | `archive/logs/` | Indefinite | Doc Steward |

### Cleanup Rules

1. **Local**: Logs older than 30 days may be deleted unless referenced by open issue
2. **CI**: Artifacts auto-expire per platform default (GitHub: 90 days)
3. **Pre-deletion check**: Before deleting logs related to governance decisions, export to `archive/logs/`

### Log Content

Each JSONL entry contains:
- `timestamp`: ISO 8601 UTC
- `run_id`: Unique run identifier
- `event`: Event type (preflight, test, validate, commit, etc.)
- Event-specific data (files, results, errors)

### Audit Trail

Logs are append-only during a run. The `run_id` ties all entries together.
For governance audits, the complete log for a run provides deterministic replay evidence.
```

---

## End of Review Packet
