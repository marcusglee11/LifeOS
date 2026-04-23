---
source_docs:
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/02_protocols/Council_Protocol_v1.3.md
  - docs/02_protocols/Governance_Protocol_v1.0.md
last_updated: bf4d9ecd
concepts:
  - CEO supremacy
  - hard invariants
  - Council
  - governance
  - amendment
---

# Governance Model

## Summary

LifeOS is a CEO augmentation system: the CEO is the sole source of strategic
intent and ultimate authority. The system amplifies human agency — it does not
originate intent. The Constitution v2.0 (effective 2026-01-01) is the supreme
governing document; all other docs and agent behaviors must conform to it.

## Key Relationships

- **CEO** — sole authority; all non-reversible actions require explicit CEO authorization. See [agent-roles](agent-roles.md).
- **Council** — multi-agent deliberative body; governs amendment and policy changes. See [protocols-index](protocols-index.md) → `Council_Protocol_v1.3.md`.
- **Protected paths** — `docs/00_foundations/` and `docs/01_governance/` require Council approval to modify.
- **Hard invariants** — non-negotiable, detectable; any violation is a system fault.

## Hard Invariants

| Invariant | Meaning |
|-----------|---------|
| CEO Supremacy | CEO intent overrides all agent decisions |
| Audit Completeness | All actions must be logged and traceable |
| Reversibility | Prefer reversible actions; irreversible requires CEO authorization |
| Amendment Discipline | All amendments logged with rationale; emergency amendments reviewed within 30d |

## Guiding Principles (interpretive, not absolute)

- Prefer action over paralysis
- Reversible over irreversible
- External outcomes over internal elegance
- Automation over human labor
- Transparency over opacity

## Current State

Constitution v2.0 active since 2026-01-01. Council protocol at v1.3.
Phase 7 (`prod_ci`) is the current active phase; Phase 9 ratification complete
(`workspace_mutation_v1` approved). See [backlog-task-system](backlog-task-system.md).

## Open Questions

None currently flagged.
