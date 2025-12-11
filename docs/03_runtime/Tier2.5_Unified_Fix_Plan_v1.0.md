# Unified Fix Plan v1.0 (Non-Blocking)

**Authority**: AI Governance Council  
**Date**: 2025-12-10  
**Scope**: Tier-2.5 Maintenance Missions  
**Status**: Non-Blocking for Tier-2 Certification and Tier-2.5 Activation

---

## Overview

To respect all identified nits while not blocking activation, Council adopts the following non-blocking Fix Plan, to be executed as early Tier-2.5 maintenance missions.

---

## F1 — Artefact Manifest Completeness (Claude – Architect)

**Objective**: Add `runtime/orchestration/config_adapter.py` and `runtime/orchestration/config_test_run.py` explicitly to:
- FP-4.x Implementation Artefact manifest (Section 2.B).

**Classification**: Docs only, non-blocking.

**Priority**: Low  
**Estimated Effort**: Minimal (documentation update)

---

## F2 — API Evolution & Versioning Strategy (Claude – Architect)

**Objective**: Create a short Tier-3-facing document / section:
- Describing versioning for Tier-2 interfaces (e.g. `TestRunResult`, `run_test_run_from_config`).
- Outlining deprecation policy for any future changes.

**Classification**: Governance / Productisation doc, to be completed before large-scale external integrations.

**Priority**: Medium  
**Estimated Effort**: 1-2 hours (new document creation)

---

## F3 — Tier-2.5 Activation Conditions Checklist (Claude – Alignment)

**Objective**: Add a formal checklist to the Tier-2.5 governance doc / CRP addendum, containing at minimum:
- Tier-2 tests = 100% pass.
- All FP-4.x conditions certified.
- No unresolved envelope violations.
- Council approval recorded.
- Rollback procedure documented.

**Classification**: Governance doc, first Tier-2.5 mission.

**Priority**: **High** (required for Tier-2.5 operations)  
**Estimated Effort**: 1 hour (checklist creation)

---

## F4 — Tier-2.5 Deactivation & Rollback Conditions (Claude – Alignment)

**Objective**: Define explicit conditions that trigger downgrading/suspending Tier-2.5:
- Drop in test pass rate.
- Newly detected envelope violation.
- Runtime-to-Antigrav protocol breach.
- Explicit Council HOLD.

**Classification**: Governance doc, coupled with F3.

**Priority**: **High** (required for Tier-2.5 operations)  
**Estimated Effort**: 1 hour (conditions definition)

---

## F5 — Obsolete Comment Removal (Kimi – Risk Secondary)

**Objective**: Remove the outdated "might access time/random" comment from `runtime/tests/test_tier2_daily_loop.py`.

**Classification**: Tiny micro-fix, does not change behaviour.

**Priority**: Low  
**Estimated Effort**: 5 minutes (comment removal)

---

## F6 — Violation Hierarchy Clarification (DeepSeek – Red-Team)

**Objective**: Add a short section / docstring clarifying:
- `AntiFailureViolation` = step-count / human-step constraints.
- `EnvelopeViolation` = illegal step kinds / I/O / forbidden operations.

**Classification**: Docs + readability, non-blocking.

**Priority**: Low  
**Estimated Effort**: 15 minutes (docstring addition)

---

## F7 — Runtime ↔ Antigrav Mission Protocol (DeepSeek – Red-Team, Gemini – Autonomy)

**Objective**: Draft a Tier-2.5 protocol document specifying:
- Which Tier-2 entrypoints Antigrav may call.
- How missions are represented and validated.
- How Anti-Failure and envelope constraints are enforced on Antigrav-originated missions.
- How Council-approved mission whitelists/registries are updated (via Fix Packs only).

**Classification**: Core Tier-2.5 governance spec, to be produced early in Tier-2.5.

**Priority**: **High** (required for Tier-2.5 operations)  
**Estimated Effort**: 2-3 hours (new protocol document)

---

## Execution Order

### Phase 1 — Critical Governance (First Tier-2.5 Missions)
1. **F3** — Activation Conditions Checklist
2. **F4** — Deactivation & Rollback Conditions
3. **F7** — Runtime ↔ Antigrav Mission Protocol

### Phase 2 — Documentation & Cleanup
4. **F2** — API Evolution & Versioning Strategy
5. **F6** — Violation Hierarchy Clarification
6. **F1** — Artefact Manifest Completeness
7. **F5** — Obsolete Comment Removal

---

## Success Criteria

All items F1–F7 are **non-blocking** for Tier-2 certification and Tier-2.5 activation, but are adopted as **binding follow-up work** for Tier-2.5.

Completion of F3, F4, and F7 is required before full-scale Tier-2.5 operations commence.
