# Architecture Normalization Reconciliation Packet — 2026-04-24

Status: Working packet for normalization reset
Owner: CEO / active COO normalization pass
Scope: Re-establish canon, authority semantics, writer boundaries, and controlled follow-on cleanup
Related reset: AMENDED RECOVERY PLAN — Architecture Normalization and COO Onboarding Reset

---

## 1. Canonical docs list

| Surface | Repo path | Declared / inferred status | Notes |
|---|---|---|---|
| Canonical operational architecture | `docs/00_foundations/LifeOS Target Architecture v2.3c.md` | Declared `Canonical` | Current canonical operational architecture for CEO→COO→EA orchestration, COO Commons, state machine, active/standby substrate, fail-closed behavior. |
| Canonical governance agreement | `docs/01_governance/COO_Operating_Contract_v1.0.md` | Declared canonical in opening paragraph | Governance contract for CEO/COO interaction, escalation, and change control. Canonical, but materially less specific than v2.3c on active/standby and sole-writer boundaries. |
| Active actor taxonomy / autonomy routing reference | `docs/00_foundations/Agent_Roles_Reference_v1.0.md` | Declared `Active` | Current actor taxonomy and COO autonomy level reference. Supportive canon, not the deepest architecture authority. |
| Canonical runtime state ledger | `docs/11_admin/LIFEOS_STATE.md` | Declared canonical source in file and corpus | Current operational state / recent wins / blockers / phase posture. |
| Canonical backlog / work tracker | `docs/11_admin/BACKLOG.md` | Declared canonical backlog | Actionable work tracker. Execution surface, not architecture authority. |

## 2. Proposal-only docs list

| Surface | Repo path | Declared / inferred status | Notes |
|---|---|---|---|
| Communications / advisory architecture | `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` | Declared `Draft` | Strongest articulation of advisory ingress, promotion, approval binding, receipts, and briefing projection. Not canonical yet. |
| Future build automation operating model | `docs/00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md` | Declared `Architecture Proposal` | Future-state platform architecture; not current authority. |
| Two-agent bootstrap architecture | `docs/00_foundations/lifeos-agent-architecture.md` | Inferred proposal / reference architecture | Historical bootstrap reference, no canonical marker. |
| Maximum-vision doc | `docs/00_foundations/lifeos-maximum-vision.md` | Inferred vision / explainer | End-state vision, not executable canon. |

## 3. Superseded / stale / in-tension docs list

| Surface | Repo path | Status | Why it is here |
|---|---|---|---|
| High-level architecture skeleton | `docs/00_foundations/Architecture_Skeleton_v1.0.md` | Stale conceptual explainer | Still useful as a mental model, but it predates current canon and points to `COOSpecv1.0Final.md`, which is not present in repo. |
| Meta changelog | `docs/10_meta/CHANGELOG.md` | Stale control surface | Not functioning as an architecture delta log; effectively frozen on 2026-01-09. |
| Derived autonomy status | `docs/11_admin/AUTONOMY_STATUS.md` | Derived and stale | File self-declares derived status; current metadata is anchored to 2026-02-14 and should not be used as current architecture authority. |
| Communications / advisory architecture | `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` | In tension with canon, not stale | Not obsolete, but in tension with canonical v2.3c on Drive role, CEO approval channel capture, and operational-state scope. |
| COO operating contract | `docs/01_governance/COO_Operating_Contract_v1.0.md` | Canonical but incomplete for normalization concerns | Still authority for CEO/COO relationship, but too abstract for active/standby, proxy authority, approval binding, and sole-writer boundaries needed for onboarding reset. |

## 4. Truth-surface hierarchy

| Surface | Classification | Current authority posture |
|---|---|---|
| `docs/00_foundations/LifeOS Target Architecture v2.3c.md` | authority | Canonical operational architecture |
| `docs/01_governance/COO_Operating_Contract_v1.0.md` | authority | Canonical governance contract |
| `docs/00_foundations/Agent_Roles_Reference_v1.0.md` | authority-supporting reference | Active actor taxonomy / autonomy routing reference |
| `docs/11_admin/LIFEOS_STATE.md` | execution/work tracker | Canonical current operational state |
| `docs/11_admin/BACKLOG.md` | execution/work tracker | Canonical actionable work tracker |
| GitHub issue body + state block | authority within runtime execution | Canonical work-order state per v2.3c |
| GitHub issue labels | projection / metadata | Machine-readable routing and filtering; not deepest truth |
| GitHub Projects v2 fields | projection | Derived planning/index surface only |
| PRs / commits / structured result comments | evidence surfaces | Execution evidence, not sole state truth |
| COO Commons webhook ingress / validation / config read path | operational interface | Deterministic shared-services layer feeding active COO |
| `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` | proposal / explainer | Draft articulation of communications canon candidate |
| Google Drive proposal files / briefing projections | adapter surface in draft only | Not canonical operational truth; draft treats these as constrained advisory ingress + projection |
| `briefing/current.md` | projection in draft only | Draft explicitly says projection, not authority |
| Telegram / CLI command surface | authority-bearing human channel | Human command / approval channel; does not directly mutate GitHub state |
| `docs/INDEX.md` | projection / navigation | Repository orientation index, not architecture authority |
| `docs/11_admin/AUTONOMY_STATUS.md` | projection / derived view | Self-declared derivative; canon loses if conflict |
| `artifacts/googleforcoo.md` | proposal / implementation note | Useful evidence of shared Google Workspace intent, but not canonical architecture |

## 5. Authority matrix

| Actor / surface | May propose | May approve | May direct | May push back / challenge | May mutate state | May only observe / report |
|---|---|---|---|---|---|---|
| CEO | Yes | Yes, ultimate authority | Yes | Yes | Indirectly only, via COO execution | No |
| Active COO | Yes, operational proposals / escalations | No independent strategic approval in current canon | Yes, within phase-scoped discretion | Yes, via escalation / fail-closed behavior | Yes, operational GitHub state mutations and receipts | No |
| Standby COO | No canonical independent proposal lane defined | No | No active direction authority while standby | Verification / rehearsal implied by standby role, but no forwarding or mutation authority | No while standby | Primarily observe / stay ready |
| Advisory agents | Yes, advisory ingress only | No | No operational direction authority | Yes, advisory challenge / analysis outside operational loop | No operational state mutation | Read / advise |
| Executing agents (EAs) | No | No | No | No strategic pushback authority defined; return status only | Evidence only (PRs, commits, result comments) | No |
| COO Commons | No judgment authority | No | No | No | No decision-layer mutation authority; deterministic shared services only | Service role |
| Telegram / CLI approval channel | Carries proposals / commands | Carries authoritative human approval if COO captures it | Carries human direction | Can carry rejection / escalation responses | Does not directly mutate GitHub state | N/A |
| GitHub work-order surfaces | N/A | N/A | N/A | N/A | Mutated by active COO; evidence written by EAs | Read by all relevant actors |
| Google Drive / Workspace advisory surfaces | Yes, in draft only | No | No | Advisory only | No operational mutation authority in canon | Read by COO/advisory agents as applicable |

## 6. Writer-boundary matrix

| Surface | Sole writer | Allowed readers | Standby role | Authoritative or derivative |
|---|---|---|---|---|
| GitHub issue body + structured state block | Active COO | CEO, standby COO, advisory agents, EAs, observers via GitHub | Observe only; receives no forwarded events in Phase 1 | Authoritative |
| GitHub issue labels | Active COO | Same as above | Observe only | Derivative metadata with routing value |
| GitHub Projects v2 fields | Active COO | CEO, standby COO, observers | Observe only | Derivative projection |
| Approval receipt (if captured) | Active COO | CEO, standby COO, relevant reviewers | Observe only | Operational evidence / gate artefact |
| Promotion receipt | Active COO | CEO, standby COO, relevant reviewers | Observe only | Operational evidence / gate artefact |
| Reconciliation / completion / closure receipts | Active COO | CEO, standby COO, relevant reviewers | Observe only | Operational evidence / gate artefact |
| EA structured result comment | EA for that workflow run | CEO, active COO, standby COO, reviewers | Observe only | Evidence, not canonical state |
| PR / commit evidence | EA for that workflow run | Same as above | Observe only | Evidence |
| Drive proposal file | Advisory agent / proposing surface | COO, possibly CEO/advisory readers | Standby may inspect if manually pointed, but no canonical role defined | Non-operational adapter surface |
| `briefing/current.md` | Not yet canonically assigned; active COO is strongest implied owner | Constrained agents, CEO, reviewers | Standby can read | Derivative projection |
| `docs/11_admin/LIFEOS_STATE.md` | Human / stewardship workflow today | CEO, agents, reviewers | Read only | Canonical execution tracker, not architecture authority |
| `docs/11_admin/BACKLOG.md` | Human / stewardship workflow today | Same | Read only | Canonical execution tracker |

## 7. Mismatch matrix — canonical target architecture vs communications architecture draft

| Topic | v2.3c position | Communications draft position | Classification | Note |
|---|---|---|---|---|
| Primary operational bus | GitHub is canonical relay bus and evidence surface | GitHub is sole primary operational bus | Same concept, wording mismatch | Substantively aligned. |
| Drive / Workspace role | `docs/00_foundations/LifeOS Target Architecture v2.3c.md` says Drive is read-only mirror, not operational truth, not shared state store, GitHub → Drive sync only | Draft says Drive is constrained advisory ingress adapter plus bounded briefing projection | Unresolved decision required | Biggest live architecture conflict. Current canon says mirror-only; draft says ingress adapter. |
| Advisory ingress / promotion boundary | Not explicit as a separate advisory lifecycle | Explicit advisory ingress → validation → classification → approval / policy gate → promotion → operational work order | Canonical gap | Draft has needed semantics missing from canon. |
| Operational-state scope | v2.3c focuses on work-order state and GitHub surfaces | Draft explicitly includes approval / promotion / reconciliation / completion receipts as operational state | Canonical gap | Needed for authority clarity and onboarding. |
| Sole-writer boundary | v2.3c makes COO sole writer of issue state block; EAs are evidence producers | Draft says COO is sole writer of all operational state | Same concept, wording mismatch | Draft generalizes a principle that canon only partially states. |
| Human approval semantics | v2.3c says CEO issues commands via Telegram or CLI; no approval binding tuple | Draft defines Telegram approval contract and binding tuple | Canonical gap | Required for normalization. |
| CLI channel scope | v2.3c explicitly allows Telegram or CLI | Draft names Telegram only | Unresolved decision required | Need explicit ruling on authoritative human approval form and whether CLI is co-equal or fallback-only. |
| Approval binding tuple | Not explicit | `(proposal_id, proposal_fingerprint, rendered_summary_hash)` with drift blocking | Canonical gap | Draft likely needed; not yet canon. |
| Briefing projection | Absent | `briefing/current.md` projection with trigger/freshness rules, not authority | Proposal-only surface | Useful candidate surface, not canon. |
| Active / standby COO semantics | Explicit Phase 1 active/standby topology and switchover semantics | Not substantially covered | Same concept, wording mismatch | Canon already stronger here; governance surfaces need to catch up. |
| Inter-agent directionality (Hermes ↔ OpenClaw) | Not defined | Not defined | Unresolved decision required | Conversationally important, not canonically captured. |
| Shared Google Workspace / `gws` surface | Not defined | Not defined in draft file; only seen in artifacts and session work | Unresolved decision required | Observed implementation intent exists, but repo canon has not absorbed it. |

## 8. Required decisions only

1. Confirm whether Google Drive / Workspace is canonically mirror-only or also advisory ingress.
2. Define authoritative CEO approval form and capture path: Telegram only, Telegram + CLI, or channel-agnostic with mandatory receipt capture.
3. Ratify minimum approval binding tuple, including whether `policy_version` and `phase` are mandatory additions beyond `(proposal_id, proposal_fingerprint, rendered_summary_hash)`.
4. Codify proxy / delegated authority limits for COO substrates and clarify whether standby can ever authorize mutation.
5. Codify inter-agent directionality between Hermes and OpenClaw: advisory only, challengeable delegated direction, or no cross-direction authority.
6. Expand sole-writer rule from issue-state-block scope to full operational-state scope, or explicitly reject that expansion.
7. Assign canonical ownership for `briefing/current.md` if that projection surface is retained.

## 9. Bottom line

From this packet alone:
- Canon now: `LifeOS Target Architecture v2.3c`, `COO_Operating_Contract_v1.0`, `Agent_Roles_Reference_v1.0`, `LIFEOS_STATE.md`, `BACKLOG.md`.
- Proposal only: communications architecture draft, future operating-model proposal, vision/bootstrap architecture docs.
- Stale / in tension: architecture skeleton, meta changelog, derived autonomy status, communications draft vs canon on Drive/approval semantics, and the governance contract for current active/standby specificity.
- Active writer of operational work-order state: active COO.
- Standby COO: observe / remain cold-failover only; no active mutation authority in current canon.
- Biggest unresolved blockers: approval form + binding, Drive/Workspace role, sole-writer scope, and Hermes/OpenClaw directionality.
