---
source_docs:
  - docs/02_protocols/Git_Workflow_Protocol_v1.1.md
  - docs/02_protocols/Build_Handoff_Protocol_v1.1.md
source_commit_max: df4bb54bba3a499ef8a41f4ccb711e1f59862820
authority: derived
page_class: evergreen
concepts:
  - worktree isolation
  - branch naming
  - build lifecycle
  - handoff
  - sprint isolation
---

## Summary

All LifeOS builds run in isolated git worktrees — never in the primary repo. This is a
hard gate, not guidance. The `Git_Workflow_Protocol_v1.1.md` defines enforced invariants
for branch naming, merge gating, and CI proof. Handoff semantics are defined by
`Build_Handoff_Protocol_v1.1.md`.

## Key Relationships

- [agent-roles](agent-roles.md) — sprint agent role (EA)
- [doc-stewardship](doc-stewardship.md) — stewardship gates in close-build
- Source: `docs/02_protocols/Git_Workflow_Protocol_v1.1.md` — branch, merge, CI invariants
- Source: `docs/02_protocols/Build_Handoff_Protocol_v1.1.md` — handoff messaging

## Authority Note

Canonical source: `docs/02_protocols/Git_Workflow_Protocol_v1.1.md`. That document wins
on any conflict. Implementation-level build scripts and Article XIX hook details are in
`CLAUDE.md` (operational rules) which agents read directly.

## Current Truth

**Branch naming (enforced by tooling):**

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `build/<topic>` | `build/coo-control-plane` |
| Fix | `fix/<issue>` | `fix/test-failures` |
| Hotfix | `hotfix/<issue>` | `hotfix/ci-regression` |
| Spike | `spike/<topic>` | `spike/new-executor` |

Never commit directly on `main`.

**Build lifecycle:** start (`python3 scripts/workflow/start_build.py <topic>`) → work in
worktree → tests + quality gate → close (`python3 scripts/workflow/close_build.py`).

**Handoff semantics:** `Build_Handoff_Protocol_v1.1.md` defines the packetized handoff
architecture — CONTEXT_REQUEST / CONTEXT_RESPONSE / HANDOFF_PACKET types, evidence requirements,
and artifact bundling at `artifacts/for_ceo/`.

## Open Questions

None.
