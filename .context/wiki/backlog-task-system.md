---
source_docs:
  - docs/11_admin/LIFEOS_STATE.md
  - docs/11_admin/BACKLOG.md
  - docs/02_protocols/Intent_Routing_Rule_v1.1.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: 560164c7180b5ce4e0e4ed7f6a0fe47407554ff8
derived_edit_mode: generated
source_command: python3 scripts/wiki/refresh_wiki.py
source_change_ref: https://github.com/marcusglee11/LifeOS/issues/120
authority: derived
page_class: status
concepts:
  - backlog
  - task proposal
  - delegation
  - COO workflow
---

## Summary

The COO reviews canonical backlog/state docs, proposes bounded tasks, and routes approved work to build or stewardship lanes. `docs/11_admin/LIFEOS_STATE.md` remains the canonical current-state surface; `docs/11_admin/BACKLOG.md` is the backlog summary view, not a replacement for live issue/PR readback.

## Key Relationships

- [agent-roles](agent-roles.md) — COO autonomy levels that govern proposal routing
- [openclaw-integration](openclaw-integration.md) — how COO proposals are invoked
- [governance-model](governance-model.md) — CEO approval authority
- Source: `docs/11_admin/LIFEOS_STATE.md` — current phase and WIP (volatile)
- Source: `docs/11_admin/BACKLOG.md` — prioritized work items
- Source: `docs/02_protocols/Intent_Routing_Rule_v1.1.md` — routing and autonomy rules

## Authority Note

Canonical sources: `docs/11_admin/LIFEOS_STATE.md` for current operating state and `docs/11_admin/BACKLOG.md` for backlog orientation. This wiki page is derived and compact; it must not be used as completion, dispatch, or closure truth.

## Current Truth

**Proposal flow:**
1. COO reads current state/backlog and GitHub issue evidence.
2. CEO or governing policy approves the next bounded action when required.
3. Build/stewardship work runs in isolated branches or worktrees.
4. Completion requires PR/issue/check/readback evidence, not wiki text.

**Routing guard:** low-risk, reversible work may proceed under existing autonomy rules; CEO-level decisions still include canon promotion, financial/billing changes, external/public commitments, or irreversible operational changes.

**Doc reconciliation note:** after issue #154, bus/hub/runtime documentation truth is split across LifeOS canonical docs, the operational bus issue/PR receipts, and hub accounting docs. The wiki only points to those sources.

## Open Questions

For current active phase, blockers, and WIP, read `docs/11_admin/LIFEOS_STATE.md` and live GitHub issue/PR state directly.
