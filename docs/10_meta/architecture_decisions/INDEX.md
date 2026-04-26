# Architecture Decision Records Index

Status: Active register skeleton
Owner: CEO / active COO stewardship
Purpose: Record ratified architecture decisions only

Use ADRs only for:

- authority-boundary changes
- truth-surface changes
- writer-boundary changes
- state-machine / receipt-model changes
- other ratified architectural decisions with operational consequences

Do not use ADRs for:

- every cleanup observation
- speculative future-state ideas
- uncaptured chat conclusions
- generic documentation churn

---

## ADR status legend

- Proposed — drafted, not ratified
- Ratified — decision accepted as architecture authority
- Superseded — replaced by a later ADR

---

## Index

| ADR | Title | Status | Date | Scope |
| --- | --- | --- | --- | --- |
| ADR-001 | Active vs Standby COO and Sole-Writer Boundary | Ratified | 2026-04-24 | `COO_Operating_Contract_v1.0.md` §7 |
| ADR-002 | Inter-Agent Directionality and Pushback Rules | Ratified | 2026-04-24 | `COO_Operating_Contract_v1.0.md` §8 |
| ADR-003 | Human Approval Capture Contract | Ratified | 2026-04-26 | `COO_Operating_Contract_v1.0.md` §9 |
| ADR-004 | Drive / Workspace Canonical Role | Ratified | 2026-04-26 | `LifeOS Target Architecture v2.3c.md` §2.7; `COO_Operating_Contract_v1.0.md` §9.6 |

### ADR-001 — Active vs Standby COO and Sole-Writer Boundary

- Date: 2026-04-24
- Status: Ratified
- Authority: CEO
- Closes: normalization issues #3 (sole-writer boundary) and #4 (active/standby semantics);
  GitHub issue #31
- Decision: Exactly one COO substrate is active writer at a time. Active COO is sole writer of
  operational state (issue body, labels, projections, receipts). Standby COO may observe,
  rehearse, verify, and prepare switchover; may not mutate operational state. Activation
  requires a seven-step switchover sequence.
- Governance surface: `docs/01_governance/COO_Operating_Contract_v1.0.md` §7

### ADR-002 — Inter-Agent Directionality and Pushback Rules

- Date: 2026-04-24
- Status: Ratified
- Authority: CEO
- Closes: normalization issue #5 (Hermes/OpenClaw directionality); GitHub issue #33
- Decision: Hermes and OpenClaw may exchange advisory guidance, challenge packets, readiness
  assessments, and recommendations. Peer-to-peer direction is advisory only; not authoritative
  unless re-issued through the active COO authority path or explicitly stamped by CEO. Pushback
  is mandatory when authority, phase, approval, or writer boundary is unclear.
- Governance surface: `docs/01_governance/COO_Operating_Contract_v1.0.md` §8

### ADR-003 — Human Approval Capture Contract

- Date: 2026-04-26
- Status: Ratified
- Authority: CEO
- Closes: normalization issue #1 (approval capture contract); GitHub issue #30
- Decision:
  - CEO is the supreme source of LifeOS authority. No agent, channel, receipt store, workflow,
    policy surface, or operational convention may narrow, transfer, override, or veto CEO authority.
  - Approval source channels do not limit CEO authority. They define the current ratified list of
    channels from which approval may be captured without additional channel ratification.
  - Capture rules govern operational admissibility only. They define when CEO approval becomes
    operationally actionable inside LifeOS, not the limits of CEO authority itself.
  - Direct CEO interaction with COO agents is a valid approval source event. The active COO may
    capture such approval into the canonical receipt store. A standby COO may only relay or
    prepare capture; it may not mutate operational state.
  - GitHub operational state is the canonical approval receipt store until normalization issue #32
    resolves Drive / Workspace authority.
  - Closes GitHub issue #30 only. Does not resolve issues #32, #34, or #35.
- Governance surface: `docs/01_governance/COO_Operating_Contract_v1.0.md` §9

### ADR-004 — Drive / Workspace Canonical Role

- Date: 2026-04-26
- Status: Ratified
- Authority: CEO
- Closes: normalization issue #2 (Drive / Workspace role); GitHub issue #32
- Decision:
  - Drive / Workspace is a non-canonical collaboration, drafting, advisory, and briefing surface.
  - Drive / Workspace may be used for shared documents, draft specs, review notes, planning material, advisory proposals, briefing packs, human/agent communication, and context sharing between the CEO, COO agents, advisory agents, and review agents.
  - Drive / Workspace is not canonical operational state, not a canonical approval receipt store, not a work-order lifecycle store, not an execution gate, not a promotion source, not execution truth, and not a substitute for GitHub receipts.
  - Drive / Workspace is not ratified as an automatic advisory ingress adapter.
  - Material originating in Drive / Workspace may inform COO judgment and advisory review, but has no operational effect until captured into GitHub operational state by the active COO path or by an explicitly CEO-authorized operator acting for that path.
  - Google Workspace tooling, including `gws`, OAuth credentials, Drive polling, Drive push notifications, and service accounts, is not part of the canonical runtime unless separately ratified.
  - `ARCH_Multi_Agent_Communication_Architecture.md` remains draft/proposal-only and is not promoted by this ADR.
- Architecture surface: `docs/00_foundations/LifeOS Target Architecture v2.3c.md` §2.7
- Governance surface: `docs/01_governance/COO_Operating_Contract_v1.0.md` §9.6

---

## Next ADR candidates after normalization

1. Advisory lifecycle / receipt model if promoted from draft to canon
