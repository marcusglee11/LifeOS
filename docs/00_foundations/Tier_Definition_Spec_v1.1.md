# Tier Definition Specification v1.1

**Status**: Active  
**Authority**: LifeOS Constitution v2.0  
**Effective**: 2026-01-07

---

## 1. Purpose

Defines the tier progression model for LifeOS: what each tier means, entry/exit criteria, and capabilities.

---

## 2. Definitions

**Envelope**: The set of invariant constraints that bound Tier-2 execution. Specifically: no I/O, no system time access, no randomness, deterministic outputs. Code operating within the envelope produces identical outputs for identical inputs.

**Mission**: A discrete unit of autonomous work executed by an agent (e.g., run tests, regenerate corpus, commit changes). A mission cycle is one complete execution from invocation through result logging.

**Council**: The review body for tier progression decisions. Composition and procedures defined in Governance_Protocol_v1.0.

---

## 3. Tier Overview

| Tier | Name | Summary |
|------|------|---------|
| **Tier-1** | Foundation | Core infrastructure, hardened invariants |
| **Tier-2** | Deterministic Core | Orchestrator, Builder, Envelope-pure execution |
| **Tier-2.5** | Governance Mode | Agent-driven maintenance with human oversight |
| **Tier-3** | Productisation | CLI, Config, User Surfaces |
| **Tier-4** | Autonomy (Future) | Bounded autonomous operation |

---

## 4. Tier-1: Foundation

### 4.1 Scope

- Runtime scaffolding
- Test infrastructure
- Governance document framework
- Basic envelope enforcement

### 4.2 Entry Criteria

- Initial repo setup
- Constitution ratified

### 4.3 Exit Criteria

- Core test suite passing
- Envelope constraints defined
- Governance protocols v1.0 in place

### 4.4 Status

**COMPLETE**

---

## 5. Tier-2: Deterministic Core

### 5.1 Scope

- `runtime/orchestration/` — Orchestrator, Builder, Daily Loop
- `runtime/mission/` — Mission Registry
- Deterministic execution with no I/O, time, randomness

### 5.2 Entry Criteria

- Tier-1 complete
- Envelope invariants codified

### 5.3 Exit Criteria

- All Tier-2 tests green
- Hash-level determinism proven
- Council ruling: CERTIFIED

### 5.4 Status

**COMPLETE** per [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](../01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md)

---

## 6. Tier-2.5: Governance Mode

### 6.1 Scope

- Agent (Antigravity) executes deterministic missions
- Human role elevated to intent/approval/veto
- No new code paths; governance-layer activation

### 6.2 Entry Criteria

- Tier-2 certified
- Activation conditions defined per [F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md](../03_runtime/F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md)
- Deactivation conditions defined per [F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md](../03_runtime/F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md)
- Runtime ↔ Agent protocol defined per [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](../03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md)

### 6.3 Exit Criteria

- Stable operation demonstrated
- No unresolved envelope violations
- Rollback not triggered
- Council ruling: CERTIFIED

### 6.4 Status

**ACTIVE** per Council ruling

---

## 7. Tier-3: Productisation

### 7.1 Scope

- CLI interfaces
- Config loader
- User surface components
- External integrations

### 7.2 Entry Criteria

- Tier-2.5 stable
- API evolution strategy defined

### 7.3 Exit Criteria

- User-facing surfaces operational
- Documentation complete
- Onboarding path defined
- Council ruling: CERTIFIED

### 7.4 Status

**AUTHORIZED TO BEGIN**

---

## 8. Tier-4: Autonomy (Future)

### 8.1 Scope

- Bounded autonomous operation
- Self-improvement within envelope
- Reduced human intervention

### 8.2 Entry Criteria

- Tier-3 stable
- Safety envelope proven
- CEO authorization

### 8.3 Exit Criteria

- TBD (to be defined before Tier-4 entry)

### 8.4 Status

**NOT STARTED**

---

## 9. Progression Rules

1. **Sequential**: Tiers must be completed in order
2. **Certified**: Each tier requires Council ruling to exit
3. **Reversible**: Rollback to prior tier permitted (see §10)
4. **Evidence-Based**: Progression requires test suite + Council ruling

---

## 10. Rollback Procedure

### 10.1 Authority

CEO may declare rollback at any time for any reason.

### 10.2 Mechanism

1. CEO declares rollback, specifying target tier
2. Declaration logged to DECISIONS.md with rationale
3. System reverts to target tier's operational constraints
4. Re-certification required to progress again

### 10.3 Effect

During rollback, operations are constrained to the target tier's boundaries until a new Council ruling certifies progression.

---

## 11. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-07 | CEO + Claude | Initial canonical release. Resolved gaps: added definitions (Envelope, Mission, Council), explicit F3/F4/F7 links, rollback procedure, Tier-1/Tier-4 status. |

---

**END OF SPECIFICATION**
