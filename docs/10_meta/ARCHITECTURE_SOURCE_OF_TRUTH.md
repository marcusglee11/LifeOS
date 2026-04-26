# Architecture Source of Truth

Status: Active orientation surface
Owner: CEO / active COO stewardship
Purpose: One-page map of what is canonical now, what is proposal only, and what is superseded or stale
Related packet: `docs/10_meta/Architecture_Normalization_Reconciliation_Packet_2026-04-24.md`

Important: this page is an orientation surface. It is not itself the deepest authority for operational architecture or governance.

---

## 1. Canonical now

| Class | Repo path | Role |
| --- | --- | --- |
| Canonical operational architecture | `docs/00_foundations/LifeOS Target Architecture v2.3c.md` | Operational architecture authority |
| Canonical governance contract | `docs/01_governance/COO_Operating_Contract_v1.0.md` | CEO/COO governance authority |
| Canonical runtime state ledger | `docs/11_admin/LIFEOS_STATE.md` | Current operational state |
| Canonical runtime work tracker | `docs/11_admin/BACKLOG.md` | Actionable work tracker |

## 2. Proposal-only surfaces

| Repo path | Current status |
| --- | --- |
| `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` | Draft communications / advisory-ingress architecture; proposal-only; non-canonical; contains unratified Drive / Workspace ingress, advisory lifecycle, approval-channel, and briefing-trigger proposals; loses to canonical architecture, COO contract §§7–9, and ADR-001 through ADR-004 on conflict |
| `docs/00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md` | Architecture proposal |
| `docs/00_foundations/lifeos-agent-architecture.md` | Reference / bootstrap architecture |
| `docs/00_foundations/lifeos-maximum-vision.md` | Vision / explainer |

## 3. Supporting orientation / derived references

| Repo path | Current status |
| --- | --- |
| `docs/00_foundations/Agent_Roles_Reference_v1.0.md` | Active orientation reference; non-authoritative; loses to canonical architecture/governance docs on conflict |

## 4. Superseded or stale surfaces

| Repo path | Current classification |
| --- | --- |
| `docs/00_foundations/Architecture_Skeleton_v1.0.md` | Stale conceptual explainer |
| `docs/10_meta/CHANGELOG.md` | Stale repository changelog surface |
| `docs/11_admin/AUTONOMY_STATUS.md` | Derived and stale orientation surface |

## 5. Truth hierarchy

1. Constitution and governance rulings
2. Canonical governance contract + canonical operational architecture
3. Canonical execution trackers (`LIFEOS_STATE.md`, `BACKLOG.md`)
4. Supporting orientation / derived references
5. Derived projections and indexes
6. Proposal / explainer docs
7. Conversation memory and uncaptured notes — never canonical by themselves

## 6. Normalization blockers still open

None.

Issue #34 is a reconciliation/classification issue for `ARCH_Multi_Agent_Communication_Architecture.md`; it does not reopen issues #30, #31, #32, or #33 and does not promote the communications draft into canon.

Architecture normalization issues #30, #31, #32, #33, and #34 are resolved. Issue #35 installs the lightweight maintenance rule; after #35 is accepted, the architecture normalization campaign is complete.

## 7. Normalization blockers resolved

| # | Decision | Ratified | ADR | Governance surface |
| --- | --- | --- | --- | --- |
| 1 | Human approval capture contract | 2026-04-26 | ADR-003 | `COO_Operating_Contract_v1.0.md` §9 |
| 2 | Drive / Workspace canonical role | 2026-04-26 | ADR-004 | `LifeOS Target Architecture v2.3c.md` §2.7; `COO_Operating_Contract_v1.0.md` §9.6 |
| 3 | Full operational-state sole-writer boundary | 2026-04-24 | ADR-001 | `COO_Operating_Contract_v1.0.md` §7 |
| 4 | Active vs standby COO semantics in governance surfaces | 2026-04-24 | ADR-001 | `COO_Operating_Contract_v1.0.md` §7 |
| 5 | Hermes ↔ OpenClaw directionality and pushback rules | 2026-04-24 | ADR-002 | `COO_Operating_Contract_v1.0.md` §8 |

## 8. Change-control rule

No architecture-affecting change is canonical until required repo surfaces are updated:

- this source-of-truth page when canon classification changes
- architecture changelog when architecture deltas occur
- ADR register when ratified architecture decisions land

## 9. Lightweight architecture maintenance rule

Architecture maintenance is event-triggered only. There is no monthly ritual, standing ceremony, or broad recurring architecture review by default.

Before merge, any PR that changes architecture, governance, authority, truth surfaces, operational-state semantics, approval capture, writer boundaries, agent directionality, Drive / Workspace authority, receipt models, state-machine semantics, or canonical/proposal/stale classification must record one of the following in the PR body or closing issue:

```text
Architecture impact: none
```

or:

```text
Architecture impact: yes
Architecture surfaces updated:
- Source-of-truth page: yes/no + reason
- Architecture changelog: yes/no + reason
- ADR index: yes/no + reason
Canonicality changed: yes/no
Ratified decision added: yes/no
```

**Update triggers:**

| Trigger | Required architecture-control update |
| --- | --- |
| Canonical / proposal-only / stale classification changes | Update this source-of-truth page |
| A canonical architecture or governance surface is added, removed, renamed, promoted, or demoted | Update this source-of-truth page and architecture changelog |
| Architecture semantics materially change | Update architecture changelog |
| A ratified architecture decision changes authority boundaries, truth surfaces, writer boundaries, approval capture, receipt models, state-machine semantics, agent directionality, or canonical runtime role | Update the relevant canonical doc, architecture changelog, and ADR index |
| A proposal-only document changes but remains proposal-only and does not alter current canon | Do not add an ADR; update this page only if classification or conflict rules change |
| Typo, formatting, generated index refresh, or non-semantic cleanup | No architecture-control update required; mark Architecture impact: none |

ADRs remain reserved for ratified architecture decisions with operational consequences. They are not required for checklist maintenance, cleanup observations, speculative ideas, or generic documentation churn.
