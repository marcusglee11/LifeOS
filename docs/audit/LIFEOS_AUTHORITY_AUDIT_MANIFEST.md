# LifeOS Authority Audit Manifest

Status: Pro-level audit context manifest
Owner: CEO / active COO stewardship
Audit target commit: `c2f558e3b9d5e60c4fac80ae9b251fb57f325966`
Prepared for: cross-project authority, approval, delegation, pushback, evidence, and state-machine audit

This manifest is a launch surface for a scarce Pro-level Thinking audit. It is not a new canonical architecture decision and does not modify authority semantics by itself.

---

## 1. Audit target

| Field | Value |
| --- | --- |
| Repo | `marcusglee11/LifeOS` |
| Branch | `main` |
| Commit SHA | `c2f558e3b9d5e60c4fac80ae9b251fb57f325966` |
| Manifest path | `docs/audit/LIFEOS_AUTHORITY_AUDIT_MANIFEST.md` |
| Scope | Authority, approval, proxy approval, StepGate, Council Runtime, OpenClaw/Hermes authority, work item lifecycle, receipts/evidence, state transitions |

## 2. Canonicality rule for the auditor

Treat artefacts in this priority order:

1. Constitution and governance rulings
2. Architecture Source of Truth and ratified ADRs
3. COO Operating Contract
4. Canonical operational architecture
5. Current protocol specs
6. Current schemas/tests
7. Current runtime state and backlog trackers
8. Current wiki only when mechanically derived and up to date
9. Proposal/draft docs only where explicitly marked non-canonical
10. Archived docs and conversation memory — never canonical by themselves

Draft/proposal documents are not binding unless ratified. If a draft conflicts with a canonical document, the canonical document wins and the draft should be treated as evidence of unresolved or rejected design pressure, not operative policy.

## 3. Required artefacts

### A. Canonical architecture truth

| Artefact | Path | Canonical? | Notes |
| --- | --- | --- | --- |
| Architecture Source of Truth | `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md` | Orientation/control surface | Current canon/proposal/stale map; says it is not itself the deepest authority |
| Architecture Changelog | `docs/10_meta/ARCHITECTURE_CHANGELOG.md` | Control log | Architecture deltas and normalization amendments |
| ADR / decision index | `docs/10_meta/architecture_decisions/INDEX.md` | Active register | Ratified decisions only; ADR-001 through ADR-004 |
| Docs index | `docs/INDEX.md` | Navigation/control index | Current repo navigation and authority chain |
| Strategic corpus | `docs/LifeOS_Strategic_Corpus.md` | Derived context | Use as orientation only; canonical docs win on conflict |
| Wiki schema | `.context/wiki/SCHEMA.md` | Derived-surface schema | Use only to understand derived wiki constraints |
| Wiki home | `.context/wiki/home.md` | Derived surface | Use only if source_commit/source freshness is valid |

### B. COO authority and operating contract

| Artefact | Path | Canonical? | Notes |
| --- | --- | --- | --- |
| COO Operating Contract | `docs/01_governance/COO_Operating_Contract_v1.0.md` | Canonical governance contract | Main authority surface for CEO/COO/agent boundaries |
| ADR-001 Active/standby + sole-writer | `docs/10_meta/architecture_decisions/INDEX.md` | Ratified | See ADR-001 section |
| ADR-002 Inter-agent directionality | `docs/10_meta/architecture_decisions/INDEX.md` | Ratified | See ADR-002 section |
| ADR-003 Human approval capture | `docs/10_meta/architecture_decisions/INDEX.md` | Ratified | See ADR-003 section |
| ADR-004 Drive/Workspace role | `docs/10_meta/architecture_decisions/INDEX.md` | Ratified | See ADR-004 section |
| Agent roles reference | `docs/00_foundations/Agent_Roles_Reference_v1.0.md` | Non-authoritative orientation | Loses to canonical governance docs on conflict |

### C. StepGate and approval semantics

| Artefact | Path | Canonical? | Notes |
| --- | --- | --- | --- |
| StepGate protocol | `docs/09_prompts/v1.0/protocols/stepgate_protocol_v1.0.md` | Protocol surface | Explicit gate sequencing and approval semantics |
| Human approval capture contract | `docs/01_governance/COO_Operating_Contract_v1.0.md` | Canonical | §9, including binding tuple and ambiguity fails closed |
| Approval capture ADR | `docs/10_meta/architecture_decisions/INDEX.md` | Ratified | ADR-003 |
| G-CBS standard | `docs/02_protocols/G-CBS_Standard_v1.1.md` | Protocol | Include if audit needs governance/build-control semantics |
| Deterministic artefact protocol | `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md` | Protocol | Include if audit needs artefact/receipt semantics |

### D. Council Runtime / governance protocol

| Artefact | Path | Canonical? | Notes |
| --- | --- | --- | --- |
| Council Protocol | `docs/02_protocols/Council_Protocol_v1.3.md` | Canonical | Current council review procedure |
| Council Procedural Specification | `docs/02_protocols/AI_Council_Procedural_Spec_v1.1.md` | Runbook | Executes council procedure |
| Council invocation binding | `docs/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.1.md` | Governance spec | Invocation/runtime binding rules |
| Intent routing | `docs/02_protocols/Intent_Routing_Rule_v1.1.md` | Protocol | CEO/CSO/Council/runtime routing |
| Council context pack schema | `docs/02_protocols/Council_Context_Pack_Schema_v0.3.md` | Schema | Council context pack structure |
| Reviewer prompts | `docs/09_prompts/v1.2/` | Current prompts | Use as role-prompt reference, not higher authority than protocol |

### E. Work item lifecycle and task schemas

| Artefact | Path | Canonical? | Notes |
| --- | --- | --- | --- |
| Runtime state ledger | `docs/11_admin/LIFEOS_STATE.md` | Canonical tracker | Current operational state |
| Runtime work tracker | `docs/11_admin/BACKLOG.md` | Canonical tracker | Actionable work tracker |
| COO schemas | `artifacts/coo/schemas.md` | Schema/reference | Contains `task_proposal.v1`, `execution_order.v1`, `escalation_packet.v1` |
| COO parser | `runtime/orchestration/coo/parser.py` | Runtime implementation | Use for actual schema parsing/enforcement reality |
| Runtime spec | `docs/03_runtime/COO_Runtime_Spec_v1.0.md` | Runtime spec | Mechanical execution contract/FSM/determinism |
| Runtime core spec | `docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md` | Runtime spec | Extended core specification |
| Build handoff protocol | `docs/02_protocols/Build_Handoff_Protocol_v1.1.md` | Protocol | Handoff architecture for agent coordination |
| Project planning protocol | `docs/02_protocols/Project_Planning_Protocol_v1.0.md` | Protocol | Mission plan requirements and lifecycle |

### F. OpenClaw / Hermes / agent runtime operations

| Artefact | Path | Canonical? | Notes |
| --- | --- | --- | --- |
| OpenClaw COO integration | `docs/02_protocols/OpenClaw_COO_Integration_v1.0.md` | Protocol | Gateway invocation, CLI wrappers, known constraints |
| OpenClaw integration wiki | `.context/wiki/openclaw-integration.md` | Derived surface | Use only if fresh against source commits |
| Multi-agent communication architecture | `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` | Proposal-only / non-canonical | Important contradiction-pressure source; loses to COO contract and ADRs |
| Agent roles reference | `docs/00_foundations/Agent_Roles_Reference_v1.0.md` | Non-authoritative orientation | Actor taxonomy and autonomy levels |
| Build loop architecture | `docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md` | Canonical per docs index | Use for autonomous build-loop semantics |
| Runtime hardening / clean build | `docs/03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md` | Spec | Use for runtime build constraints where relevant |
| OpenClaw OAuth recovery guide | `docs/02_protocols/guides/OpenClaw_Codex_OAuth_Recovery_v1.0.md` | Operational guide | Include only for current OpenClaw operational constraints |

### G. Representative examples

| Example | Path / PR / issue | Notes |
| --- | --- | --- |
| Architecture normalization reset | PR #28 | Adds architecture control surfaces and review packet |
| COO authority amendment | PR #36 | Ratifies active/standby sole-writer and Hermes/OpenClaw directionality |
| Human approval capture | PR #38 and main squashed lineage | PR body captures §9 contract and validation; final main content is authoritative |
| Drive/Workspace role | PR #39 and main squashed lineage | PR closed unmerged, but content later landed in main lineage; final main content is authoritative |
| Architecture maintenance rule | PR #40 | Event-triggered pre-merge architecture impact rule |
| Review packet: architecture normalization | `artifacts/review_packets/Review_Packet_Architecture_Normalization_Reset_v1.0.md` | Representative review artefact |
| Review packet: A1/A2 StepGate | `artifacts/review_packets/Review_Packet_A1_A2_StepGate_v1.0.md` | Representative StepGate review artefact |
| Closure process review | `artifacts/review_packets/Review_Packet_Closure_Process_20260216_v1.0.md` | Representative closure evidence process |

## 4. Known stale / non-canonical / caution surfaces

| Artefact | Path | Classification | Replacement / caution |
| --- | --- | --- | --- |
| Multi-agent communication architecture | `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` | Proposal-only, non-canonical | Loses to COO contract §§7–9 and ADR-001 through ADR-004 |
| Architecture skeleton | `docs/00_foundations/Architecture_Skeleton_v1.0.md` | Stale conceptual explainer | Use canonical target architecture instead |
| Legacy changelog | `docs/10_meta/CHANGELOG.md` | Stale repository changelog | Use `docs/10_meta/ARCHITECTURE_CHANGELOG.md` |
| Autonomy status | `docs/11_admin/AUTONOMY_STATUS.md` | Derived/stale orientation | Use canonical state/backlog and COO contract |
| Archive docs | `docs/99_archive/**` | Historical only | Not canonical unless explicitly referenced by a current canonical doc |
| PR #26/#27 claims | GitHub PRs #26/#27 | Superseded/unsafe | Use later normalization decisions and source-of-truth page |

## 5. Known open decisions / pressure points

| ID | Decision needed | Why it matters | Candidate owner |
| --- | --- | --- | --- |
| OD-001 | Whether advisory lifecycle / receipt model should be promoted from draft to canon | Current draft contains useful semantics but remains non-canonical | CEO / active COO / council if invoked |
| OD-002 | Whether work item lifecycle states need formal schema-level enforcement beyond current tracker/parser surfaces | Recent reviews identified possible review-return and closure-evidence gaps | Active COO |
| OD-003 | Whether Hermes/OpenClaw authority language should be represented as machine-checkable policy | ADR-002 is canonical prose; runtime enforcement may lag | Active COO / runtime owner |
| OD-004 | Whether approval receipts should become a dedicated typed schema rather than fields embedded in operational state | COO contract §9 defines tuple; enforcement surface may need hardening | Active COO / runtime owner |

## 6. Out of scope for the Pro audit

- Broad web research
- Tool/vendor comparison
- Generic multi-agent framework design
- New feature design not required by authority/evidence reconciliation
- Quant/trading strategy design
- Productisation strategy

## 7. Context sufficiency expectation

Categories A–F are populated for a valid audit. Category G has representative examples but should be checked for whether PR bodies, merged commits, and current main-line files agree.

The audit should proceed only after verifying that all listed paths exist at the pinned commit and that proposal-only surfaces are not accidentally treated as canonical.
