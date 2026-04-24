# Architecture Changelog

Status: Active control surface
Owner: CEO / active COO stewardship
Purpose: Record architecture deltas over time without turning runtime state trackers into architecture junk drawers

---

## Entry format

- Date:
- Change:
- Why:
- Affected docs:
- Related issue:
- Related ADR:
- Status: `proposed | ratified | implemented | superseded`

---

## Entries

### 2026-04-24 — Amendment A1: COO Authority and Inter-Agent Directionality (Issues #31, #33)

- Change: Ratified active/standby COO sole-writer boundary (§7) and inter-agent directionality
  and pushback rules (§8) into `COO_Operating_Contract_v1.0.md`. Registered ADR-001 and
  ADR-002. Closed normalization blockers #3, #4, #5 in source-of-truth page.
- Why: Normalization reset (PR #28) surfaced unresolved authority boundaries: sole-writer scope,
  standby COO permissions, and whether Hermes/OpenClaw peer-to-peer direction is authoritative.
  Issues #31 and #33 captured these gaps as acceptance criteria.
- Affected docs:
  - `docs/01_governance/COO_Operating_Contract_v1.0.md` — added §7 and §8
  - `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md` — closed blockers #3, #4, #5; added §7 resolved table
  - `docs/10_meta/ARCHITECTURE_CHANGELOG.md` — this entry
  - `docs/10_meta/architecture_decisions/INDEX.md` — added ADR-001, ADR-002
- Related issue: GitHub #31, GitHub #33
- Related ADR: ADR-001, ADR-002
- Status: ratified

### 2026-04-24
- Change: Installed architecture normalization control surfaces (`Architecture_Normalization_Reconciliation_Packet_2026-04-24.md`, `COO_Authority_Contract_Draft_2026-04-24.md`, `ARCHITECTURE_SOURCE_OF_TRUTH.md`, this changelog, ADR index skeleton, targeted issue list draft).
- Why: Architecture truth had fragmented across canonical docs, draft docs, runtime trackers, and uncaptured onboarding discussions.
- Affected docs:
  - `docs/10_meta/Architecture_Normalization_Reconciliation_Packet_2026-04-24.md`
  - `docs/10_meta/COO_Authority_Contract_Draft_2026-04-24.md`
  - `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md`
  - `docs/10_meta/ARCHITECTURE_CHANGELOG.md`
  - `docs/10_meta/architecture_decisions/INDEX.md`
  - `docs/10_meta/Architecture_Normalization_Targeted_Issue_List_2026-04-24.md`
- Related issue: not opened yet — targeted issue list drafted first
- Related ADR: none yet
- Status: proposed
