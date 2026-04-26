---
source_docs:
  - docs/02_protocols/Document_Steward_Protocol_v1.1.md
  - docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: bf4d9ecd01e5124584e96a42b95f16c7f39e3fd2
authority: derived
page_class: evergreen
concepts:
  - DAP
  - doc_steward
  - freshness
  - index consistency
  - document stewardship
---

## Summary

Document stewardship is agent-owned, not human-operated. The `doc_steward` CLI validates
naming, link integrity, index consistency, and freshness. The source of truth is the local
`docs/` directory; GitHub and Google Drive are sync targets.

## Key Relationships

- [governance-model](governance-model.md) — protected paths requiring Council approval
- [build-workflow](build-workflow.md) — stewardship gates in close-build
- Source: `docs/02_protocols/Document_Steward_Protocol_v1.1.md` — canonical stewardship protocol
- Source: `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md` — DAP validation
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md` — canonical target architecture

## Authority Note

Canonical source: `docs/02_protocols/Document_Steward_Protocol_v1.1.md`. That document
wins on any conflict with this page.

## Current Truth

**Stewardship flow:** doc_steward CLI owns file creation, indexing, git operations, and
syncing. CEO approves intent only; never manually shuffles files or updates indices.

**doc_steward CLI commands:** `dap-validate`, `index-check`, `link-check`, `freshness-check`,
`admin-structure-check`, `protocols-structure-check`, `wiki-lint`.

**Stewardship ledger:** all runs recorded at `artifacts/ledger/dl_doc/YYYY-MM-DD_<type>_<case_id>.yaml`.

**Protected paths:** `docs/00_foundations/` and `docs/01_governance/` require Council
approval (pre-commit hook: `scripts/claude_doc_stewardship_gate.py`).

## Open Questions

> [!CONFLICT] `docs/02_protocols/Document_Steward_Protocol_v1.1.md` (Section 5) states
> Google Drive sync is **bidirectional** via Google Drive for Desktop. However,
> `docs/00_foundations/LifeOS Target Architecture v2.3c.md` (Section 2.7) explicitly states
> Drive is a **read-only mirror for human consumption** and sync is **one-directional:
> GitHub → Drive**. v2.3c is the current canonical target architecture and takes precedence.
> `Document_Steward_Protocol_v1.1.md` Section 5 requires updating to align with v2.3c.
> Until updated, agents should treat Drive as a read-only output target, not a source.
