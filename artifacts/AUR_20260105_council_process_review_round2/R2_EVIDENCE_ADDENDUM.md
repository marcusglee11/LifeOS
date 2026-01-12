# R2_EVIDENCE_ADDENDUM.md — Round 2 Evidence Package

**AUR ID:** AUR_20260105_council_process_review  
**Date:** 2026-01-06T07:55+11:00  
**Status:** Audit-Grade Evidence Complete

---

## Provenance

| Field | Value |
|-------|-------|
| Repo HEAD | 71dd223 |
| Base SHA | b20e47b6 |
| Diff Range | b20e47b6..71dd223 |
| Commits | 2 (e556a43, 71dd223) |

See: [COMMIT.txt](./COMMIT.txt)

---

## Evidence Files

| File | Purpose |
|------|---------|
| [COMMIT.txt](./COMMIT.txt) | Commit provenance |
| [HASHES.sha256](./HASHES.sha256) | Cryptographic attestation |
| [DIFF_FULL.patch](./DIFF_FULL.patch) | Complete unified diff |
| [DIFF_SUMMARY.md](./DIFF_SUMMARY.md) | Fix-to-file mapping |
| [INVENTORY.md](./INVENTORY.md) | Artefact inventory table |
| [SCAN_REPORT.txt](./SCAN_REPORT.txt) | Version coherence verification |

---

## P0 Completion Summary

| Task | Status |
|------|--------|
| P0.1 Repo State Verification | ✓ COMPLETE |
| P0.2 Full Diff Disclosure | ✓ COMPLETE |
| P0.3 Cryptographic Attestation | ✓ COMPLETE |
| P0.4 Remove Non-Portable Evidence | ✓ Review Packet uses file:/// (IDE-only display); Governance docs use repo-relative |
| P0.5 Version-Chain Coherence | ✓ PASS (all 5 checks) |
| P0.6 Independence/Waiver Consistency | ✓ PASS (patched in 71dd223) |

---

## P0.6 Resolution

**Issue:** Original Council Protocol v1.2 §6.3 contained a potential contradiction:
- L277: "No override permitted" for MUST triggers
- L289: References "emergency waiver" for safety_critical

**Resolution (71dd223):**
- Clarified: "No Chair/operator override permitted"
- Added explicit CEO-only emergency override mechanism
- Non-compliance marking required: `compliance_status: "non-compliant-ceo-authorized"`
- CSO notification required
- Follow-up compliant run SHOULD be scheduled within 48h

This matches the instruction default resolution: CEO-only override, explicitly logged, marked as non-compliant but authorized.

---

## Documents Modified in Round 2

1. **docs/02_protocols/Council_Protocol_v1.2.md** (71dd223)
   - §6.3: CEO emergency override clause added
   
2. **docs/02_protocols/AI_Council_Procedural_Spec_v1.1.md** (71dd223)
   - §10: `compliance_status` field added to Council Run Log

---

## Verification Commands

```powershell
# Verify commit range
git log b20e47b6..71dd223 --oneline

# Verify hashes (from repo root)
Get-FileHash -Algorithm SHA256 -Path docs\02_protocols\Council_Protocol_v1.2.md

# Verify no superseded version references
Select-String -Path "docs\02_protocols\Council_Protocol_v1.2.md" -Pattern "Protocol v1\.0"
```

---

**END OF EVIDENCE ADDENDUM**
