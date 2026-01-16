# Review Packet: Council Process Review Fix Pack Execution

**AUR ID:** AUR_20260105_council_process_review  
**Mission Type:** Lightweight Stewardship (Diff-Based Context)  
**Date:** 2026-01-06T07:30+11:00  
**Agent:** Antigravity (Doc Steward)

---

## Summary

Executed CEO-approved Fix Pack containing 12 fixes (F1–F12) across 4 governance documents following M2_FULL council review with distributed topology (Gemini, Kimi, DeepSeek, Claude).

---

## Issue Catalogue (Resolved)

| Fix | Priority | Target Document | Change |
|-----|----------|-----------------|--------|
| F1 | CRITICAL | Runtime Binding Spec | Updated all "v1.0" → "v1.1" references |
| F2 | CRITICAL | Runtime Binding Spec | Replaced §4.3 local template with canonical reference |
| F3 | HIGH | Council Protocol | SHOULD→MUST for safety_critical, governance_protocol, tier_activation |
| F4 | HIGH | Council Protocol + Procedural Spec | Added waiver logging + CSO audit |
| F5 | HIGH | Council Protocol | Expanded Testing/Governance seat definitions |
| F6 | HIGH | Council Protocol | Added Step 1.5 (Seat completion validation) |
| F7 | HIGH | CCP Schema | Added v1.0 promotion criteria |
| F8 | MEDIUM | Council Protocol | Co-Chair Contradiction Ledger verification |
| F9 | MEDIUM | Procedural Spec | Hash field optional→SHOULD |
| F10 | MEDIUM | Council Protocol | Added explicit enum definitions |
| F11 | MEDIUM | Procedural Spec | Max 2 correction cycles |
| F12 | MEDIUM | Council Protocol | Bootstrap mode restrictions |

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| All CRITICAL fixes (F1–F2) applied | ✓ PASS |
| All HIGH fixes (F3–F7) applied | ✓ PASS |
| All MEDIUM fixes (F8–F12) applied | ✓ PASS |
| Superseded versions archived | ✓ PASS |
| INDEX.md updated | ✓ PASS |
| Strategic Corpus regenerated | ✓ PASS |

---

## Non-Goals

- F13–F16 (LOW priority): Explicitly deferred per Fix Pack specification
- Automation tooling for CCP validation (F15 deferred)
- Merging Procedural Spec (F13 deferred)

---

## Document Changes

### Created Files

| File | Fixes Applied |
|------|---------------|
| [Council_Invocation_Runtime_Binding_Spec_v1.1.md](docs/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.1.md) | F1, F2 |
| [Council_Protocol_v1.2.md](docs/02_protocols/Council_Protocol_v1.2.md) | F3, F4, F5, F6, F8, F10, F12 |
| [AI_Council_Procedural_Spec_v1.1.md](docs/02_protocols/AI_Council_Procedural_Spec_v1.1.md) | F4, F9, F11 |
| [Council_Context_Pack_Schema_v0.3.md](docs/02_protocols/Council_Context_Pack_Schema_v0.3.md) | F7 |

### Archived Files

| File | To |
|------|-----|
| Council_Invocation_Runtime_Binding_Spec_v1.0.md | docs/99_archive/ |
| Council_Protocol_v1.1.md | docs/99_archive/ |
| AI_Council_Procedural_Spec_v1.0.md | docs/99_archive/ |
| Council_Context_Pack_Schema_v0.2.md | docs/99_archive/ |

### Modified Files

| File | Change |
|------|--------|
| [INDEX.md](docs/INDEX.md) | Updated timestamp and version references |
| [LifeOS_Strategic_Corpus.md](docs/LifeOS_Strategic_Corpus.md) | Regenerated |

---

## Appendix — Key Diffs

### F3: Hardened Independence Rule (Council Protocol v1.2 §6.3)

```diff
-  then at least one of **Risk/Adversarial** or **Governance** seats SHOULD be executed on an independent model (different vendor/model family) when practical.
-  - If not practical, the CCP must record: `override.rationale` explaining why independence was not used.
+  **MUST (hard requirement):**
+  If any of the following are true:
+  - safety_critical == true, OR
+  - touches includes governance_protocol, OR
+  - touches includes tier_activation,
+  
+  then at least one of **Risk/Adversarial** or **Governance** seats MUST be executed on an independent model (different vendor/model family). No override permitted.
+
+  **SHOULD (soft requirement with logging):**
+  If any of the following are true:
+  - touches includes runtime_core, OR
+  - uncertainty == high and blast_radius != local,
+  
+  then at least one of **Risk/Adversarial** or **Governance** seats SHOULD be executed on an independent model when practical.
+  - If not practical, the CCP must record: `override.rationale` explaining why independence was not used.
+  - CSO may audit override patterns; systemic waivers (>50% of applicable runs) trigger escalation.
```

### F6: Seat Completion Validation (Council Protocol v1.2 §8)

```diff
+**Step 1.5 — Seat completion validation**
+Before synthesis, Chair MUST verify:
+- All seats assigned in the CCP header `model_plan_v1.role_to_model` have submitted outputs
+- All outputs conform to the required schema (§7)
+- Any missing seats are either: (a) explicitly waived with rationale, or (b) flagged as blocking
+
+Chair may not proceed to synthesis with missing seats unless topology permits reduced seat count (M0_FAST or explicit M1_STANDARD seat selection).
```

### F7: CCP Schema Promotion Criteria (v0.3)

```diff
+## Promotion Criteria (v0.3 → v1.0)
+
+This schema may be promoted to v1.0 when the following are satisfied:
+
+1. **Mode selection test suite**: Automated tests covering all `mode_selection_rules_v1` logic paths
+2. **Template validation test**: Parser that validates CCP structure against required sections
+3. **REF parsing test**: Parser that extracts and validates REF citations in all three permitted formats
+4. **Adversarial review**: At least one council review of the schema itself with Governance and Risk seats on independent models
+
+Status: [ ] Mode selection tests  [ ] Template validation  [ ] REF parsing  [ ] Adversarial review
```

---

## Stewardship Evidence

- **INDEX.md timestamp**: 2026-01-06T07:30+11:00
- **Corpus regeneration**: Strategic Context (v1.3) successfully generated
- **Archive complete**: 4 superseded files moved to `docs/99_archive/`

---

**END OF REVIEW PACKET**
