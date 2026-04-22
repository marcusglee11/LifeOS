# Multi-Agent Communication Architecture

Status: Draft  
Owner: CEO  
Purpose: Define the authoritative communication architecture for advisory agents, the COO, EAs, and system buses/adapters.  
Design posture: fail-closed, typed ingress, deterministic promotion, audit-first

---

## 1. Core framing

### 1.1 Primary model

LifeOS uses **one primary operational bus: GitHub**.

Google Drive is **not** a peer bus. It is an asynchronous adapter and briefing mirror for agents that cannot reliably access the primary operational bus directly.

### 1.2 Roles

- **CEO** — directs priorities, approves gated actions, receives escalations
- **COO** — control plane; validates ingress, classifies proposals, applies gates, promotes approved work, reconciles execution truth
- **Advisory agents** — propose work; never write operational state directly
- **Execution agents (EAs)** — execute promoted work orders and return results to GitHub
- **GitHub** — authoritative store for operational artefacts and audit trail
- **Google Drive** — constrained-agent ingress adapter and bounded briefing projection
- **Telegram** — CEO ↔ COO approval and escalation channel

### 1.3 Architectural invariant

All execution-relevant work must cross an explicit authority boundary:

**advisory ingress → COO validation/classification → CEO/policy gate → promotion → operational work order**

No advisory artefact is a command.

---

## 2. Authority boundary

### 2.1 Operational state

**Operational state** is any artefact the COO, EAs, or CI treat as authoritative input to execution or gating.

Operational state includes:

- work orders
- Schema A command envelopes
- PR-linked execution state
- CI results used for gating
- approval receipts
- promotion receipts
- reconciliation receipts
- completion and closure receipts

### 2.2 Non-operational state

The following are explicitly **non-operational**:

- advisory issues
- Drive proposal files
- rejection notes
- briefing projections
- advisory archives
- drafts, notes, and bootstrap material

These may inform decisions but do not authorize execution.

### 2.3 Sole-writer rule

The **COO is the sole writer of operational state**.

Advisory agents may write ingress artefacts only.

### 2.4 Boundary crossing

An advisory artefact becomes operational only when the COO:

1. validates it
2. classifies it
3. obtains required approval or policy clearance
4. translates it into Schema A
5. emits a promotion receipt

That act is the only authority boundary crossing.

---

## 3. Topology

### 3.1 Primary operational path

- GitHub hosts authoritative operational artefacts
- COO ingests GitHub events by webhook
- EAs execute against promoted work orders and write results back into GitHub
- COO reconciles GitHub truth and updates state

### 3.2 Advisory ingress paths

#### 3.2.1 ChatGPT advisory ingress

ChatGPT may write directly to GitHub using a dedicated **advisory issue class**.

This is advisory ingress only. It is not operational state.

#### 3.2.2 Claude advisory ingress

Claude writes proposal YAML files into Drive:

- `advisory/inbox/`
- optional re-read of `briefing/current.md` at session start

The COO polls or receives change notifications, validates the file, and translates conforming ingress into the same internal advisory lifecycle used for GitHub-origin ingress.

### 3.3 CEO channel

CEO commands, approvals, and escalations route through Telegram.

Telegram approvals do not directly change GitHub state. They authorize the COO to do so, subject to approval binding rules.

---

## 4. Ingress contracts

### 4.1 GitHub advisory ingress

GitHub advisory ingress must use a required typed body block or issue template payload.

Labels are **projections only** and are not trusted as the authoritative type signal.

Required properties:

- stable advisory issue class marker in body/template
- typed proposal payload
- proposal version
- content suitable for deterministic hashing

### 4.2 Drive advisory ingress

Drive advisory ingress is a validated YAML file.

Filename is convenience only. Authority comes from:

- validated payload
- Drive metadata
- COO-assigned processing metadata

### 4.3 Trust posture by phase

#### Phase 1

Drive-origin ingress is **unauthenticated**. `session_hash` is metadata only and not proof of identity.

Implications:

- Drive-origin proposals require explicit CEO approval before promotion
- Drive-origin proposals are treated as untrusted advisory input

#### Phase 2+

Drive-origin ingress is authenticated via per-agent OAuth service accounts.

The COO binds writer identity from Drive metadata such as `lastModifyingUser`.

### 4.4 Fail-closed ingress rule

Ingress missing its typed payload is invalid.

A label alone is insufficient. Malformed YAML is invalid. Invalid ingress cannot be promoted.

---

## 5. Advisory proposal schema

### 5.1 Required fields

```yaml
schema_version: "1.0"
proposal_id: "{uuid-or-empty-on-ingress}"
requester:
  agent: "claude" | "chatgpt" | "other"
  session_hash: "{opaque_metadata_or_empty}"
  on_behalf_of: "CEO"
submitted_at: "{iso8601}"

intent:
  title: "{short imperative}"
  summary: "{2-4 sentences}"
  category: "infra" | "governance" | "content" | "research" | "ops" | "other"

target:
  repo: "{repo_identifier}"
  surface: "{path|component|surface_identifier}"

requested_outcome_type: "pr" | "issue" | "doc" | "config_change" | "research_output" | "other"

proposed_work:
  decomposition:
    - "{step}"
  suggested_ea: "claude_code" | "codex_cli" | "either" | null
  estimated_scope: "small" | "medium" | "large"
  reversibility: "reversible" | "reversible_with_effort" | "irreversible"

risk_class: "routine" | "elevated" | "novel"

risk_assessment:
  failure_modes:
    - "{mode}"
  blast_radius: "local" | "repo" | "system" | "external"
  mitigations: "{briefly}"

expected_evidence:
  - "{artefact or receipt expected on completion}"

dedupe_key: "{agent_computed_hint}"

provenance:
  source_context: "{origin context}"
  related_issues: ["{id}"]
  related_docs: ["{path}"]
```

### 5.2 Optional human-review fields

These may be present for CEO review but are excluded from fingerprinting unless explicitly version-changed into the fingerprint set:

- `alternatives_considered`
- `why_now`

### 5.3 Risk classification authority

The agent may self-declare `risk_class`.

The COO may:

- upgrade `risk_class`
- not downgrade `risk_class` without an explicit logged rationale and CEO-visible note

Default enforcement: if uncertain, classify upward.

---

## 6. Identity, fingerprinting, and dedupe

### 6.1 proposal_id

`proposal_id` is assigned by the COO on discovery if not already present.

It is a stable lifecycle identifier.

### 6.2 proposal_fingerprint

`proposal_fingerprint` is a deterministic hash over a canonicalized subset of fields:

- `intent`
- `target`
- `requested_outcome_type`
- `proposed_work`
- `risk_class`
- `dedupe_key`

Excluded from the fingerprint:

- `submitted_at`
- `session_hash`
- freeform provenance prose
- archive metadata
- rejection metadata

Reason: cosmetic or transport-only changes must not invalidate an otherwise identical proposal.

### 6.3 dedupe_key

`dedupe_key` is a deterministic hash over:

- `target.repo`
- `target.surface`
- `requested_outcome_type`
- normalized intent slug

The agent may provide a candidate value. The COO recomputes and validates it. The COO-computed value is authoritative.

### 6.4 Canonicalization

All hashes must be computed over canonicalized structured content.

The same semantic content must yield the same hash independent of field order or whitespace.

---

## 7. Processing state machine

### 7.1 States

`discovered → validated | rejected → classified(duplicate | conflicting | admissible | inadmissible) → held | approved → promoted | withdrawn → archived`

### 7.2 State meanings

- **discovered** — ingress observed and assigned processing metadata
- **validated** — schema-valid and structurally admissible
- **rejected** — structurally invalid or missing typed contract
- **duplicate** — materially the same as an open proposal or work order
- **conflicting** — materially overlapping or incompatible with another active proposal or work order
- **admissible** — eligible for approval evaluation
- **inadmissible** — valid structure but disallowed by current policy
- **held** — awaiting CEO decision or dependency resolution
- **approved** — approval bound and still valid
- **promoted** — translated into operational state via Schema A plus promotion receipt
- **withdrawn** — explicitly abandoned before promotion
- **archived** — lifecycle closed with no further action

### 7.3 Terminal states

Terminal states:

- `promoted`
- `withdrawn`
- `archived`

### 7.4 Receipt rule

Any transition into a terminal state requires a logged receipt:

- rejection receipt
- withdrawal receipt
- promotion receipt
- archive-without-promotion receipt

### 7.5 Reversibility

Non-terminal transitions may be reversed only within the same advisory lifecycle and only with logged rationale.

Terminal states are not reversible. Any later action must create a new advisory lifecycle.

### 7.6 Idempotence

COO processing is idempotent on:

`(proposal_fingerprint, source_event_id)`

Replays must not create duplicate promotions or duplicate terminal receipts.

---

## 8. Approval binding

### 8.1 Binding tuple

CEO approval binds to:

`(proposal_id, proposal_fingerprint, rendered_summary_hash)`

If any element changes before promotion, approval is invalid and re-approval is required.

### 8.2 Deterministic rendering

When the COO presents a proposal to the CEO for approval, it must render a deterministic summary using a versioned template.

That rendered summary:

- is archived
- is hashable
- is the exact content the CEO approved

### 8.3 Approval drift protection

If the underlying proposal changes after approval, the COO recomputes:

- `proposal_fingerprint`
- `rendered_summary_hash`

Mismatch blocks promotion automatically.

### 8.4 Telegram approval contract

Telegram approvals must reference at least:

- `proposal_id`
- rendered summary token or fingerprint
- approval action

The COO records the approval receipt and links it to the advisory lifecycle.

---

## 9. Promotion flow

### 9.1 Ingress arrival

Ingress arrives from either:

- GitHub advisory issue class
- Drive proposal file

### 9.2 Discovery

The COO assigns:

- processing timestamp
- source origin
- source event identity
- `proposal_id` if absent

### 9.3 Validation

The COO validates the advisory payload against the advisory schema.

Invalid ingress:

- fail closed
- emit rejection receipt
- write rejection note back to source if possible

### 9.4 Classification

The COO classifies valid ingress as one of:

- duplicate
- conflicting
- admissible
- inadmissible

### 9.5 Gate application

For admissible proposals:

#### Phase 1

All promotions require CEO approval.

#### Phase 2+

Routine classes may auto-promote if allowed by policy.

Novel or elevated classes escalate automatically.

### 9.6 Translation

Approved proposals are translated by the COO into Schema A command envelopes.

This translation is explicit and logged.

### 9.7 Promotion receipt

Promotion emits:

- Schema A artefact reference
- source advisory reference
- `proposal_id`
- `proposal_fingerprint`
- linked approval receipt
- timestamp
- actor = COO

---

## 10. Briefing projection

### 10.1 Nature of briefing

`briefing/current.md` is a **projection**, not authority.

It exists to bootstrap constrained agents with current context.

Agents may not infer:

- approvals
- state transitions
- execution truth

from briefing alone.

### 10.2 Required metadata

The briefing must include:

- `generated_at`
- `source_cursor` or `last_event_id`
- `projection_policy_version`
- `freshness_window`
- authoritative GitHub references

### 10.3 Projection trigger policy

Briefing refresh is event-driven on the following GitHub event classes only:

- advisory proposal created
- advisory proposal terminalized
- work order opened
- work order status materially changed
- PR opened, merged, or closed for an active work order
- CI result changed for an active work order
- promotion receipt created
- closure or completion receipt created

No vague “phase-significant” standard is permitted.

### 10.4 Freshness rule

If briefing age exceeds `freshness_window`, it is informational only.

Default Phase 1 freshness window:

- 30 minutes

Stale briefing must not be used as sole decision context for new advisory proposals.

### 10.5 Write-failure rule

If briefing refresh fails:

- operational flow continues
- failure is logged
- briefing is marked stale until successful regeneration

---

## 11. Rejections and archives

### 11.1 Rejection contract

Rejections write a typed artefact containing:

- `proposal_id`
- `rejected_at`
- `reason_code`
- `human_readable_reason`
- `remediation_hint`

### 11.2 Duplicate disposition

Duplicates are not silently discarded.

The COO records:

- matched active proposal or work order
- dedupe basis
- disposition
- timestamp

### 11.3 Conflict disposition

Conflicts create a bundled decision packet for CEO review rather than arbitrary first-wins promotion.

### 11.4 Archive rule

Every completed advisory lifecycle is archived with enough metadata to reconstruct:

- origin
- fingerprint
- classification
- approval status
- terminal disposition

---

## 12. Failure modes and controls

### 12.1 Ingress ambiguity

**Problem:** GitHub issue has advisory label but no typed payload.  
**Control:** Fail closed. Invalid ingress. Reject.

### 12.2 Drive spoofing

**Problem:** Any Drive writer can submit a file in Phase 1.  
**Control:** Treat as unauthenticated advisory input. Require CEO approval for promotion. Phase 2 hardens via per-agent service accounts and Drive metadata binding.

### 12.3 Approval drift

**Problem:** Proposal content changes after approval.  
**Control:** Approval binds to `(proposal_id, proposal_fingerprint, rendered_summary_hash)`. Mismatch invalidates approval.

### 12.4 Duplicate promotion on replay

**Problem:** Webhook replay or polling replay triggers another promotion.  
**Control:** Idempotence key `(proposal_fingerprint, source_event_id)`. No duplicate terminal receipts.

### 12.5 Rendering non-determinism

**Problem:** CEO approval summary cannot be reproduced deterministically.  
**Control:** Promotion blocked. This is treated as a COO defect, not a policy discretion issue.

### 12.6 Briefing staleness

**Problem:** Claude starts with stale projection.  
**Control:** Freshness metadata required. Stale briefing is informational only.

### 12.7 GitHub outage

**Problem:** Authoritative bus unavailable.  
**Control:** Fail closed. No promotions proceed.

### 12.8 Drive outage

**Problem:** Claude cannot read or write adapter surfaces.  
**Control:** Claude path degraded only. Primary operational loop remains intact.

---

## 13. Phase model

### 13.1 Phase 1

- GitHub is the primary operational bus
- ChatGPT uses GitHub advisory ingress directly
- Claude uses Drive adapter
- Drive polling is allowed
- all promotions require CEO approval
- Drive-origin proposals are unauthenticated

### 13.2 Phase 2

- hosted always-on COO
- Drive push notifications replace polling where possible
- per-agent OAuth service accounts
- routine classes may auto-promote under policy
- Drive metadata is used for writer binding

### 13.3 Phase 3

- direct MCP or synchronous advisory paths to COO where available
- Drive remains fallback adapter
- richer external pulses may feed COO
- invariant unchanged: advisory inputs are proposals, never commands

---

## 14. Final design decisions

1. GitHub is the sole primary operational bus.
2. Drive is an adapter, not a peer bus.
3. Operational state is explicitly bounded.
4. Advisory ingress is explicitly non-operational.
5. Labels are non-authoritative projections only.
6. Proposal fingerprint composition is specified.
7. Approval binds to proposal content and the rendered CEO-visible summary.
8. Processing lifecycle is formalized as a state machine.
9. Drive-origin trust is explicitly weak in Phase 1 and hardened in Phase 2.
10. Briefing is a bounded projection with enumerated refresh triggers.
