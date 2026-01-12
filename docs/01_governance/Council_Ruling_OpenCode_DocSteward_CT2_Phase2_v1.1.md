# Council Ruling: OpenCode Document Steward CT-2 Phase 2 — PASS (GO)

**Ruling**: PASS (GO)  
**Date**: 2026-01-07 (Australia/Sydney)  
**Subject**: CT-2 Phase 2 (P0) — OpenCode Doc Steward Activation: Enforced Gate + Passage Fixes  
**Bundle Accepted**: Bundle_CT2_Phase2_Passage_v2.4_20260107.zip  

---

## Scope Passed

- Post-run git diff is the source of truth for enforcement.
- Phase 2 envelope enforced (denylist-first, allowlist enforced, docs `.md`-only, `artifacts/review_packets/` add-only `.md`).
- Structural ops blocked in Phase 2 (delete/rename/move/copy) derived from git name-status.
- Packet discovery remains explicit `packet_paths` only (no convention fallback).
- Symlink defense is fail-closed (git index mode + filesystem checks; unverifiable => BLOCK).
- CI diff acquisition is fail-closed with explicit reason codes.
- Evidence contract satisfied:
  - deterministic artefact set produced (exit_report, changed_files, classification, runner.log, hashes)
  - truncation footer is machine-readable (cap/observed fields present)
  - no ellipses (`...` / `…`) appear in evidence-captured outputs
- Passage evidence bundles included in the accepted bundle (PASS + required BLOCK cases) with hashes.

## Non-goals Confirmed

- No override mechanism introduced.
- No expansion of activation envelope.
- No permission for delete/rename/move in Phase 2.

## Recordkeeping

- The accepted bundle is archived under the canonical stewardship evidence root: `artifacts/ct2/Bundle_CT2_Phase2_Passage_v2.4_20260107.zip`.
- Timestamps in `exit_report.json` are operationally accepted; byte-for-byte reproducibility across reruns is not required for this passage.

---

## Sign-Off

**Chair (Architect/Head of Dev/Head of Testing)** — APPROVED FOR PASSAGE  
**Date**: 2026-01-07 (Australia/Sydney)

---

**END OF RULING**
