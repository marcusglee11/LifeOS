# Architecture Normalization — Targeted Issue List Draft

Status: Draft issue list derived from reconciliation packet and authority contract draft
Owner: CEO / active COO
Inputs:
- `docs/10_meta/Architecture_Normalization_Reconciliation_Packet_2026-04-24.md`
- `docs/10_meta/COO_Authority_Contract_Draft_2026-04-24.md`

Rule: one issue = one objective. Do not open these until the reconciliation packet and authority draft have been reviewed.

---

## Issue 1 — Ratify human approval capture contract

- Scope: Define what counts as authoritative CEO approval, where it must be captured, and what tuple it binds to.
- Source docs:
  - `docs/00_foundations/LifeOS Target Architecture v2.3c.md`
  - `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md`
  - `docs/10_meta/COO_Authority_Contract_Draft_2026-04-24.md`
- Acceptance criteria:
  - explicit approval source channels named
  - approval receipt capture rule defined
  - minimum binding tuple ratified
  - re-approval invalidation rule explicit
- Required repo surfaces before merge:
  - canonical governance / architecture doc(s)
  - `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md`
  - `docs/10_meta/ARCHITECTURE_CHANGELOG.md`
  - ADR if ratified

## Issue 2 — Ratify active vs standby COO semantics and sole-writer boundary

- Scope: Clarify mutation authority, standby limits, and switchover semantics.
- Source docs:
  - `docs/00_foundations/LifeOS Target Architecture v2.3c.md`
  - `docs/01_governance/COO_Operating_Contract_v1.0.md`
  - `docs/10_meta/COO_Authority_Contract_Draft_2026-04-24.md`
- Acceptance criteria:
  - exactly one active writer rule explicit
  - standby allowed / forbidden actions explicit
  - switchover trigger and sequence explicit
  - operational-state sole-writer scope explicit
- Required repo surfaces before merge:
  - canonical governance / architecture doc(s)
  - source-of-truth page
  - architecture changelog
  - ADR if ratified

## Issue 3 — Resolve Drive / Workspace role in canon

- Scope: Decide whether Drive / Workspace is mirror only or also advisory ingress adapter.
- Source docs:
  - `docs/00_foundations/LifeOS Target Architecture v2.3c.md`
  - `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md`
  - `artifacts/googleforcoo.md`
- Acceptance criteria:
  - canonical role chosen
  - proposal-only surfaces kept proposal-only unless ratified
  - Google Workspace / `gws` mention added only if documenting already-existing reality
  - briefing / ingress implications resolved
- Required repo surfaces before merge:
  - canonical architecture doc(s)
  - source-of-truth page
  - architecture changelog
  - ADR if ratified

## Issue 4 — Resolve Hermes ↔ OpenClaw directionality and pushback rules

- Scope: Define whether peer COOs may direct one another, what is authoritative vs advisory, and how pushback / escalation works.
- Source docs:
  - `docs/10_meta/Architecture_Normalization_Reconciliation_Packet_2026-04-24.md`
  - `docs/10_meta/COO_Authority_Contract_Draft_2026-04-24.md`
  - relevant runtime CLI / COO command surfaces if implementation wording is needed
- Acceptance criteria:
  - peer directionality class explicit
  - active/standby interaction clear
  - pushback and escalation rules explicit
- Required repo surfaces before merge:
  - canonical governance / architecture doc(s)
  - source-of-truth page
  - architecture changelog
  - ADR if ratified

## Issue 5 — Reconcile communications draft with canon or mark it proposal-only

- Scope: Either absorb ratified semantics into canon or clearly mark the communications draft as non-canonical.
- Source docs:
  - `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md`
  - `docs/00_foundations/LifeOS Target Architecture v2.3c.md`
- Acceptance criteria:
  - no silent conflict remains on approval semantics, Drive role, or operational-state scope
  - status / supersession markers are explicit
  - stale statements are marked or removed
- Required repo surfaces before merge:
  - affected architecture docs
  - source-of-truth page
  - architecture changelog
  - targeted ADRs only if ratified

## Issue 6 — Install architecture-maintenance checks after canon is stable

- Scope: Add lightweight maintenance checks / templates only after authority normalization is done.
- Source docs:
  - `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md`
  - `docs/10_meta/ARCHITECTURE_CHANGELOG.md`
  - `docs/10_meta/architecture_decisions/INDEX.md`
- Acceptance criteria:
  - pre-merge capture checklist defined
  - trigger conditions for reconciliation defined
  - no monthly ritual / process bloat added by default
- Required repo surfaces before merge:
  - changelog
  - source-of-truth page
  - issue / PR template surface if changed
