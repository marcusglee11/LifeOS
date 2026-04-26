---
source_docs:
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: c7df98632ed6dfee99daaada103cd613dc630501
authority: derived
page_class: evergreen
concepts:
  - CEO
  - COO
  - EA
  - COO Commons
  - control plane
  - GitHub relay
  - phased authority
  - Google Drive
  - attempt_id
---

## Summary

LifeOS control-plane architecture (v2.3c, 2026-04-17). The CEO sets objectives; the COO
(OpenClaw, replaceable) validates commands and creates GitHub issues as work orders; EAs
(Claude Code, Codex) execute stateless from issue body via GitHub Actions; COO Commons
provides a deterministic shared-services layer making COO substrate-independent.

## Key Relationships

- [agent-roles](agent-roles.md) — detailed actor definitions and autonomy model
- [openclaw-integration](openclaw-integration.md) — COO substrate (OpenClaw)
- [coo-runtime](coo-runtime.md) — COO runtime FSM (see conflict note)
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md`

## Authority Note

Canonical source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md`.
That document wins on any conflict with this page.

## Current Truth

**Control plane (Phase 1 design):** CEO command → COO validates & creates GitHub issue →
GitHub triggers workflow → EA executes → EA posts result comment → COO reads result →
reports to CEO. Reconciliation loop handles webhook delays. Cron heartbeat as fallback.

**Work-order states:** backlog → ready → dispatched → running → succeeded | failed |
blocked | needs_decision | superseded | timed_out. `late_result` is an event classification
(not a state) — valid result received when issue is not in `running` or `dispatched`.

**Key v2.3c fixes:** `running → blocked` and `running → needs_decision` transitions
restored; malformed results in `dispatched` or `running` → `needs_decision` (schema
rejection, escalated); `attempt_id` (COO-generated per `→ dispatched` transition) required
in EA result payloads; `workflow_run_id` sourced from GitHub webhook metadata, not EA.
Idempotency correlation key: `issue_id + attempt_id + workflow_run_id`.

**COO Commons (Phase 1):** in-process schema validation library (not a network API) +
direct file reads from verified local clone for phase/policy config. Webhook ingestion
service is the sole public-facing endpoint; substrate has no public endpoint.

**Google Drive / Workspace (ratified 2026-04-26):** non-canonical surface only —
collaboration, drafting, advisory, briefing. Not canonical operational state, not an
execution gate, not a promotion source. Material from Drive has no operational effect
until captured into GitHub state by the active COO path or CEO-authorized operator.

**Phased authority expansion:** Phase 1 (deterministic dispatch), Phase 2A (scheduled
routines), Phase 2B (bounded recovery), Phase 3 (NL intent parsing), Phase 4 (decomposition).

## Open Questions

None.
