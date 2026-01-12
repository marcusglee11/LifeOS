# Context Pack: G-CBS v1.0 Repayment Build

**Date**: 2026-01-06T14:15+11:00
**Author**: Antigravity Agent
**Purpose**: Bounded context required to implement A1/A2 re-closure under G-CBS validator
**SHA256**: (computed at completion)

---

## H1. LIFEOS_STATE.md — Waiver References

**Source**: `docs/11_admin/LIFEOS_STATE.md`
**Relevance**: Identifies A1/A2 as CLOSED (WAIVER) requiring G-CBS repayment

```markdown
6. **[CLOSED (WAIVER)]** A2 Reactive v0.1 Determinism | Waiver: `artifacts/waivers/WAIVER_A1A2_Closure_v1_3_4.md` | Waived: zip paths, zip sha mismatch, ellipses | Repayment: G-CBS v1.0 + re-close under validator
7. **[CLOSED (WAIVER)]** A1 Tier-2 Green Baseline | Waiver: `artifacts/waivers/WAIVER_A1A2_Closure_v1_3_4.md` | Waived: zip paths, zip sha mismatch, ellipses | Repayment: G-CBS v1.0 + re-close under validator
```

---

## H2. Waiver Record

**Source**: `artifacts/waivers/WAIVER_A1A2_Closure_v1_3_4.md`
**Relevance**: Defines exact waived checks and repayment trigger

### Waived Checks
| Check | Reason |
|-------|--------|
| Zip entry name canonicalization | Backslash vs forward slash inconsistency |
| Zip SHA mismatch | Recorded SHA differs from attached bundle |
| Forbidden truncation tokens | Prior artefacts contained ellipses (...) |

### Repayment Trigger
1. Implement G-CBS v1.0 (closure_manifest + validate_closure_bundle + build_closure_bundle)
2. Re-close A1/A2 under validator PASS

---

## H3. Binding Protocol — CCP Core TDD Principles

**Source**: `docs/02_protocols/Core_TDD_Design_Principles_v1.0.md`
**Relevance**: Enforcement rules for TDD compliance gate

Key sections:
- §1.2: Deterministic Envelope defined by allowlist at `tests_doc/tdd_compliance_allowlist.yaml`
- §6: Enforcement via `tests_doc/test_tdd_compliance.py`
- Prohibited: `time.time`, `datetime.now`, `uuid.uuid4`, `requests`, `random`, `eval`, `exec`, `__import__`

**Allowlist** (current):
```yaml
schema_version: "v1.0"
enforcement_scope:
  - "runtime/mission"
  - "runtime/reactive"
exemptions: []
```

---

## H4. G-CBS Packaging Infrastructure

### Validator
**Source**: `scripts/closure/validate_closure_bundle.py` (216 lines)
**Purpose**: G-CBS bundle validation with deterministic failure codes

Validation checks:
- `ZIP_PATH_NON_CANONICAL`: Rejects backslashes, absolute paths
- `REQUIRED_FILE_MISSING`: Requires `closure_manifest.json`, `closure_addendum.md`
- `MANIFEST_VERSION_MISMATCH`: Schema version must be `G-CBS-1.0`
- `SHA256_MISMATCH`: Evidence hashes must match manifest
- `TRUNCATION_TOKEN_FOUND`: Scans for `...`, `[PENDING]`, `TBD`, `TODO`
- `EVIDENCE_MISSING`: All manifest evidence paths must exist in zip

### Builder
**Source**: `scripts/closure/build_closure_bundle.py` (190 lines)
**Purpose**: Builds compliant G-CBS bundles with POSIX path normalization

Key features (line 96):
```python
zip_path = rel_p.replace("\\", "/")
```

### Profiles
**Source**: `scripts/closure/profiles/`
- `a1a2.py`: Profile for A1/A2 closure (minimal, checks state proof)
- `ct2.py`: Profile for CT-2 closure
- `council_done.py`: Profile for council closure
- `step_gate_closure.py`: Generic step-gate profile

---

## H5. TDD Compliance Test

**Source**: `tests_doc/test_tdd_compliance.py` (193 lines)
**Purpose**: Enforcement scanner for deterministic envelope

- Loads scope from allowlist with lockfile integrity check (fail-closed)
- Scans for forbidden imports/calls
- 12 tests: 1 core compliance + 11 self-tests for violation detection
- **Current Status**: PASS (12/12)

---

## H6. G-CBS Verification Suite

**Source**: `scripts/closure/tests/verify_gcbs.py` (141 lines)
**Purpose**: End-to-end validation of G-CBS pipeline

Tests:
1. Good bundle: Build + validate → PASS
2. Bad bundle: Inject failures → Validator catches with expected codes

**Current Status**: PASS

---

## H7. Existing Evidence Bundles

**Source**: `artifacts/bundles/`
- `Bundle_A1_A2_Closure_v1_3_4.zip` — Original waived closure (defective)
- `Bundle_TDD_Hardening_Enforcement_v1.3.zip` — Latest TDD bundle

---

## Search Notes

Commands used to locate artifacts:
```
find_by_name *waiver* → artifacts/waivers/WAIVER_A1A2_Closure_v1_3_4.md
find_by_name *A1*A2* → Multiple bundles, addendums, review packets
find_by_name *ct2* → CT-2 scripts and bundles
find_by_name *TDD* → TDD bundles and CCP doc
grep_search G-CBS → validate_closure_bundle.py, build_closure_bundle.py
```

---

## Context Pack Summary

| # | File | Purpose | Included |
|---|------|---------|----------|
| 1 | `docs/11_admin/LIFEOS_STATE.md` | A1/A2 waiver refs | Excerpt |
| 2 | `artifacts/waivers/WAIVER_A1A2_Closure_v1_3_4.md` | Waived checks | Full |
| 3 | `docs/02_protocols/Core_TDD_Design_Principles_v1.0.md` | TDD enforcement | Key sections |
| 4 | `tests_doc/tdd_compliance_allowlist.yaml` | Envelope scope | Full |
| 5 | `scripts/closure/validate_closure_bundle.py` | G-CBS validator | Outline |
| 6 | `scripts/closure/build_closure_bundle.py` | G-CBS builder | Key lines |
| 7 | `scripts/closure/profiles/a1a2.py` | A1A2 profile | Full |
| 8 | `tests_doc/test_tdd_compliance.py` | TDD compliance test | Outline |
| 9 | `scripts/closure/tests/verify_gcbs.py` | G-CBS verification | Outline |

**Total**: 9 files (within 20 file limit)
**Stable ordering**: Lexicographic by repo path
