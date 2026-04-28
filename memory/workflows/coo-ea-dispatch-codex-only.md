---
id: MEM-20260428-CODEX-EA-LANE
title: COO EA dispatch uses Codex lane by default
record_kind: rule
authority_class: shared_knowledge
scope: workflow
sensitivity: internal
retention_class: medium
lifecycle_state: active
created_utc: "2026-04-28T08:00:45Z"
updated_utc: "2026-04-28T08:00:45Z"
review_after: "2026-07-28T00:00:00Z"
owner: COO
writer: COO
derived_from_candidate: true
requires_human_review: true
authority_impact: high
personal_inference: false
promotion_basis: Manual COO disposition accepted the action-constraining candidate because it prevents wrong executor routing for LifeOS repo/build work. This record is branch-stable until merged to main; source branch build/memory-operational-effect-70 at main base bf04796edb0152150abd0f75be14de44a6269caf.
sources:
  - source_type: issue
    locator: https://github.com/marcusglee11/LifeOS/issues/69
    quoted_evidence: 'Issue #69 is labelled lane:codex; the repository label description is "COO-dispatched EA lane: Codex only".'
    captured_utc: "2026-04-28T08:00:45Z"
write_receipts:
  - memory/receipts/rcp-20260428-codex-ea-lane.md
tags:
  - codex
  - ea-dispatch
  - coo
  - lane:codex
  - work-management
---
Operational rule: COO-managed LifeOS build/repo implementation work should be routed to the Codex EA lane by default unless Marcus explicitly changes the rule.

Operational effect target:
- Before dispatching implementation work, retrieve this record with a natural-language query about COO executor lane or EA build dispatch.
- Use the result to select `lane:codex` / Codex execution rather than a generic Claude/OpenClaw route.
- If a future task intentionally uses another executor, record the explicit exception and reason.
