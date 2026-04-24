# Architecture Source of Truth

Status: Active orientation surface
Owner: CEO / active COO stewardship
Purpose: One-page map of what is canonical now, what is proposal only, and what is superseded or stale
Related packet: `docs/10_meta/Architecture_Normalization_Reconciliation_Packet_2026-04-24.md`

Important: this page is an orientation surface. It is not itself the deepest authority for operational architecture or governance.

---

## 1. Canonical now

| Class | Repo path | Role |
|---|---|---|
| Canonical operational architecture | `docs/00_foundations/LifeOS Target Architecture v2.3c.md` | Operational architecture authority |
| Canonical governance contract | `docs/01_governance/COO_Operating_Contract_v1.0.md` | CEO/COO governance authority |
| Active actor taxonomy | `docs/00_foundations/Agent_Roles_Reference_v1.0.md` | Supporting authority for actors / autonomy routing |
| Canonical runtime state ledger | `docs/11_admin/LIFEOS_STATE.md` | Current operational state |
| Canonical runtime work tracker | `docs/11_admin/BACKLOG.md` | Actionable work tracker |

## 2. Proposal-only surfaces

| Repo path | Current status |
|---|---|
| `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` | Draft communications / advisory architecture |
| `docs/00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md` | Architecture proposal |
| `docs/00_foundations/lifeos-agent-architecture.md` | Reference / bootstrap architecture |
| `docs/00_foundations/lifeos-maximum-vision.md` | Vision / explainer |

## 3. Superseded or stale surfaces

| Repo path | Current classification |
|---|---|
| `docs/00_foundations/Architecture_Skeleton_v1.0.md` | Stale conceptual explainer |
| `docs/10_meta/CHANGELOG.md` | Stale repository changelog surface |
| `docs/11_admin/AUTONOMY_STATUS.md` | Derived and stale orientation surface |

## 4. Truth hierarchy

1. Constitution and governance rulings
2. Canonical governance contract + canonical operational architecture
3. Active actor taxonomy / supporting authority docs
4. Canonical execution trackers (`LIFEOS_STATE.md`, `BACKLOG.md`)
5. Derived projections and indexes
6. Proposal / explainer docs
7. Conversation memory and uncaptured notes — never canonical by themselves

## 5. Normalization blockers still open

1. Authoritative CEO approval form and capture path
2. Drive / Workspace role: mirror only vs advisory ingress adapter
3. Full operational-state sole-writer boundary
4. Active vs standby COO semantics in governance surfaces
5. Hermes ↔ OpenClaw directionality and pushback rules

## 6. Change-control rule

No architecture-affecting change is canonical until required repo surfaces are updated:
- this source-of-truth page when canon classification changes
- architecture changelog when architecture deltas occur
- ADR register when ratified architecture decisions land
