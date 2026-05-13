# Review Packet — Drift Audit 2026-05-13 v1.0

Status: Review packet for reconciliation-only doc slice
Related tracker: `marcusglee11/lifeos-operational-bus#154`
Branch/worktree: `docs/issue-154-drift-audit` in `/home/cabra/LifeOS/.worktrees/doc-drift-audit-154`

## 1. Review scope

Review the first tracked implementation/documentation drift audit packet. This is not a canon promotion and not a broad docs rewrite.

## 2. Files changed

- `docs/10_meta/Implementation_Documentation_Drift_Audit_2026-05-13.md` — new semantic audit packet.
- `docs/INDEX.md` — discoverability/timestamp update.
- `docs/LifeOS_Universal_Corpus.md` — regenerated derived corpus.

## 3. Required review questions

1. Does the audit remain reconciliation-only?
2. Does it preserve `ARCH_Multi_Agent_Communication_Architecture.md` as proposal-only/non-canonical?
3. Does it avoid executing old issue `lifeos-operational-bus#8` as-is?
4. Are bus live state, hub reusable standards, and LifeOS programme docs kept in their proper authority lanes?
5. Are the proposed minimal follow-on doc updates appropriately bounded?
6. Are generated/index changes discoverability-only rather than hidden canon changes?

## 4. Validation run before review

- `python3 docs/scripts/generate_strategic_context.py` — PASS; no diff left in `docs/LifeOS_Strategic_Corpus.md`.
- `python3 docs/scripts/generate_corpus.py` — PASS; regenerated `docs/LifeOS_Universal_Corpus.md`.
- Full runtime tests not run: docs-only reconciliation packet; no code/runtime changes.

## 5. Authority safety notes

- No protected `docs/00_foundations/` or `docs/01_governance/` files were edited.
- `LIFEOS_STATE.md`, `ARCHITECTURE_SOURCE_OF_TRUTH.md`, and `ARCHITECTURE_CHANGELOG.md` were intentionally not edited in this first slice.
- No proposal-only/stale architecture was promoted.
- The generated universal corpus is intentionally not flattened into this packet because doing so recursively embeds this review packet inside the generated corpus and causes review-packet bloat; review should inspect the generated diff directly.

## Appendix A — Flattened semantic changed files

### `docs/10_meta/Implementation_Documentation_Drift_Audit_2026-05-13.md`

```markdown
# Implementation / Documentation Drift Audit — 2026-05-13

Status: Reconciliation packet; not a canon promotion
Owner: CEO / COO stewardship
Related tracker: `marcusglee11/lifeos-operational-bus#154`

This packet records the first bounded audit of documentation drift between LifeOS programme canon, the operational bus, the common hub, and live runtime/control-plane work that moved during May 2026.

It is deliberately not a broad documentation rewrite.

---

## 1. Scope and non-goals

### Scope

- Identify where implemented or tracked May 2026 bus/hub/runtime surfaces have moved ahead of current LifeOS documentation.
- Preserve current authority boundaries while naming stale or missing surfaces.
- Recommend the smallest documentation updates needed before any broader normalization pass.
- Provide a reviewable packet for issue `lifeos-operational-bus#154`.

### Non-goals

- No promotion of `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md`.
- No execution of the older `lifeos-operational-bus#8` promotion path as written.
- No CEO canon decision is implied by this packet.
- No rewrite of `LIFEOS_STATE.md`, `ARCHITECTURE_SOURCE_OF_TRUTH.md`, or `ARCHITECTURE_CHANGELOG.md` is performed here.
- No durable architecture mutation is claimed until a reviewed PR lands in the correct canonical repo.

---

## 2. Authority baseline

Current LifeOS authority surfaces as read for this audit:

| Surface | Current observed position | Drift implication |
| --- | --- | --- |
| `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md` | Last architecture-control entries are 2026-04-27; LifeOS canonical architecture, governance contract, state ledger, and backlog are named as current canon. The multi-agent communication architecture is explicitly proposal-only/non-canonical. | The source-of-truth page does not yet account for the May bus/hub/runtime split or newer shared-control surfaces. |
| `docs/10_meta/ARCHITECTURE_CHANGELOG.md` | Last entry is 2026-04-27 architecture maintenance checks. | May architecture-relevant movement is absent from the architecture changelog. |
| `docs/11_admin/LIFEOS_STATE.md` | `Last Updated: 2026-04-27 (rev38)`; current focus remains authority audit follow-up/schema lifecycle hardening. | Runtime/programme state is stale against May operational bus and hub activity. |
| `docs/INDEX.md` | Last updated 2026-04-27; lists architecture-control surfaces but not this May drift audit until this packet is indexed. | Discoverability needs a minimal index entry for the reconciliation packet. |
| `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` | Classified by source-of-truth as proposal-only/non-canonical. | Must not be used as a shortcut to canonize May communication/advisory semantics. |

### Fidelity vs completeness

The April LifeOS source-of-truth page appears faithful to the April architecture-normalization campaign. It is incomplete against the broader system as implemented/tracked in May across `lifeos-operational-bus`, `lifeos-common-hub`, and Hermes/runtime sidecar work.

---

## 3. Implemented surface inventory

### 3.1 LifeOS programme repo

Observed LifeOS state:

- Current primary checkout branch: `feat/openclaw-canary-upgrade-20260427`.
- Primary checkout has untracked OpenClaw upgrade/review/spec artefacts under `artifacts/`.
- The May audit work was isolated into a dedicated worktree/branch: `docs/issue-154-drift-audit`.
- Canonical authority docs still frame April state and do not yet capture May bus/hub/runtime surfaces.

### 3.2 Operational bus repo

Observed bus authority:

- `lifeos-operational-bus/README.md` defines the repo as the canonical live work-order bus.
- GitHub Issues + labels are authoritative state; project board fields are projections.
- The bus/hub boundary says live work-order state belongs in the bus, while shared schemas, standards, canon, fixtures, adapters, and memory manifests belong in the hub.
- `docs/HUB_LINKAGE.md` requires dispatch-capable payloads to include a pinned `hub_commit_sha` and gives precedence to bus issue labels for operational state.
- Active/recent tracker surfaces include `#154` plus sweep/meta-sweep/registry/receipt/control-plane issues such as `#153`, `#151`, `#150`, `#149`, `#141`, `#137`, and `#136`.

### 3.3 Common hub repo

Observed hub authority:

- `lifeos-common-hub/README.md` defines the hub as the shared source of schemas, standards, canon, fixtures, conformance, adapters, and memory manifests.
- The hub README states exactly one active COO may hold hub write authority; advisory agents are read-only unless explicitly delegated.
- Shared dispatch contract surfaces exist at:
  - `schemas/agent_dispatch_contract.schema.json`
  - `standards/agent-dispatch/README.md`
  - `tools/check_agent_dispatch_conformance.py`
- Additional May surfaces observed locally include:
  - Hermes plugin/runtime registration work under `adapters/hermes/plugins/lifeos_control_pack/`
  - dispatch schemas under `schemas/dispatch/`
  - Kanban workflow docs and mirror dry-run tooling under `docs/workflows/kanban/` and `tools/kanban_mirror_dry_run.py`
  - shared continuation/pre-stop skills under `skills/shared/`
  - Hermes continuation-question-gate patch material under `patches/`

### 3.4 Runtime/control-plane surfaces

May movement spans several control-plane concerns:

- Bus as the canonical work-order state and dispatch/status surface.
- Hub as the reusable shared schema/standard/adapter home.
- `hub_commit_sha` pinning as dispatch traceability.
- Shared dispatch contract / conformance tooling for Hermes and future OpenClaw adapters.
- Kanban surfaces as projections/workflow cockpit, not canonical operational state.
- Continuation/baton/pre-stop behaviour as shared agent protocol surface.
- Hermes plugin/runtime registration and sidecar extraction work as upgrade-survivable runtime plumbing.

---

## 4. Drift matrix

| Drift class | Current gap | Risk | Minimal remediation |
| --- | --- | --- | --- |
| Stale state | `LIFEOS_STATE.md` still says 2026-04-27 and does not reflect bus/hub/control-plane work. | Operators may treat April authority-audit follow-up as the current focus and miss May bus/hub runtime reality. | Add a concise May reconciliation entry once review approves the packet. |
| Missing source-of-truth boundary | `ARCHITECTURE_SOURCE_OF_TRUTH.md` does not yet name the bus/hub split, `hub_commit_sha`, shared hub contracts, or Kanban projection boundary. | New agents may infer authority from scattered README/issue comments or from proposal-only docs. | Add a small “May bus/hub/runtime surfaces under reconciliation” section without changing canonicality prematurely. |
| Missing changelog entry | `ARCHITECTURE_CHANGELOG.md` has no May entries. | Architecture deltas become chat/issue fog instead of durable change-control history. | Add a proposed/under-review entry for issue `#154` after review. |
| Missing bus operator orientation | LifeOS docs do not point operators to the bus README/HUB_LINKAGE as live work-order authority. | Work-order state may be duplicated into LifeOS docs or hub files. | Add a LifeOS orientation note that bus issue labels are live operational state and LifeOS docs are programme canon/orientation. |
| Missing hub surface accounting | LifeOS canon does not enumerate which May hub surfaces are shared standards vs adapters vs proposals/patches. | Reusable contracts may be mistaken for LifeOS programme architecture, or vice versa. | Add an inventory table in the approved packet/update that distinguishes shared standards, adapters, patches, and projections. |
| Proposal-only/stale-doc risk | The older multi-agent communication architecture and old promotion issue can look attractive as shortcuts. | Accidental promotion of stale/proposal-only communications architecture. | Require review to check that no proposal-only doc was promoted and issue `#8` was not executed mechanically. |
| Missing receipt/state model | LifeOS docs do not yet state how bus issues, hub SHAs, PR receipts, review packets, and Kanban projections relate. | Agents may treat dashboards, comments, or unmerged docs as completion truth. | Add a lifecycle/receipt map before changing canon. |
| Missing failure/ops semantics | Dispatch trigger caveats, Codex-lane blockage risks, and hub dirty/untracked surfaces live in issues/skills rather than programme docs. | Dispatch or doc promotion may run with stale assumptions. | Keep these as operational caveats in bus issues/runbooks first; promote only stable semantics into LifeOS/hub docs. |

---

## 5. Proposed minimal doc updates

These are proposed follow-on updates, not performed by this packet except for indexing this packet.

1. `docs/11_admin/LIFEOS_STATE.md`
   - Add a short May 2026 note: documentation is behind bus/hub/runtime implementation; issue `lifeos-operational-bus#154` owns reconciliation.
   - Do not convert the state ledger into the full architecture packet.

2. `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md`
   - Add a bounded section for bus/hub/runtime authority boundaries under reconciliation.
   - Preserve `ARCH_Multi_Agent_Communication_Architecture.md` as proposal-only/non-canonical.
   - State that Kanban/dashboards are projections unless separately ratified.

3. `docs/10_meta/ARCHITECTURE_CHANGELOG.md`
   - Add one proposed/under-review entry for issue `#154` describing reconciliation of implemented bus/hub/runtime surfaces.
   - Do not add ADRs unless Marcus ratifies a new authority decision.

4. `docs/INDEX.md`
   - Index this audit packet for discoverability.
   - Refresh timestamp per doc stewardship.

5. Review packet under `docs/10_meta/`
   - Provide a flattened review packet before merge.
   - Acceptance must explicitly check that proposal-only communications docs were not promoted accidentally.

6. Optional later operator runbook links
   - Add LifeOS-level orientation links to bus/hub READMEs only after the authority text is approved.

---

## 6. Review gate

Before this audit or any derived doc update is merged, review must confirm:

- The packet is reconciliation-only and does not imply CEO canon ratification.
- `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md` remains proposal-only/non-canonical.
- Issue `lifeos-operational-bus#8` is not executed mechanically or treated as current instruction.
- Bus live state remains authoritative in `lifeos-operational-bus` issues/labels.
- Hub reusable standards/schemas/adapters remain in `lifeos-common-hub`.
- LifeOS programme docs receive only the minimal orientation/control updates needed to prevent drift.
- Kanban, dashboards, briefs, and generated corpora are labeled as projections/derived surfaces where referenced.
- Any later architecture-control edits update the source-of-truth page, architecture changelog, and ADR register only when their existing trigger rules require it.

---

## 7. Current packet change-control status

- Created in isolated LifeOS worktree: `docs/issue-154-drift-audit`.
- Changed files expected for this slice:
  - `docs/10_meta/Implementation_Documentation_Drift_Audit_2026-05-13.md`
  - `docs/INDEX.md`
  - generated corpus files if doc stewardship regeneration changes them
  - review packet for this slice if prepared before PR/review
- Canonical authority docs intentionally not edited in this slice:
  - `docs/11_admin/LIFEOS_STATE.md`
  - `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md`
  - `docs/10_meta/ARCHITECTURE_CHANGELOG.md`
  - `docs/00_foundations/ARCH_Multi_Agent_Communication_Architecture.md`

```

### `docs/INDEX.md`

```markdown
# LifeOS Strategic Corpus [P26-02-28 (rev12)]

<!-- markdownlint-disable MD013 MD040 MD060 -->

Last Updated: 2026-05-13 (rev23)

**Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)

---

## Authority Chain

```
LifeOS Constitution v2.0 (Supreme)
        │
        └── Governance Protocol v1.0
                │
                ├── COO Operating Contract v1.0
                ├── DAP v2.0
                └── COO Runtime Spec v1.0
```

---

## Strategic Context

| Document | Purpose |
|----------|---------|
| [LifeOS_Strategic_Corpus.md](./LifeOS_Strategic_Corpus.md) | **Primary Context for the LifeOS Project** |

---

## Agent Guidance (Root Level)

| File | Purpose |
|------|---------|
| [CLAUDE.md](../CLAUDE.md) | Claude Code (claude.ai/code) agent guidance |
| [AGENTS.md](../AGENTS.md) | OpenCode agent instructions (Doc Steward subset) |
| [GEMINI.md](../GEMINI.md) | Gemini agent constitution |

---

## 00_admin — Project Admin (Thin Control Plane)

### Canonical Files

| Document | Purpose |
|----------|---------|
| [LIFEOS_STATE.md](./11_admin/LIFEOS_STATE.md) | **Single source of truth** — Current focus, WIP, blockers, next actions (auto-updated) |
| [BACKLOG.md](./11_admin/BACKLOG.md) | **Canonical backlog** — Actionable backlog (Now/Next/Later), target ≤40 items (auto-updated) |
| [DECISIONS.md](./11_admin/DECISIONS.md) | **Append-only** — Decision log (low volume) |
| [INBOX.md](./11_admin/INBOX.md) | Raw capture scratchpad for triage |
| [Plan_Supersession_Register.md](./11_admin/Plan_Supersession_Register.md) | **Control** — Canonical register of superseded and active plans |
| [LifeOS_Build_Loop_Production_Plan_v2.1.md](./11_admin/LifeOS_Build_Loop_Production_Plan_v2.1.md) | **Canonical plan** — Production readiness plan (per supersession register) |
| [LifeOS_Master_Execution_Plan_v1.1.md](./11_admin/LifeOS_Master_Execution_Plan_v1.1.md) | (superseded by v2.1) — Historical master execution plan W0–W7 |
| [Doc_Freshness_Gate_Spec_v1.0.md](./11_admin/Doc_Freshness_Gate_Spec_v1.0.md) | **Control** — Runtime-backed doc freshness and contradiction gate spec |
| [AUTONOMY_STATUS.md](./11_admin/AUTONOMY_STATUS.md) | **Derived view** — Autonomy capability matrix (derived from canonical sources) |
| [WIP_LOG.md](./11_admin/WIP_LOG.md) | **WIP tracker** — Work-in-progress log with controlled status enum |
| [lifeos-master-operating-manual-v2.1.md](./11_admin/lifeos-master-operating-manual-v2.1.md) | **Strategic context** — Master Operating Manual v2.1 |
| [TECH_DEBT_INVENTORY.md](./11_admin/TECH_DEBT_INVENTORY.md) | **Tech debt tracker** — Structural debt items with explicit trigger conditions |
| [QUALITY_AUDIT_BASELINE_v1.0.md](./11_admin/QUALITY_AUDIT_BASELINE_v1.0.md) | **Audit baseline** — Repo-wide quality findings, evidence, and promotion recommendations |
| [build_summaries/COO_Step6_LiveWiring_Build_Summary_2026-03-08.md](./11_admin/build_summaries/COO_Step6_LiveWiring_Build_Summary_2026-03-08.md) | COO Step 6 build summary — live wiring, shadow validation, gaps, workflow |

### Subdirectories

| Directory | Purpose | Naming Rule |
|-----------|---------|-------------|
| `build_summaries/` | Timestamped build evidence summaries | `*_Build_Summary_YYYY-MM-DD.md` |
| `archive/` | Historical documents (reference only; immutable) | Archive subdirs: `YYYY-MM-DD_<topic>/` |

---

## 00_foundations — Core Principles

| Document | Purpose |
|----------|---------|
| [LifeOS_Constitution_v2.0.md](./00_foundations/LifeOS_Constitution_v2.0.md) | **Supreme governing document** — Raison d'être, invariants, principles |
| [LifeOS Target Architecture v2.3c](./00_foundations/LifeOS%20Target%20Architecture%20v2.3c.md) | **Current canonical target architecture** — CEO→COO→EA control-plane, COO Commons, phased authority expansion |
| [Agent_Roles_Reference_v1.0.md](./00_foundations/Agent_Roles_Reference_v1.0.md) | Orientation reference — actor taxonomy, COO autonomy levels, provider routing (non-authoritative; canon wins on conflict) |
| [Anti_Failure_Operational_Packet_v0.1.md](./00_foundations/Anti_Failure_Operational_Packet_v0.1.md) | Anti-failure mechanisms, human preservation, workflow constraints |
| [Architecture_Skeleton_v1.0.md](./00_foundations/Architecture_Skeleton_v1.0.md) | High-level conceptual architecture (CEO/COO/Worker layers) |
| [Tier_Definition_Spec_v1.1.md](./00_foundations/Tier_Definition_Spec_v1.1.md) | **Canonical** — Tier progression model, definitions, and capabilities |
| [ARCH_Future_Build_Automation_Operating_Model_v0.2.md](./00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md) | **Architecture Proposal** — Future Build Automation Operating Model v0.2 |
| [lifeos-agent-architecture.md](./00_foundations/lifeos-agent-architecture.md) | **Architecture** — Non-canonical agent architecture |
| [lifeos-maximum-vision.md](./00_foundations/lifeos-maximum-vision.md) | **Vision** — Non-canonical maximum vision architecture |

---

## 01_governance — Governance & Contracts

### Core Governance

| Document | Purpose |
|----------|---------|
| [COO_Operating_Contract_v1.0.md](./01_governance/COO_Operating_Contract_v1.0.md) | CEO/COO role boundaries and interaction rules |
| [AgentConstitution_GEMINI_Template_v1.0.md](./01_governance/AgentConstitution_GEMINI_Template_v1.0.md) | Template for agent GEMINI.md files |
| [DOC_STEWARD_Constitution_v1.0.md](./01_governance/DOC_STEWARD_Constitution_v1.0.md) | Document Steward constitutional boundaries |

### Council & Review

| Document | Purpose |
|----------|---------|
| [Council_Invocation_Runtime_Binding_Spec_v1.1.md](./01_governance/Council_Invocation_Runtime_Binding_Spec_v1.1.md) | Council invocation and runtime binding |
| [Antigravity_Council_Review_Packet_Spec_v1.0.md](./01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md) | Council review packet format |
| [ALIGNMENT_REVIEW_TEMPLATE_v1.0.md](./01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md) | Monthly/quarterly alignment review template |

### Policies & Logs

| Document | Purpose |
|----------|---------|
| [COO_Expectations_Log_v1.0.md](./01_governance/COO_Expectations_Log_v1.0.md) | Working preferences and behavioral refinements |
| [Antigrav_Output_Hygiene_Policy_v0.1.md](./01_governance/Antigrav_Output_Hygiene_Policy_v0.1.md) | Output path rules for Antigravity |
| [OpenCode_First_Stewardship_Policy_v1.1.md](./01_governance/OpenCode_First_Stewardship_Policy_v1.1.md) | **Mandatory** OpenCode routing for in-envelope docs |

### Active Rulings

| Document | Purpose |
|----------|---------|
| [Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md](./01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md) | **ACTIVE** — OpenCode Document Steward CT-2 Phase 2 Activation |
| [Council_Ruling_OpenCode_First_Stewardship_v1.1.md](./01_governance/Council_Ruling_OpenCode_First_Stewardship_v1.1.md) | **ACTIVE** — OpenCode-First Doc Stewardship Adoption |
| [Council_Ruling_Build_Handoff_v1.0.md](./01_governance/Council_Ruling_Build_Handoff_v1.0.md) | **Approved**: Build Handoff Protocol v1.0 activation-canonical |
| [Council_Ruling_Build_Loop_Architecture_v1.0.md](./01_governance/Council_Ruling_Build_Loop_Architecture_v1.0.md) | **ACTIVE**: Build Loop Architecture v0.3 authorised for Phase 1 |
| [Council_Ruling_Phase9_Ops_Ratification_v1.0.md](./01_governance/Council_Ruling_Phase9_Ops_Ratification_v1.0.md) | **ACTIVE** — Phase 9 constrained ops ratification for `workspace_mutation_v1` |
| [Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md](./01_governance/Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md) | **Active**: Reactive Task Layer v0.1 Signoff |
| [Council_Review_Stewardship_Runner_v1.0.md](./01_governance/Council_Review_Stewardship_Runner_v1.0.md) | **Approved**: Stewardship Runner cleared for agent-triggered runs |

### Historical Rulings

| Document | Purpose |
|----------|---------|
| [Tier1_Hardening_Council_Ruling_v0.1.md](./01_governance/Tier1_Hardening_Council_Ruling_v0.1.md) | Historical: Tier-1 ratification ruling |
| [Tier1_Tier2_Activation_Ruling_v0.2.md](./01_governance/Tier1_Tier2_Activation_Ruling_v0.2.md) | Historical: Tier-2 activation ruling |
| [Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md](./01_governance/Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md) | Historical: Tier transition conditions |
| [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](./01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md) | Historical: Tier-2.5 activation ruling |

---

## 02_protocols — Protocols & Agent Communication

### Batch 1 Runtime Protocols

> **Note:** The 5 Batch 1 runtime modules (`run_lock`, `invocation_receipt`, `invocation_schema`, `shadow_runner`, `shadow_capture`) do not yet have dedicated protocol docs in `02_protocols/`. Their protocol definitions are captured in:

| Document | Coverage |
|----------|---------|
| [LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md](./03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md) | **Batch 1**: run_lock, invocation_receipt, invocation_schema, shadow_runner, shadow_capture — autonomous build loop protocol definitions |

### Core Protocols

| Document | Purpose |
|----------|---------|
| [Governance_Protocol_v1.0.md](./02_protocols/Governance_Protocol_v1.0.md) | Envelopes, escalation rules, council model |
| [Git_Workflow_Protocol_v1.1.md](./02_protocols/Git_Workflow_Protocol_v1.1.md) | **Fail-Closed**: Branch conventions, CI proof merging, receipts |
| [Document_Steward_Protocol_v1.1.md](./02_protocols/Document_Steward_Protocol_v1.1.md) | Document creation, indexing, GitHub/Drive sync |
| [Deterministic_Artefact_Protocol_v2.0.md](./02_protocols/Deterministic_Artefact_Protocol_v2.0.md) | DAP — artefact creation, versioning, and storage rules |
| [Build_Artifact_Protocol_v1.0.md](./02_protocols/Build_Artifact_Protocol_v1.0.md) | **NEW** — Formal schemas/templates for Plans, Review Packets, Walkthroughs, etc. |
| [Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md](./02_protocols/Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md) | Tier-2 API Versioning, Deprecation, and Compatibility Rules |
| [Build_Handoff_Protocol_v1.1.md](./02_protocols/Build_Handoff_Protocol_v1.1.md) | Messaging & handoff architecture for agent coordination |
| [Intent_Routing_Rule_v1.1.md](./02_protocols/Intent_Routing_Rule_v1.1.md) | Decision routing (CEO/CSO/Council/Runtime) |
| [LifeOS_Design_Principles_Protocol_v1.1.md](./02_protocols/LifeOS_Design_Principles_Protocol_v1.1.md) | **Canonical** — "Prove then Harden" development principles, Output-First governance, sandbox workflow |
| [Emergency_Declaration_Protocol_v1.0.md](./02_protocols/Emergency_Declaration_Protocol_v1.0.md) | **Canonical** — Emergency override and auto-revert procedures |
| [Test_Protocol_v2.0.md](./02_protocols/Test_Protocol_v2.0.md) | **WIP** — Test categories, coverage, and flake policy |
| [EOL_Policy_v1.0.md](./02_protocols/EOL_Policy_v1.0.md) | **Canonical** — LF line endings, config compliance, clean invariant enforcement |
| [Filesystem_Error_Boundary_Protocol_v1.0.md](./02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md) | **Draft** — Fail-closed filesystem error boundaries, exception taxonomy |
| [GitHub_Actions_Secrets_Setup.md](./02_protocols/GitHub_Actions_Secrets_Setup.md) | PAT creation, secrets config, and rotation for CI workflows |
| [Project_Planning_Protocol_v1.0.md](./02_protocols/Project_Planning_Protocol_v1.0.md) | Build mission plan requirements, schema compliance, lifecycle, and review rubric |
| [OpenClaw_COO_Integration_v1.0.md](./02_protocols/OpenClaw_COO_Integration_v1.0.md) | OpenClaw gateway invocation, CLI wrappers, known constraints |

### Council Protocols

| Document | Purpose |
|----------|---------|
| [Council_Protocol_v1.3.md](./02_protocols/Council_Protocol_v1.3.md) | **Canonical** — Council review procedure, modes, topologies, P0 criteria, complexity budget |
| [AI_Council_Procedural_Spec_v1.1.md](./02_protocols/AI_Council_Procedural_Spec_v1.1.md) | Runbook for executing Council Protocol v1.2 |
| [Council_Context_Pack_Schema_v0.3.md](./02_protocols/Council_Context_Pack_Schema_v0.3.md) | CCP template schema for council reviews |

### Packet & Artifact Schemas

| Document | Purpose |
|----------|---------|
| [lifeos_packet_schemas_v1.yaml](./02_protocols/lifeos_packet_schemas_v1.yaml) | Agent packet schema definitions (13 packet types) |
| [lifeos_packet_templates_v1.yaml](./02_protocols/lifeos_packet_templates_v1.yaml) | Ready-to-use packet templates |
| [build_artifact_schemas_v1.yaml](./02_protocols/build_artifact_schemas_v1.yaml) | **NEW** — Build artifact schema definitions (6 artifact types) |
| [templates/](./02_protocols/templates/) | **NEW** — Markdown templates for all artifact types |
| [example_converted_antigravity_packet.yaml](./02_protocols/example_converted_antigravity_packet.yaml) | Example: converted Antigravity review packet |

### Operational Guides

| Document | Purpose |
|----------|---------|
| [guides/OpenClaw_Codex_OAuth_Recovery_v1.0.md](./02_protocols/guides/OpenClaw_Codex_OAuth_Recovery_v1.0.md) | Recovery flow for stale `openai-codex` auth ordering, `refresh_token_reused`, and secrets reload validation |

---

## 03_runtime — Runtime Specification

### Core Specs

| Document | Purpose |
|----------|---------|
| [COO_Runtime_Spec_v1.0.md](./03_runtime/COO_Runtime_Spec_v1.0.md) | Mechanical execution contract, FSM, determinism rules |
| [COO_Runtime_Implementation_Packet_v1.0.md](./03_runtime/COO_Runtime_Implementation_Packet_v1.0.md) | Implementation details for Antigravity |
| [COO_Runtime_Core_Spec_v1.0.md](./03_runtime/COO_Runtime_Core_Spec_v1.0.md) | Extended core specification |
| [COO_Runtime_Spec_Index_v1.0.md](./03_runtime/COO_Runtime_Spec_Index_v1.0.md) | Spec index and patch log |
| [LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md](./03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md) | **Canonical**: Autonomous Build Loop Architecture (Council-authorised) |
| [Council_Agent_Design_v1.0.md](./03_runtime/Council_Agent_Design_v1.0.md) | **Information Only** — Conceptual design for the Council Agent |

### Roadmaps & Plans

| Document | Purpose |
|----------|---------|
| [LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md](./03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md) | **Current roadmap** — Core/Fuel/Plumbing tracks |
| [LifeOS_Recursive_Improvement_Architecture_v0.2.md](./03_runtime/LifeOS_Recursive_Improvement_Architecture_v0.2.md) | Recursive improvement architecture |
| [LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md](./03_runtime/LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md) | Future router and executor adapter spec |
| [LifeOS_Plan_SelfBuilding_Loop_v2.2.md](./03_runtime/LifeOS_Plan_SelfBuilding_Loop_v2.2.md) | **Plan**: Self-Building LifeOS — CEO Out of the Execution Loop (Milestone) |

### Work Plans & Fix Packs

| Document | Purpose |
|----------|---------|
| [Hardening_Backlog_v0.1.md](./03_runtime/Hardening_Backlog_v0.1.md) | Hardening work backlog |
| [Tier1_Hardening_Work_Plan_v0.1.md](./03_runtime/Tier1_Hardening_Work_Plan_v0.1.md) | Tier-1 hardening work plan |
| [Tier2.5_Unified_Fix_Plan_v1.0.md](./03_runtime/Tier2.5_Unified_Fix_Plan_v1.0.md) | Tier-2.5 unified fix plan |
| [F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md](./03_runtime/F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md) | Tier-2.5 activation conditions checklist (F3) |
| [F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md](./03_runtime/F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md) | Tier-2.5 deactivation and rollback conditions (F4) |
| [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](./03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md) | Runtime↔Antigrav mission protocol (F7) |
| [Runtime_Hardening_Fix_Pack_v0.1.md](./03_runtime/Runtime_Hardening_Fix_Pack_v0.1.md) | Runtime hardening fix pack |
| [fixpacks/FP-4x_Implementation_Packet_v0.1.md](./03_runtime/fixpacks/FP-4x_Implementation_Packet_v0.1.md) | FP-4x implementation |

### Templates & Tools

| Document | Purpose |
|----------|---------|
| [BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md](./03_runtime/BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md) | Build starter prompt template |
| [CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md](./03_runtime/CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md) | Code review prompt template |
| [COO_Runtime_Walkthrough_v1.0.md](./03_runtime/COO_Runtime_Walkthrough_v1.0.md) | Runtime walkthrough |
| [COO_Runtime_Clean_Build_Spec_v1.1.md](./03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md) | Clean build specification |

### Other

| Document | Purpose |
|----------|---------|
| [Automation_Proposal_v0.1.md](./03_runtime/Automation_Proposal_v0.1.md) | Automation proposal |
| [Runtime_Complexity_Constraints_v0.1.md](./03_runtime/Runtime_Complexity_Constraints_v0.1.md) | Complexity constraints |
| [README_Recursive_Kernel_v0.1.md](./03_runtime/README_Recursive_Kernel_v0.1.md) | Recursive kernel readme |

---

## 12_productisation — Productisation & Marketing

| Document | Purpose |
|----------|---------|
| [An_OS_for_Life.mp4](./12_productisation/assets/An_OS_for_Life.mp4) | **Promotional Video** — An introduction to LifeOS |

---

## internal — Internal Reports

| Document | Purpose |
|----------|---------|
| [OpenCode_Phase0_Completion_Report_v1.0.md](./internal/OpenCode_Phase0_Completion_Report_v1.0.md) | OpenCode Phase 0 API connectivity validation — PASSED |

---

## 10_meta — Meta / Architecture Control

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE_SOURCE_OF_TRUTH.md](./10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md) | **Orientation surface** — Current canon / proposal / stale map for architecture control |
| [ARCHITECTURE_CHANGELOG.md](./10_meta/ARCHITECTURE_CHANGELOG.md) | **Control log** — Architecture deltas and their status |
| [Implementation_Documentation_Drift_Audit_2026-05-13.md](./10_meta/Implementation_Documentation_Drift_Audit_2026-05-13.md) | **Reconciliation packet** — May 2026 bus/hub/runtime implementation vs LifeOS documentation drift audit; no canon promotion |
| [Review_Packet_Drift_Audit_2026-05-13_v1.0.md](./10_meta/Review_Packet_Drift_Audit_2026-05-13_v1.0.md) | **Review packet** — Flattened review materials for the May 2026 drift audit packet |
| [Architecture_Normalization_Reconciliation_Packet_2026-04-24.md](./10_meta/Architecture_Normalization_Reconciliation_Packet_2026-04-24.md) | **Normalization packet** — Canon, authority, writer boundaries, mismatch matrix |
| [COO_Authority_Contract_Draft_2026-04-24.md](./10_meta/COO_Authority_Contract_Draft_2026-04-24.md) | **Decision draft** — Approval, proxy authority, active/standby, sole-writer boundaries |
| [architecture_decisions/INDEX.md](./10_meta/architecture_decisions/INDEX.md) | **ADR register** — Ratified architecture decisions only |
| [Architecture_Normalization_Targeted_Issue_List_2026-04-24.md](./10_meta/Architecture_Normalization_Targeted_Issue_List_2026-04-24.md) | **Issue draft** — Targeted follow-on issues derived from reconciliation packet |

---

## 99_archive — Historical Documents

Archived documents are in `99_archive/`. Key locations:

- `99_archive/superseded_by_constitution_v2/` — Documents superseded by Constitution v2.0
- `99_archive/legacy_structures/` — Legacy governance and specs
- `99_archive/lifeos-master-operating-manual-v2.md` — Preceding version of the master operations manual
- `99_archive/lifeos-operations-manual.md` — First version of the master operations manual

---

## Other Directories

| Directory | Contents |
|-----------|----------|
| `04_project_builder/` | Project builder specs |
| `05_agents/` | Agent architecture |
| `06_user_surface/` | User surface specs |
| `08_manuals/` | Operational manuals (COO Doc Management, Governance Runtime) |
| `09_prompts/v1.0/` | Legacy v1.0 prompt templates |
| `09_prompts/v1.2/` | **Current** — Council role prompts (Chair, Co-Chair, 10 reviewer seats) |
| `10_meta/` | Meta documents, reviews, tasks |

---

## 08_manuals — Operational Manuals

| Document | Purpose |
|----------|---------|
| [COO_Doc_Management_Manual_v1.0.md](./08_manuals/COO_Doc_Management_Manual_v1.0.md) | **Executable runbook** — Doc stewardship operations, validators, governance boundaries |
| [Governance_Runtime_Manual_v1.0.md](./08_manuals/Governance_Runtime_Manual_v1.0.md) | Governance runtime operations |

<!-- markdownlint-enable MD013 MD040 MD060 -->

```

