---
source_docs:
  - docs/02_protocols/
  - docs/INDEX.md
last_updated: bf4d9ecd
concepts:
  - protocols
  - index
  - cross-reference
---

# Protocols Index

## Summary

Cross-reference of all active protocols in `docs/02_protocols/`. This page
is a navigation aid for agents — it does not duplicate protocol content.
Each entry links to the source doc and notes the primary concern.

## Active Protocols

| Protocol | File | Primary Concern |
|----------|------|----------------|
| AI Council Procedural | `AI_Council_Procedural_Spec_v1.1.md` | Council decision FSM, quorum, voting |
| Build Artifact | `Build_Artifact_Protocol_v1.0.md` | Artifact packaging standards |
| Build Handoff | `Build_Handoff_Protocol_v1.1.md` | Inter-agent handoff structure |
| Core TDD Design | `Core_TDD_Design_Principles_v1.0.md` | TDD rules for all builds |
| Council Context Pack | `Council_Context_Pack_Schema_v0.3.md` | Council packet schema |
| Council Protocol | `Council_Protocol_v1.3.md` | Full Council decision process |
| DAP (Deterministic Artefact) | `Deterministic_Artefact_Protocol_v2.0.md` | File naming, versioning |
| Document Steward | `Document_Steward_Protocol_v1.1.md` | Doc operations, sync, index |
| Emergency Declaration | `Emergency_Declaration_Protocol_v1.0.md` | Emergency override procedure |
| EOL Policy | `EOL_Policy_v1.0.md` | End-of-line standards (LF enforced) |
| Filesystem Error Boundary | `Filesystem_Error_Boundary_Protocol_v1.0.md` | FS error isolation |
| G-CBS Standard | `G-CBS_Standard_v1.1.md` | Git-backed change batch spec |
| Git Workflow | `Git_Workflow_Protocol_v1.1.md` | Branch, commit, merge rules |
| Governance | `Governance_Protocol_v1.0.md` | Governance rules and escalation |
| Intent Routing | `Intent_Routing_Rule_v1.1.md` | Route CEO intent to correct agent |
| LifeOS Design Principles | `LifeOS_Design_Principles_Protocol_v1.1.md` | System design rules |
| Packet Schema Versioning | `Packet_Schema_Versioning_Policy_v1.0.md` | Schema version management |
| Project Planning | `Project_Planning_Protocol_v1.0.md` | Plan structure and review |
| Test Protocol | `Test_Protocol_v2.0.md` | Testing standards, TDD gates |
| Tier-2 API Evolution | `Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md` | API versioning |
| TODO Standard | `TODO_Standard_v1.0.md` | `LIFEOS_TODO[P0|P1|P2]` format; no bare TODOs |

## Guides & Templates

- `guides/OpenClaw_Codex_OAuth_Recovery_v1.0.md` — OAuth recovery runbook
- `guides/plan_writing_guide.md` — Plan structure guidance
- `templates/` — 9 templates: blocked_report, doc_draft, gap_analysis, governance_request, plan_packet, plan, review_packet, test_draft, walkthrough

## Related Pages

- [governance-model](governance-model.md) — Constitution and hard invariants
- [doc-stewardship](doc-stewardship.md) — Document Steward Protocol detail
- [build-workflow](build-workflow.md) — Git Workflow Protocol detail

## Open Questions

None currently flagged.
