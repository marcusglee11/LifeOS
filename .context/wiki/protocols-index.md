---
source_docs:
  - docs/INDEX.md
source_commit_max: 87cddf2ce4f3e3d70319f26a03de0c9ccfd72c04
authority: derived
page_class: evergreen
concepts:
  - protocols
  - index
  - cross-reference
---

## Summary

Navigation index of active protocols in `docs/02_protocols/`. This page is a navigation
aid only — it does not duplicate protocol content. For full protocol text, read the source
docs directly.

## Key Relationships

- [governance-model](governance-model.md) — constitutional authority for protocols
- [doc-stewardship](doc-stewardship.md) — document stewardship protocol
- [build-workflow](build-workflow.md) — Git and build protocols
- Source: `docs/INDEX.md` — authoritative protocol listing

## Authority Note

Canonical source: `docs/INDEX.md`. That document wins on any conflict with this page.
Protocol versions and existence are determined by `docs/INDEX.md` and the actual files
present in `docs/02_protocols/` — not by this wiki page.

## Current Truth

Key active protocols (see `docs/INDEX.md` for full list):

| Protocol | Concern |
|----------|---------|
| `Build_Handoff_Protocol_v1.1.md` | Agent-to-agent handoff messaging |
| `Document_Steward_Protocol_v1.1.md` | Document creation, indexing, sync |
| `Git_Workflow_Protocol_v1.1.md` | Branch, merge, and commit invariants |
| `Council_Protocol_v1.3.md` | Council composition and rulings |
| `Governance_Protocol_v1.0.md` | Governance procedures |
| `Deterministic_Artefact_Protocol_v2.0.md` | DAP validation |
| `Build_Artifact_Protocol_v1.0.md` | Formal schemas/templates for build artifacts |
| `Intent_Routing_Rule_v1.1.md` | COO agent routing decisions |
| `LifeOS_Design_Principles_Protocol_v1.1.md` | "Prove then Harden" development principles |
| `Emergency_Declaration_Protocol_v1.0.md` | Emergency override and auto-revert |
| `Test_Protocol_v2.0.md` | TDD and test design standards |
| `EOL_Policy_v1.0.md` | End-of-life handling for docs |
| `Project_Planning_Protocol_v1.0.md` | Build mission plan requirements and review |
| `OpenClaw_COO_Integration_v1.0.md` | OpenClaw gateway invocation and constraints |
| `Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md` | Tier-2 API versioning, deprecation, compatibility |
| `Filesystem_Error_Boundary_Protocol_v1.0.md` | Fail-closed filesystem error boundaries (Draft) |
| `GitHub_Actions_Secrets_Setup.md` | PAT creation, secrets config, and rotation for CI |

For packet schemas, templates, and operational guides, see subdirectories under `docs/02_protocols/`.

## Open Questions

None.
