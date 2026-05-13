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
