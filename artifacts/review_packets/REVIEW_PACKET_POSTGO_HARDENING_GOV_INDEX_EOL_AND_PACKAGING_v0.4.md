# Review Packet: Post-GO Hardening (v0.4)

**Mission**: Stabilize Raw-Bytes Hashing and Packaging Clarity
**Author**: Antigravity
**Date**: 2026-01-06
**Status**: REVIEW_READY

---

## 1. Summary

This v0.4 fix pack ensures patch completeness and evidence hygiene:
1.  **Patch Match**: Unified diff includes all 4 apply files.
2.  **Packaging Clarity**: Bundle root contains only apply-files and evidence.
3.  **Evidence Hygiene**: Full-fidelity logs with zero ellipses.

---

## 2. Changed Files (Apply to Repo)

The following files are included in the unified diff and MUST be applied to the repository:

| File | Status | Purpose |
|------|--------|---------|
| `docs/01_governance/ARTEFACT_INDEX.json` | Modified | Updates sha256 policy text for LF normalization |
| `.gitattributes` | New | Enforces `eol=lf` for governance indices |
| `tools/validate_governance_index.py` | Modified | Adds strict CRLF rejection check |
| `scripts/package_audit_fixpack.py` | New | Script to generate admissible bundles |

---

## 3. Reference Only (Do Not Apply)

Files under `reference_only/` are included for context/validation convenience only:
- `G-CBS_Standard_v1.0.md`

---

## 4. Evidence

| Artifact | Path |
|----------|------|
| Test Report | `artifacts/TEST_REPORT_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.4.md` |
| Unified Diff | `artifacts/PATCH_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.4.diff` |

---

## 5. Deliverables

| Artifact | Path |
|----------|------|
| Bundle ZIP | `artifacts/bundles/Bundle_PostGo_Hardening_GovIndex_EOL_v0.4.zip` |
| Unified Diff | `artifacts/PATCH_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.4.diff` |

---

## 6. Verification Gates

| Gate | Command | Result |
|------|---------|--------|
| TDD Compliance | `pytest tests_doc/test_tdd_compliance.py -v` | 12/12 PASSED |
| Governance Index | `python tools/validate_governance_index.py` | PASSED |
