---
source_docs:
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: bf4d9ecd01e5124584e96a42b95f16c7f39e3fd2
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
blocked | needs_decision | superseded | timed_out

**COO Commons:** deterministic shared-services layer (webhook ingestion, schema validation,
policy/phase config as data). Not a second COO; supplies inputs to decisions.

**Phased authority expansion:** Phase 1 (deterministic dispatch), Phase 2A (scheduled
routines), Phase 2B (bounded recovery), Phase 3 (NL intent parsing), Phase 4 (decomposition).

## Open Questions

None.
