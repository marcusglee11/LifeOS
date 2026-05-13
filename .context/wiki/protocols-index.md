---
source_docs:
  - docs/INDEX.md
source_commit_max: d1f67f466388b92d820f83aa1e6334582ec7e187
derived_edit_mode: generated
source_command: python3 scripts/wiki/refresh_wiki.py
source_change_ref: https://github.com/marcusglee11/LifeOS/issues/120
authority: derived
page_class: evergreen
concepts:
  - protocols
  - index
  - cross-reference
---

## Summary

Navigation index of active protocols and protocol-adjacent surfaces in `docs/02_protocols/` and related meta docs. This page is a compact pointer only; it does not duplicate protocol text.

## Key Relationships

- [governance-model](governance-model.md) — constitutional authority for protocols
- [doc-stewardship](doc-stewardship.md) — document stewardship protocol
- [build-workflow](build-workflow.md) — Git and build protocols
- [home](home.md) — wiki navigation and authority caveats
- Source: `docs/INDEX.md` — authoritative protocol listing

## Authority Note

Canonical source: `docs/INDEX.md`. That document wins on any conflict with this page. Protocol versions and existence are determined by `docs/INDEX.md` and the actual files present under `docs/**`, not this wiki page.

## Current Truth

Key active protocol families and adjacent navigation surfaces include:

| Area | Canonical source |
|----------|---------|
| Build handoff, Git workflow, test discipline, and DAP | `docs/02_protocols/` |
| Council, governance, emergency, intent routing, and planning rules | `docs/02_protocols/` |
| OpenClaw COO integration and API/versioning boundaries | `docs/02_protocols/` |
| Work-management and workstream context | `docs/02_protocols/Work_Management_Framework_v0.1.md`, `docs/02_protocols/workstream_context_v1.md` |
| Architecture authority and reconciliation packets | `docs/10_meta/` |
| Current operational state | `docs/11_admin/LIFEOS_STATE.md` |

For packet schemas, templates, operational guides, and architecture decisions, use `docs/INDEX.md` as the canonical navigation layer.

## Open Questions

None.
