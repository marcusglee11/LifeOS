# HANDOFF_PACKET: Recursive Builder Integration (Phase 4)

**From**: Policy Engine Authoritative Gating Thread  
**To**: New Thread (Recursive Builder Integration)  
**Date**: 2026-01-23  
**Status**: READY_FOR_PICKUP

---

## Objective

Wire `recursive_kernel/runner.py` to dispatch `AutonomousBuildCycleMission` from backlog items, enabling CEO-out-of-the-loop autonomous builds.

---

## Context (What Just Happened)

Policy Engine is now **authoritative** in the loop controller:

- `AutonomousBuildCycleMission` loads config from `config/policy/` with `PolicyLoader(authoritative=True)`
- Decisions (retry/terminate/escalate/waiver) are config-driven, not hardcoded
- 8/8 E2E tests validate fail-closed invariants
- Waiver artifact workflow exists (TTL-validated, context-bound)

---

## Key Files

| File | Role |
|------|------|
| `runtime/orchestration/missions/autonomous_build_cycle.py` | Loop controller (now authoritative) |
| `recursive_kernel/runner.py` | Entry point for recursive builds |
| `recursive_kernel/autogate.py` | Auto-gating rules |
| `config/policy/loop_rules.yaml` | Policy rules (retry limits, failure routing) |
| `runtime/orchestration/loop/policy.py` | LoopPolicy + ConfigDrivenLoopPolicy |
| `docs/11_admin/BACKLOG.md` | Source of backlog items |

---

## What Needs to Happen

1. **Parse Backlog**: Extract actionable items from `BACKLOG.md` (or structured source)
2. **Dispatch Mission**: Call `AutonomousBuildCycleMission.run()` with task_spec from backlog item
3. **Handle Outcomes**:
   - PASS → Mark item done in backlog
   - ESCALATION_REQUESTED → Write escalation artifact, halt
   - WAIVER_REQUESTED → Write waiver request, await human grant
4. **Loop**: Move to next backlog item or halt if budget exhausted

---

## Constraints

- **No new architecture** — use existing mission primitives
- **Fail-closed** — any parsing/dispatch error must halt, not silently skip
- **Deterministic** — same backlog + same config → same outcomes
- **Human preservation** — escalations and waivers require human action

---

## Suggested First Steps

1. Read `recursive_kernel/runner.py` to understand current structure
2. Read `docs/11_admin/BACKLOG.md` to understand item format
3. Draft plan: how to parse → dispatch → update cycle
4. Implement minimal viable loop (single item dispatch)
5. Add E2E test: mock backlog → assert mission dispatched

---

## Evidence Pointers (From This Thread)

- `artifacts/signoffs/Policy_Engine_Authoritative_Gating_v0.2/` — E2E evidence bundle
- `runtime/orchestration/loop/waiver_artifact.py` — Waiver boundary module
- `runtime/tests/orchestration/missions/test_policy_engine_authoritative_e2e.py` — 8/8 passing tests

---

📦 **Pickup Path**: `artifacts/packets/HANDOFF_Recursive_Builder_Integration_v0.1.md`
