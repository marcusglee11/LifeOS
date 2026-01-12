# Next Build Candidate Packet — Phase 2 v1.1 Successor

**Status:** BLOCKED — Ambiguous next build  
**Date:** 2026-01-08  
**Gate:** Fail-Closed per mission spec  

---

## Context Pack Receipt

| File | SHA256 |
|------|--------|
| [`LIFEOS_STATE.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/11_admin/LIFEOS_STATE.md) | `a73c9c6afb537c8ac21adeffc5c41c2ea638ac0e1672b5666a218cc692181b64` |
| [`LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md) | `08a50ae7331e702215ad131f34e1b55d157e7a745c1869929a79e2fd1a6e822e` |
| [`LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md) | `8e6807b4dfc259b5dee800c2efa2b4ffff3a38d80018b57d9d821c4dfa8387ba` |
| [`Implementation_Plan_Build_Loop_Phase2_v1.1.md`](file:///c:/Users/cabra/Projects/LifeOS/docs/03_runtime/Implementation_Plan_Build_Loop_Phase2_v1.1.md) | `08d740b4b85de015688f31962112cdc2eff58db8bd2943d9567c59fb5f8b88a3` |

---

## Blocking Condition

There are **3 explicit candidate next build items** in the canonical sources with no single unambiguous selection:

| Candidate | Source | Section |
|-----------|--------|---------|
| Build Loop Phase 3: Mission Types | Architecture v0.3 | § 7 "Phase 3: Mission Types (Est. 5-7 days)" |
| F2: API Evolution & Versioning Strategy | LIFEOS_STATE.md | "Next Actions" line 52 |
| Tier-3 CLI Bootstrap (`coo/cli/`) | LIFEOS_STATE.md | "Next Actions" line 53 |

---

## Recommendation: **Build Loop Phase 3 — Mission Types**

### Rationale

1. **Dependency-First Ordering:** The Build Loop Architecture v0.3 § 7 defines explicit phases. Phase 2 (Operations + Run Controller) is complete. Phase 3 (Mission Types) is the documented next sequential step.

2. **Foundation for Autonomy:** Mission Types (`design`, `review`, `build`, `steward`) are prerequisites for the autonomous build cycle. Without them, neither F2 nor Tier-3 CLI can leverage automated orchestration.

3. **Architecture-Documented:** The scope is fully specified in v0.3 § 5.3 with Mission YAML Schema, mission definitions, and exit criteria.

### Alternative: F2 — API Evolution & Versioning Strategy

- **Why it might be next:** Listed first under `[TODO]` in LIFEOS_STATE.md.
- **Why it should wait:** F2 is a design/strategy deliverable, not infrastructure. The Autonomous Build Loop Phase 3 provides the execution machinery that would implement any API versioning strategy.

---

## Acceptance Criteria (if Build Loop Phase 3 selected)

Per Architecture v0.3 § 7 "Phase 3: Mission Types":

| Criterion | Evidence Required |
|-----------|-------------------|
| Mission implementations created | `runtime/orchestration/missions/{design,review,build,steward}.py` |
| `autonomous_build_cycle` composes correctly | Integration test showing step sequencing |
| Mission YAML schema validation added | Unit tests for schema validation |
| ANY seat rejection escalates to CEO | Test case demonstrating escalation |
| Steward guarantees repo clean on exit | Test case demonstrating clean state |
| All unit tests pass | `pytest runtime/tests/ -q` output PASS |

---

## What is Missing to Proceed

1. **CEO explicit selection** of ONE candidate from the 3 above.
2. If Phase 3 selected: **Confirmation of scope boundary** (e.g., mock builders vs. OpenCode integration).

---

## Fail-Closed Compliance

Per mission spec § E: "If the next build cannot be determined unambiguously from repo sources: BLOCK (do not implement anything) and return the Candidate Packet + missing inputs."

**This packet satisfies that requirement.**

---

**END OF PACKET**
