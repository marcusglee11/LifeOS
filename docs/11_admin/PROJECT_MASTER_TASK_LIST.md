> [!NOTE]
> **STATUS**: Non-Canonical (Information Only). This document is provided for context and architectural reference but is not an authoritative specification.

# LifeOS Project Master Task List

**Last Updated:** 2026-01-28 00:20 AEDT  
**Maintained By:** Clawd (COO/CSO)  
**Source:** BACKLOG.md + LIFEOS_STATE.md + Deep Dive Findings

---

## Summary

**Total Tasks:** 52  
**Completed:** 28 (54%)  
**In Progress:** 2 (4%)  
**Todo:** 19 (37%)  
**Blocked:** 3 (6%)

**By Priority:**
- **P0 (Critical):** 11 (21%)
- **P1 (High):** 28 (54%)
- **P2 (Medium):** 13 (25%)

---

## P0 — Critical (Blocking Progress)

### Phase Management
- [ ] **P0-001: Complete Phase 3 Closure** — Owner: boss — Status: TODO — Blocking: Phase 4 entry — Notes: Ratified with conditions, need final CEO sign-off
- [ ] **P0-002: Enter Phase 4 (Planning Stage)** — Owner: boss — Status: BLOCKED — Dependencies: P0-001 — Notes: Pre-req (Trusted Builder v1.1) complete

### Council Agent Build (NEW — CEO Approved 2026-01-27)
- [ ] **P0-010: Council Agent Design v1.0** — Owner: clawd — Status: IN PROGRESS (40%) — Est: 1 day — Notes: Draft started, CEO Q1-Q4 pending
- [ ] **P0-011: Council Agent MVP (M0_FAST)** — Owner: clawd — Status: TODO — Dependencies: P0-010 — Est: 2 days — DoD: Single unified reviewer working
- [ ] **P0-012: Council Agent M1_STANDARD** — Owner: clawd — Status: TODO — Dependencies: P0-011 — Est: 2 days — DoD: Multi-seat, single model
- [ ] **P0-013: Council Agent M2_FULL** — Owner: clawd — Status: TODO — Dependencies: P0-012 — Est: 1 day — DoD: Independent models, full 9 seats
- [ ] **P0-014: Council Agent CLI Integration** — Owner: clawd — Status: TODO — Dependencies: P0-013 — Est: 0.5 days — DoD: `lifeos council` command works
- [ ] **P0-015: Council Agent Production Deployment** — Owner: clawd — Status: TODO — Dependencies: P0-014 — Est: 0.5 days — DoD: CEO exits waterboy mode

### Historical (Completed)
- [x] **P0-000: E2E Test Runtime Greet** — Owner: antigravity — Status: DONE — Date: 2026-01-XX — DoD: runtime/greet.py committed

---

## P1 — High Priority

### Trusted Builder Enhancements
- [ ] **P1-001: Ledger Hash Chain** — Owner: antigravity — Status: TODO — Context: Trusted Builder v1.1 deferred — DoD: Tamper-proof bypass record linking
- [ ] **P1-002: Bypass Monitoring** — Owner: antigravity — Status: TODO — Context: Trusted Builder v1.1 deferred — DoD: Alerting on high bypass utilization
- [ ] **P1-003: Semantic Guardrails** — Owner: antigravity — Status: TODO — Context: Trusted Builder v1.1 deferred — DoD: Heuristics for meaningful changes

### Recursive Builder Iteration (Phase B)
- [ ] **P1-010: Recursive Builder Phase B** — Owner: antigravity — Status: TODO — Notes: Immediate focus (Refinement & Automation)
- [ ] **P1-011: B1 — Strengthen smoke_check evidence** — Owner: antigravity — Status: TODO — DoD: Test computes sha256 of smoke_check.stderr
- [ ] **P1-012: B2 — Tighten validation exception specificity** — Owner: antigravity — Status: TODO — DoD: Tests assert exact exception type
- [ ] **P1-013: B3 — Clarify fail-closed filesystem boundary** — Owner: antigravity — Status: TODO — DoD: Documented boundary + consistent behavior

### Documentation Finalization
- [ ] **P1-020: Finalize Emergency_Declaration_Protocol v1.0** — Owner: antigravity — Status: TODO — DoD: Markers removed
- [ ] **P1-021: Finalize Intent_Routing_Rule v1.0** — Owner: antigravity — Status: TODO — DoD: Markers removed
- [ ] **P1-022: Finalize Test_Protocol v2.0** — Owner: antigravity — Status: TODO — DoD: Markers removed
- [ ] **P1-023: Finalize Tier_Definition_Spec v1.1** — Owner: antigravity — Status: TODO — DoD: Markers removed
- [ ] **P1-024: Finalize ARTEFACT_INDEX_SCHEMA v1.0** — Owner: antigravity — Status: TODO — DoD: Markers removed
- [ ] **P1-025: Finalize QUICKSTART v1.0** — Owner: antigravity — Status: TODO — DoD: Context scan pass complete

### COO/CSO Project Management (NEW)
- [ ] **P1-030: Documentation Status Audit** — Owner: clawd — Status: TODO — Est: 2 days — DoD: 18+ draft docs promoted/archived/completed
- [ ] **P1-031: Test Suite Fixes** — Owner: clawd — Status: IN PROGRESS — Est: 2 days — Notes: 92/97 passing (+1 from config fix), 6 remaining
- [ ] **P1-032: Orchestrator Agent Design** — Owner: clawd — Status: BLOCKED — Dependencies: P0-015 — Est: 3 days — Notes: Manager-Led pattern, deferred until Council complete
- [ ] **P1-033: Orchestrator Agent Build** — Owner: clawd — Status: BLOCKED — Dependencies: P1-032 — Est: 3 days — DoD: Dispatch Designer→Builder→Council workflows

### Historical (Completed)
- [x] **P1-000: Complete Deferred Evidence F3/F4/F7** — Owner: antigravity — Status: DONE — Date: 2026-01-23 — Context: Phase 3 closure conditions

---

## P2 — Medium Priority

### Architecture & Planning
- [ ] **P2-001: Mission Type Extensions** — Owner: antigravity — Status: TODO — Notes: Add new mission types based on backlog needs
- [ ] **P2-002: Integration Testing** — Owner: antigravity — Status: TODO — Notes: Comprehensive end-to-end testing
- [ ] **P2-003: Tier-3 Planning** — Owner: antigravity — Status: TODO — Notes: Scope Tier-3 Autonomous Construction Layer

### Reactive Layer Hygiene
- [ ] **P2-010: Tighten Canonical JSON** — Owner: antigravity — Status: TODO — DoD: Require explicit escape sequence for non-ASCII input
- [ ] **P2-011: Verify README Authority Pointer** — Owner: antigravity — Status: TODO — DoD: Ensure stable canonical link to authority anchor

### Tech Debt
- [ ] **P2-020: Rehabilitate Legacy Git Workflow Tests** — Owner: antigravity — Status: TODO — Context: Quarantined to archive_legacy_r6x, missing run_cmd mock
- [ ] **P2-021: LIFEOS_TODO Inventory** — Owner: clawd — Status: TODO — Est: 0.5 days — DoD: All TODOs tracked in BACKLOG
- [ ] **P2-022: Fix Timestamp Placeholders** — Owner: clawd — Status: TODO — Est: 0.5 days — DoD: YYYY-MM-DD replaced, script created
- [ ] **P2-023: Audit Multi-Version Protocols** — Owner: doc_steward — Status: TODO — Est: 1 day — DoD: Superseded versions archived

### Future / Exploratory
- [ ] **P2-100: Fuel Track Exploration** — Owner: TBD — Status: LATER — Notes: Not blocking Core; future consideration
- [ ] **P2-101: Productisation of Tier-1/Tier-2 Engine** — Owner: TBD — Status: LATER — Dependencies: Core stabilisation

---

## Completed (Last 30 Days)

### 2026-01-27
- [x] **Read and map LifeOS architecture** — Owner: clawd — Date: 2026-01-27 — Context: COO/CSO onboarding
- [x] **Find F3/F4/F7 specs** — Owner: clawd — Date: 2026-01-27 — Context: Located in docs/03_runtime/
- [x] **Map current agent handoff flows** — Owner: clawd — Date: 2026-01-27 — Context: Deep dive analysis
- [x] **Tool acquisition (web search)** — Owner: clawd — Date: 2026-01-27 — Context: Configured Perplexity via OpenRouter

### 2026-01-26
- [x] **Trusted Builder Mode v1.1 Ratified** — Owner: boss — Date: 2026-01-26 — Context: Council Ruling, Phase 4 pre-req

### 2026-01-23
- [x] **Finalize CSO_Role_Constitution v1.0** — Owner: antigravity — Date: 2026-01-23 — DoD: Waiver W1 removed
- [x] **Standardize Raw Capture Primitive** — Owner: antigravity — Date: 2026-01-18 — DoD: Evidence Capture v0.1

### 2026-01-16 - 2026-01-18
- [x] **Git Workflow Protocol v1.1 Impact** — Owner: antigravity — Date: 2026-01-16 — Context: OpenCode deletion logic via Safety Gate
- [x] **Grok Fallback Debug & Robustness Fixes v1.0** — Date: 2026-01-18

### 2026-01-13
- [x] **BuildWithValidation v0.1 P0 Patch 2 Refinement** — Date: 2026-01-13
- [x] **Fix OpenCode Config Compliance v1.0** — Date: 2026-01-13
- [x] **CLI & Mission Hardening v1.0** — Date: 2026-01-13
- [x] **Tier-3 CLI Integration (Full)** — Date: 2026-01-13
- [x] **BuildWithValidation Mission Hardening v0.1** — Date: 2026-01-13
- [x] **BuildWithValidation Mission Type v0.1** — Date: 2026-01-13
- [x] **Tier-3 Mission Dispatch Wiring Fixes v1.0** — Date: 2026-01-13
- [x] **CI Regression Fixes v1.0** — Date: 2026-01-13
- [x] **OpenCode Sandbox Activation v2.2** — Date: 2026-01-13

### 2026-01-11 - 2026-01-12
- [x] **A1/A2 Re-closure v2.1c** — Date: 2026-01-12
- [x] **G-CBS Readiness v1.1** — Date: 2026-01-11

### 2026-01-02 - 2026-01-03
- [x] **F3 — Tier-2.5 Activation Conditions Checklist** — Date: 2026-01-02
- [x] **F4 — Tier-2.5 Deactivation & Rollback Conditions** — Date: 2026-01-02
- [x] **F7 — Runtime ↔ Antigrav Mission Protocol** — Date: 2026-01-02
- [x] **Strategic Context Generator v1.3** — Date: 2026-01-03
- [x] **Agent Packet Protocol v1.0** — Date: 2026-01-02

---

## Critical Path Analysis

**Phase 4 Entry:**
```
P0-001 (Phase 3 Closure) → P0-002 (Phase 4 Entry)
```

**Council Agent (Exit Waterboy Mode):**
```
P0-010 (Design) → P0-011 (MVP) → P0-012 (M1) → P0-013 (M2) → P0-014 (CLI) → P0-015 (Production)
```

**Orchestrator Agent (Full Autonomous Operation):**
```
P0-015 (Council complete) → P1-032 (Design) → P1-033 (Build)
```

**Estimated Timeline:**
- Council Agent: 6.5 days (design → production)
- Orchestrator Agent: 6 days (after Council)
- **Total to Rung 2 (Supervised Chains):** ~12-13 days

---

## Dependency Matrix

| Task | Blocks | Blocked By |
|------|--------|-----------|
| P0-001 | P0-002 | — |
| P0-010 | P0-011 | — |
| P0-011 | P0-012 | P0-010 |
| P0-012 | P0-013 | P0-011 |
| P0-013 | P0-014 | P0-012 |
| P0-014 | P0-015 | P0-013 |
| P0-015 | P1-032 | P0-014 |
| P1-032 | P1-033 | P0-015 |
| P1-031 | — | — |
| P1-030 | — | — |

---

## Resource Allocation

### Clawd (COO/CSO)
**Primary:** Council Agent (P0-010 through P0-015)  
**Secondary:** Project admin, test fixes, doc audit  
**Capacity:** ~8 hours/day

### Antigravity
**Primary:** Trusted Builder enhancements, Recursive Builder Phase B  
**Secondary:** Documentation finalization  
**Status:** Available for assigned work

### Boss (CEO)
**Required For:**
- P0-001: Phase 3 closure sign-off
- P0-010: Council Agent design Q1-Q4 decisions
- Strategic decisions as escalated

---

## Next 7 Days (Focus)

### This Week (2026-01-28 to 2026-02-03)

**Day 1-2 (Mon-Tue):**
- Complete P0-010 (Council Agent Design)
- Build P0-011 (MVP M0_FAST)
- Continue P1-031 (Test fixes)

**Day 3-4 (Wed-Thu):**
- Build P0-012 (M1_STANDARD)
- Start P0-013 (M2_FULL)
- P1-030 (Doc audit report)

**Day 5-7 (Fri-Sun):**
- Complete P0-013 (M2_FULL)
- P0-014 (CLI integration)
- P0-015 (Production deployment)
- **Milestone:** CEO exits waterboy mode

---

## Risk Register

| Risk | Impact | Probability | Mitigation | Owner |
|------|--------|-------------|------------|-------|
| Council Agent complexity exceeds estimate | High | Medium | Modal implementation (start M0), incremental delivery | Clawd |
| Phase 3 closure delays Phase 4 | High | Low | Council Agent not blocked by Phase 4 entry | Boss |
| Test suite issues block CI | Medium | Low | Fix in parallel, non-blocking for Council | Clawd |
| CEO bandwidth for Q1-Q4 decisions | Low | Medium | Provide defaults, refine later | Clawd |
| Orchestrator scope creep | Medium | Medium | Clear design, bounded by Council learnings | Clawd |

---

**Maintained in:** `/home/cabra/clawd/lifeos/docs/11_admin/PROJECT_MASTER_TASK_LIST.md`  
**Next Review:** Daily (automated heartbeat)  
**Change Log:** Track all additions/completions
