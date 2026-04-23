---
source_docs:
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/02_protocols/Council_Protocol_v1.3.md
  - docs/02_protocols/Governance_Protocol_v1.0.md
source_commit_max: e1a968bd4087d4cbe5000c04753f66b04a1594f7
authority: derived
page_class: evergreen
concepts:
  - CEO supremacy
  - hard invariants
  - Council
  - governance
  - amendment
---

## Summary

CEO is the sole source of strategic intent; the system amplifies human agency and does
not originate it. Constitution v2.0 (effective 2026-01-01) is the supreme governing
document. All docs, protocols, and agent behaviors must conform to it.

## Key Relationships

- [agent-roles](agent-roles.md) — CEO and COO role definitions
- [target-architecture](target-architecture.md) — operational control-plane under governance
- Source: `docs/00_foundations/LifeOS_Constitution_v2.0.md` — supreme
- Source: `docs/02_protocols/Council_Protocol_v1.3.md` — Council composition and rulings
- Source: `docs/02_protocols/Governance_Protocol_v1.0.md` — governance procedures

## Authority Note

Canonical source: `docs/00_foundations/LifeOS_Constitution_v2.0.md`. That document wins
on any conflict with this page.

## Current Truth

**Hard invariants (non-negotiable):**

| Invariant | Rule |
|-----------|------|
| CEO Supremacy | All strategic intent originates from CEO only |
| Audit Completeness | Every state-changing action must be traceable |
| Reversibility | Prefer reversible actions; gate irreversible ones |
| Amendment Discipline | Constitution changes require Council ratification |

**Guiding principles:** action > paralysis; reversible > irreversible; explicit > implicit;
human-in-loop for high-stakes; safe > fast.

**Protected paths (Council approval required):** `docs/00_foundations/`, `docs/01_governance/`,
`config/governance/protected_artefacts.json`.

## Open Questions

For current operational phase, active workstreams, and WIP status, see
`docs/11_admin/LIFEOS_STATE.md` directly — governance-model.md does not carry volatile state.
