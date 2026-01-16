# Tier Definition Specification v1.0

**Status**: WIP (Non-Canonical)  
**Authority**: LifeOS Constitution v2.0  
**Effective**: 2026-01-07 (Provisional)

---

## 1. Purpose

Defines the tier progression model for LifeOS: what each tier means, entry/exit criteria, and capabilities.

---

## 2. Tier Overview

| Tier | Name | Summary |
|------|------|---------|
| **Tier-1** | Foundation | Core infrastructure, hardened invariants |
| **Tier-2** | Deterministic Core | Orchestrator, Builder, Envelope-pure execution |
| **Tier-2.5** | Governance Mode | Agent-driven maintenance with human oversight |
| **Tier-3** | Productisation | CLI, Config, User Surfaces |
| **Tier-4** | Autonomy (Future) | Bounded autonomous operation |

---

## 3. Tier-1: Foundation

### 3.1 Scope
- Runtime scaffolding
- Test infrastructure
- Governance document framework
- Basic envelope enforcement

### 3.2 Entry Criteria
- Initial repo setup
- Constitution ratified

### 3.3 Exit Criteria
- Core test suite passing
- Envelope constraints defined
- Governance protocols v1.0 in place

---

## 4. Tier-2: Deterministic Core

### 4.1 Scope
- `runtime/orchestration/` — Orchestrator, Builder, Daily Loop
- `runtime/mission/` — Mission Registry
- Deterministic execution with no I/O, time, randomness

### 4.2 Entry Criteria
- Tier-1 complete
- Envelope invariants codified

### 4.3 Exit Criteria
- All Tier-2 tests green
- Hash-level determinism proven
- Council ruling: CERTIFIED

### 4.4 Status
**COMPLETE** per [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](../01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md)

---

## 5. Tier-2.5: Governance Mode

### 5.1 Scope
- Agent (Antigravity) executes deterministic missions
- Human role elevated to intent/approval/veto
- No new code paths; governance-layer activation

### 5.2 Entry Criteria
- Tier-2 certified
- Activation/Deactivation conditions defined (F3/F4)
- Runtime ↔ Antigrav protocol defined (F7)

### 5.3 Exit Criteria
- Stable operation for N mission cycles
- No envelope violations
- Rollback not triggered

### 5.4 Status
**ACTIVE** per Council ruling

---

## 6. Tier-3: Productisation

### 6.1 Scope
- CLI interfaces
- Config loader
- User surface components
- External integrations

### 6.2 Entry Criteria
- Tier-2.5 stable
- API evolution strategy defined

### 6.3 Exit Criteria
- User-facing surfaces operational
- Documentation complete
- Onboarding path defined

### 6.4 Status
**AUTHORIZED TO BEGIN**

---

## 7. Tier-4: Autonomy (Future)

### 7.1 Scope
- Bounded autonomous operation
- Self-improvement within envelope
- Reduced human intervention

### 7.2 Entry Criteria
- Tier-3 stable
- Safety envelope proven
- Council and CSO confidence threshold met

---

## 8. Progression Rules

1. **Sequential**: Tiers must be completed in order
2. **Certified**: Each tier requires Council ruling to exit
3. **Reversible**: Rollback to prior tier on safety trigger
4. **Evidence-Based**: Progression requires test suite + ruling

---

**END OF SPECIFICATION**
