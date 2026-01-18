# Review_Packet_Stewardship_Hardening_Combined_v1.0

**Mission**: Feature Hardening + Canonical Surface Scope + Governance Fixes  
**Date**: 2026-01-02  
**Author**: Antigravity Agent  
**Status**: COMPLETE — Smoke Test `smoke-009` PASSED (Exit Code 0)

---

## 1. Summary

Hardened Stewardship Runner (P0/P1 fixes), enforced Canonical Surface Scope for all validators, and fixed Governance Index alignment.

---

## 2. Stewardship Runner Fixes (P0/P1)

| Issue | Fix | Verification |
|-------|-----|--------------|
| **P0-1 Test Scope** | `tests.paths` appended to argv | AT-11 ✅ |
| **P0-2 Logs** | `logs/steward_runner/` gitignored | Smoke Test ✅ |
| **P1-1 Staging** | `git add -A -- <roots>` | AT-07 ✅ |
| **P1-2 Normalization** | Segment-based `..`, Windows/UNC detection, exact-file support | AT-12, AT-13 ✅ |
| **SyntaxWarning** | Raw strings for regex docstrings | Manual check ✅ |

---

## 3. Canonical Surface Scope (Validation Policy)

All validators now strictly scoped to **Canonical Roots** (`docs/00_foundations/`, `docs/01_governance/`).

| Validator | Scope/Policy | Change |
|-----------|--------------|--------|
| **link-check** | Canonical Roots + Template Skip | Explicit allowlist + `{token}` regex skip |
| **dap-validate** | Canonical Roots + INDEX exception | Scoped walk + `INDEX.md` skip |
| **index-check** | Canonical Roots | Scoped walk for unindexed files |

---

## 4. Governance & Structural Fixes

| Component | Status | Fix |
|-----------|--------|-----|
| **Agent Constitution** | Restored ✅ | Copied template to `docs/01_governance/` |
| **ARTEFACT_INDEX** | Fixed ✅ | Pointed protocols to `docs/02_protocols/` |
| **Gov Index Validator** | Updated ✅ | Allowed `docs/02_protocols/` prefix |

---

## 5. Verification Results

### Acceptance Tests
**20/20 Passed** (`tests_recursive/test_steward_runner.py`)

### Full Smoke Test (`smoke-009`)
- **Preflight**: PASS (Clean repo)
- **Tests**: PASS (347 tests passed)
- **Validator 0 (Gov Index)**: PASS (All artifacts found)
- **Validator 1 (DAP)**: PASS (Canonical docs compliant)
- **Validator 2 (Index)**: PASS (Canonical docs indexed)
- **Postflight**: Success

---

## Appendix — Key Code Changes

### allowlist hardening
```python
# Segment-based limits
segments = normalized.rstrip("/").split("/")
for segment in segments:
    if segment == "..": return normalized, "path_traversal"
    if segment == ".": return normalized, "current_dir_segment"
```

### canonical_roots (validators)
```python
CANONICAL_ROOTS = ["00_foundations", "01_governance"]

def check_xxx(doc_root, canonical_roots=None):
    if canonical_roots is None: canonical_roots = CANONICAL_ROOTS
    # ... only walk canonical roots ...
```

---

## End of Review Packet
