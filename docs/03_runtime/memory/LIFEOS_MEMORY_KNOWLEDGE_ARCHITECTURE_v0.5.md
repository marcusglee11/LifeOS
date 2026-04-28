<!-- CANONICAL STATUS -->
<!--
This document is the canonical implementation-planning source for the LifeOS
Memory and Knowledge Architecture v0.5.

Drafting surface: Google Doc (provenance link below)
Canonical source: this repo-backed file
Canonical path: docs/03_runtime/memory/LIFEOS_MEMORY_KNOWLEDGE_ARCHITECTURE_v0.5.md

Do not treat the Google Doc as authoritative after this file is merged.
The Google Doc URL is preserved here for provenance only.

Source Google Doc:
https://docs.google.com/document/d/1-tg9pYdP7Sje1RD0jlBU79qHzDxpsMUPOBsrSTb0dbs/edit?usp=sharing
-->

> **Next step:** Implementation of Phase 1 is tracked in
> [GitHub issue #53 — Implement Phase 1 of the LifeOS memory and knowledge architecture v0.5](https://github.com/marcusglee11/LifeOS/issues/53).
> This document is the planning source for that work. Do not implement runtime,
> schema, or tooling behavior from this file until #53 is actioned.

---

# LifeOS Memory and Knowledge Architecture v0.5

Status: Draft for Phase 1 implementation planning review
Owner: COO role
Audience: AA / Claude / Gemini / OpenClaw / Hermes / Architecture Review
Purpose: Long-horizon shared memory and knowledge system for Boss, Hermes, OpenClaw, EAs, and future LifeOS agents.

## 0. Review incorporation posture

This v0.5 revision incorporates the Claude, Gemini, OpenClaw, and Hermes reviews with the following critical decisions.

Accepted:

- COO is now defined as a runtime role with Phase 1 identity explicitly assigned.
- Phase 1 COO is Boss/Marcus acting through an explicit manual review and repo-merge step.
- No automatic durable write path exists in Phase 1.
- A future agentic COO or governance harness may receive isolated write authority only after explicit approval.
- Hermes native memory direct-write behavior is incompatible with this architecture and is superseded for
  LifeOS durable memory.
- Hermes, OpenClaw, EAs, and advisory agents must emit candidate packets instead of durable writes.
- Canonical candidate-packet transport is a GitHub PR into `knowledge-staging/`.
- GitHub issues/comments may be used as raw ingress, but not as durable memory until converted into
  repo-backed candidate packets.
- Durable write receipts are required, but Phase 1 may batch receipts by review session or distillation packet.
- Phase 1 retrieval needs a minimal authority-envelope retrieval script/skill, not just human discipline.
- The boilerplate generator must be an interactive classifier/wizard, not only empty YAML shells.
- Agent-scoped memory receives a physical prefix to reduce collision risk.
- Google Docs remain drafting surfaces only; canonical architecture and schemas must land in the LifeOS
  repo before Phase 1 activation.

Accepted with modification:

- "One example per record_kind" is retained as a goal, but Phase 1 must not create fake memory provenance.
  Synthetic examples belong under test fixtures and must be marked non-memory.
- Weekly review cadence is treated as operating guidance, not an architectural invariant.

Rejected:

- Treating conflict records merely as promotion-queue items. Conflict records may share staging
  infrastructure, but conflict semantics remain first-class.
- Allowing Hermes native memory as canonical LifeOS memory. It may remain external personal/context
  memory only if treated as non-authoritative observation.

## 1. Objective

Build a durable memory and knowledge architecture that enables LifeOS agents to learn over time without
corrupting doctrine, over-promoting noise, or acting on stale or low-authority information.

The system must support:

- durable learning about Boss, workflows, projects, agents, decisions, and recurring failure modes
- shared reuse across agents
- provenance-backed updates
- explicit authority boundaries
- conservative promotion to shared knowledge and canon
- contradiction detection and supersession
- pruning, archival, and review hygiene
- retrieval that respects authority before recency
- low-friction capture that does not make Boss the classifier or integration layer
- auditable durable write receipts for all accepted, rejected, staged, or merged candidate memory actions
- an explicit transport path from agents to staging

## 2. Hard invariants

1. Authority beats freshness.
2. Canon is not memory.
3. Memory is not doctrine.
4. Observations may be captured aggressively, but promotion must be conservative.
5. Durable records require provenance.
6. Durable memory decisions require receipts.
7. Conflicts must never be resolved by silent overwrite.
8. Structured records are the machine truth surface.
9. Wiki/docs are reviewed human renderings, not uncontrolled lore.
10. Retrieval must expose source, authority, status, sensitivity, and review freshness.
11. COO is sole writer for all durable memory and knowledge records.
12. In Phase 1, COO means Boss/Marcus acting through explicit manual review and repo merge.
13. EAs, Hermes, OpenClaw, and advisory agents emit packets or recommendations; they do not directly commit durable memory.
14. Candidate packets are proposals only.
15. Native memory tools that bypass candidate packets, staging, receipts, and COO decision are
    non-canonical for LifeOS durable memory.
16. Physical indexes are deferred until Phase 3; Phase 1 uses logical separation plus a minimal retrieval script/skill.

## 3. Runtime identity and write-authority model

### 3.1 COO role definition

COO is a governance role, not automatically a specific human, model, or agent.

In Phase 1:

```text
COO = Boss/Marcus acting through explicit manual review and repo merge.
```

Assistants, Hermes, OpenClaw, and EAs may draft, classify, recommend, and generate candidate packets.
They do not make final durable write decisions.

In later phases, COO durable write authority may be delegated to a dedicated governance agent or
deterministic harness only if all conditions are true:

- Boss explicitly approves the delegation.
- The writer has isolated credentials.
- The writer can only write through validated schemas.
- Every decision emits a durable write receipt.
- The writer cannot modify canonical doctrine without separate approval.
- The writer can be disabled without corrupting memory history.

### 3.2 Automatic write meaning

"Automatic write" never means arbitrary agent write access.

In Phase 1:

```text
automatic durable writes = not implemented
```

In Phase 2:

```text
automatic write eligibility = mechanically checked recommendation
```

In Phase 4 or later:

```text
automatic durable write = COO-governed write through an approved writer/harness, under allowlisted rules, with receipt emission
```

## 4. Logical stores

The architecture uses distinct logical stores with different authority, write rules, and retrieval behavior.

### 4.1 Session Context

Purpose: transient working state for the current conversation, workorder, or execution run.

Contains:

- current task state
- local assumptions
- unresolved questions
- temporary notes
- local execution context

Retention: session-bounded unless explicitly promoted.
Authority: low.
Write authority: automatic session runtime.
Retrieval use: working context only. Never normative.

### 4.2 Candidate Packets

Purpose: structured proposals for durable memory changes emitted by EAs, Hermes, OpenClaw, advisory
agents, or workorder processes.

Contains:

- proposed action
- source agent
- source packet ID
- candidate ID
- proposed record classification
- mechanical gating fields
- evidence pointers
- payload

Retention: short to medium unless linked to a durable write receipt.
Authority: proposal only.
Write authority: emitting process.
Retrieval use: staging and COO decision support only. Candidate packets are not durable memory records.

### 4.3 Agent Memory

Purpose: durable machine-retrievable memory for future reasoning.

Contains:

- explicit Boss preferences
- stable workflow patterns
- recurring failure modes
- bounded project lessons
- stable tool or environment facts
- agent-local operational learnings

Retention: medium to long.
Authority: medium.
Write authority: COO sole writer. In Phase 1, this is Boss/Marcus via explicit review and repo merge.
Storage form: structured markdown records with YAML front matter.
Retrieval use: advisory working context inside the authority envelope.

### 4.4 Shared Operational Knowledge

Purpose: reviewed reusable knowledge for multi-agent LifeOS operations.

Contains:

- SOPs
- playbooks
- reusable checklists
- routing rules
- governance interpretations
- cross-agent operating conventions

Retention: long.
Authority: high after review.
Write authority: COO stages; reviewed before becoming shared knowledge.
Storage form: wiki/docs plus generated claim summaries from structured memory where useful.
Retrieval use: operational guidance, subordinate to canon.

### 4.5 Canonical Doctrine

Purpose: normative truth for how LifeOS should operate.

Contains:

- approved policies
- architecture decisions
- governance rules
- protocol definitions
- reference definitions
- authority contracts

Retention: long/permanent.
Authority: highest.
Write authority: explicit review and approval only.
Storage form: versioned docs under reviewed namespaces.
Retrieval use: authority envelope; constrains all lower stores.

### 4.6 Evidence and History

Purpose: preserve why knowledge exists, how it changed, and what supports it.

Evidence is not a separate Phase 1 store by default. Evidence is embedded in durable records unless it
is large, reused, binary, or historically material.

Contains:

- source pointers
- quoted evidence or summaries
- timestamps
- commit SHAs
- issue/PR references
- transcript/workorder locators
- supersession links
- reviewer metadata
- durable write receipt references

Retention: long/permanent where historically material.
Authority: supporting.
Write authority: COO with durable record creation.
Retrieval use: audit, validation, contradiction review, and provenance display.

### 4.7 Conflict Records

Purpose: isolate unresolved contradictions, duplicates, stale records, and authority collisions.

Conflict records may live in the same physical staging directory as other staged records in Phase 1,
but they retain first-class conflict semantics.

Contains:

- conflicting record references
- conflict type
- materiality
- owner
- owner action expectation
- escalation date
- status
- resolution
- supersession edges

Retention: until resolved, then archived with linkage.
Authority: blocking metadata.
Write authority: COO from detection or reviewer recommendation.
Retrieval use: hard flag; may block action if material.

### 4.8 Durable Write Receipts

Purpose: auditable evidence of COO decisions over candidate memory changes.

Contains:

- candidate IDs
- dispositions
- target record paths
- rationale
- source agent
- source packet ID
- decision timestamp

Retention: long/permanent where linked to durable records.
Authority: audit trail.
Write authority: COO.
Retrieval use: audit, validation, provenance, and reconstruction of memory-change history.

## 5. Authority model

Authority classes are explicit and mandatory.

```yaml
authority_class:
  - observation
  - agent_memory
  - shared_knowledge
  - canonical_doctrine
```

Authority ordering:

```text
canonical_doctrine > shared_knowledge > agent_memory > observation > session_context
```

Rules:

- Canonical doctrine overrides all lower-authority stores.
- Shared operational knowledge overrides agent-local memory unless scoped otherwise.
- Agent memory may inform action but may not override policy, doctrine, or active project state.
- Observations are evidence candidates, not durable truth.
- Session context is local and non-normative.
- Candidate packets are proposals and have no durable authority until COO disposition.
- Durable write receipts are audit records, not normative operating instructions.
- A lower-authority record that conflicts with higher authority is marked conflicted or rejected.

## 6. Tool compatibility and migration

### 6.1 Hermes native memory tool

The adopted memory architecture supersedes Hermes native durable-memory direct writes for LifeOS memory.

Any Hermes capability equivalent to:

```text
memory(action="add")
```

is incompatible with Phase 1 activation if it writes durable LifeOS memory directly.

Required migration:

- Hermes emits candidate packets instead of direct durable memory writes.
- Candidate packets land in `knowledge-staging/` through the approved transport path.
- COO reviews, accepts, rejects, stages, or merges the candidate.
- Every disposition emits a durable write receipt or batched receipt entry.

If native memory cannot be disabled, its contents are treated as non-canonical observation only and must
not be used as LifeOS durable memory, shared knowledge, or canon.

### 6.2 OpenClaw and EA behavior

OpenClaw and EAs may emit candidate packets, review findings, and evidence pointers.

They must not:

- write directly to `memory/` durable records
- write directly to shared knowledge or canon
- bypass candidate packets
- bypass COO receipt emission
- merge their own candidate packets into durable memory paths

## 7. Candidate packet transport contract

### 7.1 Canonical transport

The canonical Phase 1 transport is:

```text
agent/workorder emits candidate packet -> GitHub branch -> PR adding file(s) under knowledge-staging/ -> COO review/merge/reject
```

The PR is the transport and review surface. Merge is the Phase 1 COO durable/staging decision point.

### 7.2 Allowed raw ingress

GitHub issues, issue comments, PR comments, chat transcripts, or OpenClaw session outputs may be used as raw ingress only.

Raw ingress must be converted into a candidate packet before any durable memory disposition.

### 7.3 Disallowed transport

The following are disallowed for Phase 1 durable memory mutation:

- direct commits to `main` by EAs or advisory agents
- direct writes to `memory/` by non-COO actors
- native memory-tool writes treated as canonical LifeOS memory
- issue/comment text treated as durable memory without candidate packet conversion

## 8. Minimal ontology

The schema uses orthogonal fields. Do not create compound record kinds such as `project_state`,
`workflow_rule`, or `risk_pattern`. Use `record_kind`, `scope`, and `tags` together.

### 8.1 Record kind

```yaml
record_kind:
  - fact
  - preference
  - rule
  - decision
  - state
  - lesson
  - pattern
```

Definitions and discriminant tests:

- `fact`: descriptive claim intended to remain true until contradicted or superseded.
- `preference`: stated or explicitly confirmed behavioral preference that should shape future action.
- `rule`: ongoing normative constraint or instruction that remains in force across future actions.
- `decision`: time-bound choice made or ratified at a specific moment with durable downstream effect.
- `state`: time-scoped snapshot of the condition of a named subject.
- `lesson`: reusable learning extracted from experience, review, failure, or success.
- `pattern`: recurring tendency, risk, anti-pattern, or success mode observed across more than one event.

Rules:

- If a record describes a specific choice made at a point in time, use `decision`, not `rule`.
- If a record describes an ongoing constraint, use `rule`, not `decision`.
- If a record lacks a named subject and observation time, it must not use `state`.
- If a record reflects a one-off incident with no reuse claim, it must not use `pattern`.
- If the classification is uncertain, the candidate is staged for review rather than auto-written.
- Reference material such as glossary terms and relationship maps belongs in wiki/canon or rendered
  documentation, not as primary agent-memory records.

### 8.2 Scope

```yaml
scope:
  - global
  - project
  - agent
  - workflow
  - infrastructure
```

Notes:

- Boss-specific preferences use `record_kind: preference` and usually `scope: global` or `scope: workflow`.
- Project state uses `record_kind: state` and `scope: project`.
- Tool facts normally use `scope: infrastructure` unless they are agent-specific.
- Agent-specific memory uses `scope: agent` and should live under `memory/agents/<agent_name>/` in Phase 1.

### 8.3 Lifecycle state

```yaml
lifecycle_state:
  - draft
  - active
  - stale
  - archived
  - superseded
  - conflicted
```

Rules:

- `superseded` is the lifecycle state derived from a non-empty `superseded_by` field.
- `conflicted` is the lifecycle state derived from a material open conflict reference.
- Ordinary retrieval excludes archived and superseded records.
- Ordinary action use excludes conflicted records with medium/high materiality.

### 8.4 Sensitivity

```yaml
sensitivity:
  - public
  - internal
  - private
  - sensitive
  - secret
```

### 8.5 Retention class

```yaml
retention_class:
  - session
  - short
  - medium
  - long
  - permanent
```

## 9. Memory unit model

Use hybrid atomicity.

Default durable unit: one file per coherent claim cluster.

A claim cluster is acceptable when all claims:

- share the same scope
- share the same authority class
- share the same lifecycle state
- are supported by the same evidence set
- can be reviewed or superseded together

Avoid broad file-per-topic memory records for machine truth. Use topic pages only for rendered summaries,
dashboards, or human review docs.

## 10. Storage model

### 10.1 Canonical repo location

Google Docs are drafting surfaces only.

Before Phase 1 activation, the architecture, schemas, examples, and validation scripts must land in the primary LifeOS repo.

Recommended canonical targets:

```text
docs/03_runtime/memory/LIFEOS_MEMORY_KNOWLEDGE_ARCHITECTURE_v0.5.md
schemas/memory/
knowledge-staging/
memory/
memory/receipts/
tools/memory/
tests/memory/
```

Exact pathing may be adjusted to match the repository's active architecture source-of-truth rules, but
the canonical source must be repo-backed.

### 10.2 Phase 1 storage principle

Phase 1 uses logical separation by directory and front matter. It does not create physical vector indexes
or separate retrieval services.

Phase 1 retrieval is:

```text
filesystem traversal + grep/search + front-matter parse + authority-envelope retrieval script/skill
```

Physical indexes are Phase 3.

### 10.3 Agent memory store

Suggested path families:

```text
memory/preferences/
memory/workflows/
memory/projects/
memory/decisions/
memory/lessons/
memory/patterns/
memory/infrastructure/
memory/agents/<agent_name>/
```

Path families are convenience groupings, but `memory/agents/<agent_name>/` is required for
`scope: agent` records in Phase 1.

Validator rule:

```text
records under memory/agents/<agent_name>/ must have scope: agent and agent: <agent_name>
```

Authority and classification still come from front matter.

### 10.4 Shared operational knowledge

Suggested path families:

```text
wiki/workflows/
wiki/policies/
wiki/projects/
wiki/playbooks/
wiki/glossary/
wiki/adr/
```

Rule: only reviewed reusable knowledge enters the shared wiki.

### 10.5 Canonical doctrine

Canonical doctrine must live under the repository's reviewed doctrine/governance namespaces.

Examples:

```text
docs/00_foundations/
docs/01_governance/
docs/02_protocols/
docs/03_runtime/
docs/architecture_decisions/
```

Exact pathing follows the repository's current architecture source-of-truth rules.

### 10.6 Staging area

Use one physical staging directory in Phase 1:

```text
knowledge-staging/
```

Queue identity is represented by front matter, not separate folders.

```yaml
staging_status:
  - workorder_distillation
  - candidate_packet
  - memory_candidate
  - promotion_candidate
  - conflict_candidate
  - prune_candidate
  - review_digest
```

Purpose:

- receive raw post-workorder distillations
- receive candidate packets from agents and advisory processes
- queue candidate memory writes
- queue shared/canonical promotion candidates
- hold conflicts before resolution
- support human review

### 10.7 Durable write receipts

Suggested path:

```text
memory/receipts/
```

A durable record may reference one or more write receipts.

Phase 1 may use batched receipts:

```text
one receipt file per distillation packet or review session
```

A batched receipt must include one disposition entry per candidate.

### 10.8 Extracted evidence

Evidence is embedded by default.

Extract evidence to a separate file only when:

- quoted evidence exceeds 2KB
- the same evidence supports two or more durable records
- the evidence is binary or cannot be represented cleanly in front matter
- a reviewer marks the evidence as historically material

Suggested path when extraction is needed:

```text
knowledge-evidence/
```

No separate evidence index exists in Phase 1.

## 11. Required durable record schema

Every durable memory or knowledge record must include YAML front matter.

```yaml
id:
title:
record_kind:
authority_class:
scope:
project:
agent:
sensitivity:
retention_class:
lifecycle_state:
confidence:
created_utc:
updated_utc:
review_after:
owner:
writer: COO
sources:
  - source_type:
    locator:
    quoted_evidence:
    captured_utc:
    content_hash:
    commit_sha:
supersedes:
superseded_by:
conflicts:
write_receipts:
staging_status:
tags:
```

Additional required fields for `record_kind: state`:

```yaml
state_subject:
state_observed_utc:
```

Mechanical enforcement fields for candidate-derived durable records:

```yaml
requires_human_review:
authority_impact:
personal_inference:
promotion_basis:
```

### 11.1 Phase 1 required fields

A Phase 1 durable record is invalid unless these fields are present:

```text
id
title
record_kind
authority_class
scope
sensitivity
retention_class
lifecycle_state
created_utc
updated_utc
owner
writer
sources
```

Additional required fields:

- `record_kind: state` records require `state_subject` and `state_observed_utc`.
- active state records require `review_after`.
- active non-canon durable records require `review_after`.
- candidate-derived durable commits require at least one `write_receipts` reference.
- `scope: agent` records require `agent` and must use `memory/agents/<agent_name>/` in Phase 1.

Field rules:

- `id` must be stable.
- `writer` must be `COO` for durable records.
- `sources` must be non-empty.
- `review_after` is mandatory for non-canon active records.
- `superseded_by` implies `lifecycle_state: superseded`.
- open material `conflicts` imply `lifecycle_state: conflicted`.
- `confidence` is allowed but not used for Phase 1 gating.
- `evidence_strength` is not a Phase 1 field.
- State records should use shorter review cadences than other durable record kinds unless explicitly justified.

## 12. Evidence model

Evidence pointers must be structured.

```yaml
source_type:
  - conversation
  - workorder
  - repo_file
  - commit
  - issue
  - pull_request
  - receipt
  - manual_note
  - external_doc

locator:
quoted_evidence:
captured_utc:
content_hash:
commit_sha:
```

Rules:

- Repo-backed evidence requires a commit SHA.
- Acceptable repo locators: commit SHA alone, or file path plus commit SHA, or immutable tag.
- Branch references are invalid as durable evidence locators.
- Workorder-derived facts require workorder ID or distillation packet ID.
- Conversation-derived facts require transcript locator or review packet reference.
- External facts require source locator and capture date.
- Unsupported durable claims are invalid.

## 13. Write authority, receipts, and automatic write policy

### 13.1 Sole-writer rule

All durable memory record writes are performed by COO as sole writer.

In Phase 1, COO is Boss/Marcus acting through explicit manual review and repo merge.

"Automatic" does not mean Hermes, OpenClaw, EAs, or advisory agents may write durable memory directly.

EAs and advisory agents may emit:

- distillation packets
- candidate packets
- review recommendations
- conflict candidates
- promotion candidates

COO commits, stages, merges, or rejects them.

### 13.2 Durable write receipt

Every COO durable-memory decision must emit a durable write receipt or batched receipt entry.

Single-candidate receipt fields:

```yaml
receipt_id:
candidate_id:
disposition: accepted | rejected | staged | merged
target_record_id:
target_record_path:
decided_by: COO
decided_utc:
rationale:
source_agent:
source_packet_id:
```

Batched receipt fields:

```yaml
receipt_id:
receipt_type: batch
review_session_id:
source_packet_id:
decided_by: COO
decided_utc:
entries:
  - candidate_id:
    disposition: accepted | rejected | staged | merged
    target_record_id:
    target_record_path:
    rationale:
    source_agent:
```

Rules:

- Every durable record commit must be traceable to a receipt or batched receipt entry.
- Candidate packets without `source_agent` and `source_packet_id` are invalid for durable commit.
- Rejections, staging decisions, and merges must also emit receipts.
- A durable record may reference one or more write receipts.
- Durable write receipts are audit artifacts and do not themselves authorize action.

### 13.3 Automatic write decision rule

Automatic agent-memory write is allowed only if all conditions are true:

```text
writer == COO
authority_class == agent_memory
record_kind in {fact, preference, state, lesson, pattern}
sensitivity in {public, internal, private}
requires_human_review == false
authority_impact in {none, low}
personal_inference == false
sources valid and non-empty
no open medium/high conflict
no contradiction with canonical_doctrine or shared_knowledge
not security-sensitive
not governance doctrine
not authority-changing
```

Mechanical enforcement fields:

```yaml
requires_human_review:
authority_impact:
personal_inference:
promotion_basis:
```

Rules:

- In Phase 1, automatic durable write is not implemented; the rule is used to classify and stage.
- If any mechanical enforcement field is missing, the record must be staged for review.
- Any record with `requires_human_review: true` is ineligible for automatic durable write.
- Any record with `authority_impact: medium|high` is ineligible for automatic durable write.
- Any record with `personal_inference: true` is ineligible for automatic durable write.
- Any record with `sensitivity: sensitive|secret` is ineligible for automatic durable write.
- A Boss preference may be auto-written only when the source contains an explicit preference,
  instruction, or stable repeated operating pattern. Inferred preferences are staged for review.

### 13.4 Automatic write denylist

Review required before durable write for:

- worldview-defining beliefs
- inferred psychological traits
- sensitive personal attributes
- health, legal, political, religious, identity, or financial vulnerability claims
- governance doctrine
- authority model changes
- cross-agent operating policy
- security-sensitive details
- claims that materially affect permissions, autonomy, escalation, or agent authority
- anything with `sensitivity: sensitive` or `sensitivity: secret`

### 13.5 Boss authority

Boss remains final authority on:

- sensitive preferences
- personal worldview-defining rules
- governance doctrine
- authority changes
- canonical approvals
- material autonomy boundaries

## 14. Ingestion pipeline

### Step 1: Capture

A distillation packet is required when any of the following occur:

- a workorder changes project state
- Boss states or confirms an operating preference
- an agent/tool failure mode recurs
- a decision is made or ratified
- a reusable lesson is discovered
- a contradiction or stale record is found
- a milestone closes
- Boss explicitly requests memory capture or review

A packet is optional for trivial Q&A, temporary discussion, or one-off execution with no durable learning.

Required distillation packet fields:

```yaml
workorder_id:
project:
date_utc:
summary:
outcomes:
facts_learned:
preferences_observed:
workflow_lessons:
decisions:
patterns:
contradictions:
followups:
candidate_memory_writes:
candidate_promotions:
candidate_archivals:
```

### 14.1 Candidate packet contract

Any EA, Hermes, OpenClaw runtime, or advisory process that proposes durable memory changes must emit a candidate packet.

Required candidate packet fields:

```yaml
candidate_id:
source_agent:
source_packet_type:
source_packet_id:
generated_utc:
proposed_action: create | update | supersede | conflict_open | archive
proposed_record_kind:
proposed_authority_class:
scope:
requires_human_review:
authority_impact: none | low | medium | high
personal_inference: true | false
sensitivity:
promotion_basis:
sources:
summary:
payload:
```

Rules:

- Candidate packets are proposals only. They are not durable writes.
- COO is the only component allowed to convert a candidate packet into a durable record.
- Candidate packets missing required provenance fields are invalid.
- Candidate packets missing mechanical enforcement fields are staged for review or rejected.
- Candidate packets must arrive through the approved transport contract before Phase 1 disposition.

### Step 2: Classify

COO drafts classification. Boss only reviews edge cases.

Each item is classified as:

```text
discard
session_only
observation
agent_memory_candidate
shared_knowledge_candidate
canonical_doctrine_candidate
conflict_candidate
archive_candidate
```

### Step 3: Deduplicate

Compare against existing memory, shared knowledge, canon, and conflict records.

Actions:

```text
reject_duplicate
merge_evidence
create_new_record
open_conflict
mark_supersession_candidate
stage_for_review
```

### Step 4: Validate

Phase 1 validation checks:

- required front-matter fields present
- enum values valid
- source block present and non-empty
- writer is COO
- repo-backed evidence uses commit SHA, tag, or file path plus commit SHA
- `superseded_by` implies `lifecycle_state: superseded`
- open material conflicts imply `lifecycle_state: conflicted`
- active non-canon durable records include `review_after`
- `record_kind: state` records include `state_subject` and `state_observed_utc`
- `scope: agent` records include `agent` and valid path prefix
- authority/store compatibility is valid
- candidate-derived durable commits include a write receipt reference

Phase 2 validation adds:

- duplicate checks
- contradiction checks
- automatic-write allowlist enforcement
- stale record checks
- sensitivity checks
- no unresolved higher-authority conflict
- no transient noise promoted to durable memory
- no canon change without review

### Step 5: Commit or stage

Allowed destinations:

- COO manual commit to agent memory
- staging queue for shared/canonical candidates
- conflict candidate in staging
- prune/archive candidate in staging
- durable write receipt or batched receipt entry for every accepted, rejected, staged, or merged candidate action

No non-COO direct durable writes.

### Step 6: Promote

Promotion is gated.

Raw distillation → agent memory requires:

- valid evidence
- stable reuse value
- correct scope
- low sensitivity or review approval
- no conflict with active canon
- durable write receipt or batched receipt entry

Agent memory → shared knowledge requires:

- cross-agent or cross-workflow reuse value
- review
- no material unresolved conflict
- owner
- review cadence
- durable write receipt or batched receipt entry

Shared knowledge → canonical doctrine requires:

- explicit approval
- normative force
- versioned canonical path
- changelog/ADR/receipt where applicable
- supersession impact review
- durable write receipt or batched receipt entry

### Step 7: Promotion forcing function

Promotion is not automatic, but staging should not starve.

An agent_memory record auto-stages for shared-knowledge review when either condition is met:

- cited by at least 3 workorders across at least 2 distinct projects or workflows
- cited in a milestone closure packet as reusable outside its original scope

Auto-staging is not auto-promotion.

## 15. Conflict and supersession model

Conflicts are first-class records.

In Phase 1 they live under:

```text
knowledge-staging/
```

with:

```yaml
staging_status: conflict_candidate
```

Conflict status values:

```yaml
status:
  - open
  - acknowledged
  - blocked
  - resolved
  - archived
```

Required conflict schema:

```yaml
conflict_id:
status: open
records_in_conflict:
  - path:
    id:
conflict_type:
materiality:
opened_utc:
escalation_date:
owner: COO
owner_action:
summary:
evidence:
resolution:
resolved_utc:
supersession_edges:
```

Conflict types:

```yaml
conflict_type:
  - contradiction
  - duplicate
  - scope_mismatch
  - staleness
  - authority_collision
  - evidence_dispute
```

Materiality:

```yaml
materiality:
  - low
  - medium
  - high
```

Materiality default rules:

- involves canonical_doctrine: high
- involves shared_knowledge: high
- agent_memory ↔ agent_memory, same scope: medium
- observation-level or cross-scope conflict: low

COO assigns materiality. Reviewer may override.

Rules:

- Every conflict record must include an owner action expectation.
- High-materiality conflicts must be acknowledged in the same review cycle in which they are opened.
- Medium-materiality conflicts must be resolved or explicitly deferred by the next milestone review.
- Open conflicts past `escalation_date` must surface for Boss review or override.
- Conflicting durable records are preserved until resolved.
- Material high-authority conflicts block promotion.
- Resolved conflicts create supersession edges.
- Historical records are archived, not hard-deleted, when they retain audit value.
- Superseded records are excluded from ordinary action retrieval.

Supersession edge schema:

```yaml
from_record:
to_record:
supersession_type:
reason:
decided_by:
decided_utc:
evidence:
```

Supersession types:

```yaml
supersession_type:
  - replaces
  - narrows
  - broadens
  - corrects
  - archives
```

## 16. Retrieval architecture

Retrieval is two-pass.

### 16.1 Pass 1: Authority envelope

Before retrieving working context, the system retrieves constraints from:

1. canonical doctrine
2. active operating policies
3. active project state that constrains permissible action
4. conflict metadata
5. supersession metadata

Purpose: establish what the agent is allowed to believe, use, or do.

Clarification:

- Only project state that constrains permissible action belongs in Pass 1.
- Informational or historical project state belongs in Pass 2 working context.

### 16.2 Pass 2: Working context

After authority envelope retrieval, the system retrieves:

1. session context
2. agent memory
3. shared operational knowledge
4. supporting docs/wiki
5. evidence records as needed
6. informational or historical project state

Purpose: gather useful context inside the authority envelope.

### 16.3 Phase 1 retrieval skill/script

Phase 1 must include a minimal retrieval script or skill that hard-codes the two-pass order.

Minimum command behavior:

```text
memory_retrieve --query <text> --scope <scope> --authority-floor <class> --include-sensitive false
```

Minimum behavior:

- search canon and active operating policy first
- search action-constraining project state before general memory
- exclude archived and superseded records by default
- flag medium/high conflicts
- exclude sensitive/secret unless explicitly permitted
- return required metadata with each result

### 16.4 Hard retrieval filters

Exclude from ordinary action use:

- archived records
- superseded records
- stale records past review threshold unless explicitly permitted
- conflicted records with medium/high materiality
- records above the allowed sensitivity level
- records below the required authority floor

Additional sensitivity enforcement:

- Records with `sensitivity: sensitive|secret` are ineligible for automatic durable write.
- Records with `sensitivity: sensitive|secret` are ineligible for automatic promotion.
- Ordinary retrieval excludes `sensitive|secret` records unless the retrieval context explicitly permits them.

### 16.5 Ranking principles

Ranking formulas are deferred to Phase 3.

Phase 1 retrieval priority is deterministic and rule-based:

```text
authority envelope first
then active records
then exact scope match
then reviewed/shared records
then agent memory
then observations
```

Phase 3 may introduce scoring, but hard filters always dominate.

Required retrieval result metadata:

```yaml
source_path:
record_id:
record_kind:
authority_class:
scope:
lifecycle_state:
review_after:
superseded_by:
conflicts:
sensitivity:
last_updated:
write_receipts:
```

## 17. Index topology

### 17.1 Phase 1

No physical indexes.

Use logical separation by directory and front matter, plus the minimal retrieval script/skill.

### 17.2 Phase 3 target

Use separate physical indexes with federated retrieval.

Indexes:

```text
session_index
agent_memory_index
shared_knowledge_index
canon_index
conflict_index
receipt_index
```

No separate `evidence_index` until extracted evidence volume justifies it.

Rules:

- Do not flatten all stores into one undifferentiated vector pool.
- Federated retrieval may merge results only after preserving authority metadata.
- Canon and conflict indexes must be queryable independently.
- Receipt records must be independently queryable for audit.
- Retrieval consumers must be able to request an authority floor.
- Retrieval consumers must be able to exclude stale/superseded/conflicted records.

## 18. Wiki relationship model

Use a hybrid wiki model.

Structured memory is the source for machine-readable claim truth.

Wiki pages are human-readable renderings that may contain:

- generated summaries from structured memory
- human-authored interpretation
- reviewed playbooks
- operational guidance
- links to canon, decisions, receipts, and evidence

Generated sections must be delimited.

Example:

```markdown
<!-- BEGIN GENERATED MEMORY SUMMARY: source=index/memory/workflows.json -->
...
<!-- END GENERATED MEMORY SUMMARY -->
```

Rules:

- Operationally forceful wiki claims must link to structured records, shared knowledge, or canon.
- Manual wiki prose must not silently contradict structured truth.
- In Phase 1 this is a discipline rule.
- In Phase 2 it becomes a lint/check target for generated sections.
- Canon remains separately versioned and reviewed.

## 19. Hygiene jobs

### 19.1 Phase 1 hygiene

Phase 1 hygiene is milestone-based by default.

Run memory hygiene when:

- a project milestone closes
- a major architecture change lands
- a conflict escalation date passes
- Boss requests review

Milestone hygiene actions:

- consolidate project memory
- archive stale project state
- promote reusable lessons to staging
- open conflicts for doctrine drift
- refresh generated wiki summaries if present
- verify candidate packets have receipts or explicit unresolved staging status

Operating guidance: until Phase 2 automation exists, a short weekly staging review is recommended but
not required as an architecture invariant.

### 19.2 Phase 2 hygiene

Add:

- schema validation in CI or local quality gate
- automatic-write allowlist enforcement
- duplicate checks
- contradiction checks
- stale record checks
- review queue digest
- prune queue digest
- generated wiki summary drift checks
- receipt coverage checks

### 19.3 Phase 4 hygiene

Only after automation exists, add scheduled jobs:

- weekly staging review
- weekly conflict review
- monthly stale memory audit
- monthly retrieval quality review
- quarterly doctrine/ontology review

## 20. Pruning and archival

Prune or archive when:

- item is transient and no longer useful
- item is duplicated by stronger record
- item is superseded
- item has weak or invalid evidence and no reuse
- item belongs in session history only
- project state is obsolete
- review date has expired and no owner revalidates it

Rules:

- Do not hard-delete durable records with historical or audit value.
- Archive with linkage.
- Supersession must be explicit.
- Pruning actions should be reviewable.
- Rejections, merges, and archive decisions require durable write receipts when derived from candidate packets.

## 21. Governance roles

### COO

In Phase 1, COO is Boss/Marcus acting through explicit manual review and repo merge.

Sole writer for durable memory and knowledge records.

Responsible for:

- capture
- classification
- staging
- durable memory writes
- durable write receipts
- routing
- hygiene orchestration
- promotion recommendations
- conflict materiality assignment

### Hermes

Advisory/synthesis role.

Responsible for:

- synthesis
- cross-project coherence review
- memory consolidation recommendations
- reusable knowledge recommendations
- contradiction surfacing
- candidate packet emission when proposing durable memory changes

Hermes does not directly write LifeOS durable memory. Native memory writes, if unavoidable, are
non-canonical observations only.

### OpenClaw / EAs

Execution and advisory agents may emit:

- workorder packets
- distillation packets
- candidate packets
- evidence pointers
- review findings

They do not directly write durable memory.

Canonical transport is a PR into `knowledge-staging/`.

### AA

Responsible for:

- architecture review
- ontology review
- schema review
- retrieval quality review
- doctrine boundary review

### Boss

Final authority for:

- sensitive preferences
- worldview-defining rules
- governance doctrine
- authority changes
- canonical approvals
- material autonomy boundaries
- conflict override where escalation reaches Boss review

## 22. Minimum viable implementation

### Phase 1: Manual structured memory with basic scaffolding

Deliverables:

- repo-landed architecture document
- directory structure
- durable record schema
- candidate packet schema
- durable write receipt schema with batch mode
- distillation packet schema
- conflict record schema
- supersession edge schema
- front-matter boilerplate generator with classification wizard
- minimal required-field/front-matter validator
- minimal authority-envelope retrieval script/skill
- genuine worked examples where available
- synthetic schema fixtures clearly marked as test fixtures where genuine examples do not yet exist
- one worked example each for candidate packet, durable write receipt, conflict record, and supersession edge
- manual promotion flow
- manual retrieval metadata convention
- distillation trigger rule
- EA/OpenClaw/Hermes candidate-packet transport contract
- Hermes native-memory migration note

Acceptance criteria:

- architecture and schemas are repo-backed, not only in Google Docs
- schemas exist and are documented
- directories exist
- candidate packet example includes mechanical enforcement fields
- durable write receipt example exists and links to a candidate packet
- batched receipt example exists
- front-matter generator creates a syntactically valid record shell
- generator includes classification decision prompts for record_kind/scope/sensitivity
- minimal validator rejects missing required fields and invalid enum values
- minimal validator enforces state-specific required fields
- minimal validator enforces receipt reference for candidate-derived durable commits
- minimal validator enforces `memory/agents/<agent_name>/` path mapping for `scope: agent`
- repo-backed evidence examples use commit SHA, tag, or file path plus commit SHA
- COO Phase 1 identity is explicit
- COO sole-writer rule is represented in every durable example
- Hermes direct durable-memory path is superseded or marked non-canonical
- candidate packet transport via PR to `knowledge-staging/` is documented
- no automatic durable write path exists yet
- canon remains separate from memory
- physical indexes are not implemented

### Phase 2: Validation and hygiene

Deliverables:

- semantic schema validation
- automatic-write allowlist enforcement
- duplicate checks
- contradiction checks
- stale record checks
- review queue digest
- prune queue digest
- generated wiki summary prototype
- generated-section drift check
- receipt coverage check

Acceptance criteria:

- invalid durable records fail validation
- automatic writes are mechanically limited by allowlist
- records missing mechanical enforcement fields are staged, not auto-written
- stale records are discoverable
- conflict candidates are queryable
- generated wiki sections are source-linked
- promotion candidates are reviewable
- candidate-derived durable commits without receipts fail validation

### Phase 3: Retrieval/indexing

Deliverables:

- separate physical indexes
- federated retrieval planner
- authority-envelope retrieval
- metadata-preserving merged results
- retrieval tests
- authority-floor filtering
- receipt audit retrieval
- optional ranking formula

Acceptance criteria:

- canon is retrieved before working context
- only action-constraining project state appears in Pass 1
- informational/historical project state appears in Pass 2
- stale/superseded/conflicted records are handled correctly
- retrieval result exposes required metadata
- lower-authority memory cannot override canon
- sensitivity filters are enforceable
- receipt records are independently queryable for audit
- evidence index is added only if extracted evidence volume justifies it

### Phase 4: Automation and quality tuning

Deliverables:

- automated post-workorder hook
- automated distillation packet generation
- automated candidate packet generation
- automated durable write receipt generation for COO decisions
- ranking calibration
- review dashboards
- periodic hygiene jobs
- retrieval contamination tests

Acceptance criteria:

- post-workorder hook emits valid packet
- candidate packet generation emits required mechanical enforcement fields
- low-risk memory writes can be automated safely through COO write path
- every accepted, rejected, staged, or merged candidate action emits a durable write receipt
- shared/canonical candidates remain staged
- retrieval quality can be evaluated against known scenarios
- hygiene jobs produce auditable receipts

## 23. Non-goals for v0.5

This architecture does not yet require:

- full automated claim graph
- fully generated wiki
- automatic canon promotion
- automatic contradiction resolution
- vector-only retrieval
- Phase 1 physical indexes
- cross-agent autonomous doctrine editing
- non-COO durable memory writes
- hard deletion of durable history
- maximal ontology
- manual Boss classification of routine memory items
- automatic durable write path in Phase 1
- synthetic examples disguised as real memory records

## 24. Design decisions

### Decision 1: Phase 1 COO identity

In Phase 1, COO is Boss/Marcus acting through explicit manual review and repo merge.

Reason: without explicit identity, the sole-writer invariant has no operational owner. Delegation to an
agentic COO requires a later approved runtime and credential boundary.

### Decision 2: COO sole writer

All durable memory writes go through COO.

Reason: durable memory shapes future agent behavior and is operationally consequential. Treating memory
as outside sole-writer control would create an ungoverned state mutation path.

### Decision 3: Durable write receipts

Every COO durable-memory decision emits a receipt or batched receipt entry.

Reason: memory mutation must be reconstructable, auditable, and attributable to a candidate packet or source decision.

### Decision 4: Candidate packets as proposal boundary

Agents propose memory changes through candidate packets.

Reason: separates observation/proposal from durable state mutation and preserves the COO sole-writer invariant.

### Decision 5: GitHub PR as Phase 1 transport

Candidate packets enter staging through PRs into `knowledge-staging/`.

Reason: PRs preserve review, diff, provenance, and merge discipline without building a new message bus.

### Decision 6: Native memory tools are non-canonical

Hermes/native assistant memory tools do not constitute LifeOS durable memory.

Reason: direct native writes bypass candidate packets, staging, receipts, and COO review.

### Decision 7: Hybrid memory unit

Adopt file-per-claim-cluster for durable machine records and file-per-topic only for human summaries.

Reason: preserves reviewability and provenance without exploding into one file per atomic claim.

### Decision 8: Collapsed but not overcollapsed ontology

Use seven record kinds: fact, preference, rule, decision, state, lesson, pattern.

Reason: trims the original taxonomy while retaining `state` as an operationally necessary primitive.

### Decision 9: Two-pass retrieval

Retrieve authority envelope before working context.

Reason: prevents fresh but low-authority memory from overriding canon or active policy.

### Decision 10: Phase 1 retrieval script

Phase 1 includes a minimal retrieval script/skill even without indexes.

Reason: two-pass retrieval should not rely on human discipline in every turn.

### Decision 11: First-class conflict records

Represent contradictions separately rather than burying them inside topic files.

Reason: makes unresolved conflicts queryable, reviewable, and enforceable.

### Decision 12: Embedded evidence by default

Evidence is embedded unless large, reused, binary, or historically material.

Reason: avoids premature evidence-store and evidence-index complexity while preserving provenance.

### Decision 13: Phase 1 logical separation only

Phase 1 uses directories, front matter, validator, and retrieval script, not physical indexes.

Reason: avoids pretending infrastructure exists before the schema and examples prove useful.

### Decision 14: Hybrid wiki

Use structured memory as machine truth and wiki/docs as reviewed human renderings.

Reason: avoids both unreadable generated docs and uncontrolled doctrine drift.

## 25. Open review questions for v0.5

1. Is Phase 1 COO identity now operationally clear enough?
2. Is the Hermes native-memory migration rule strict enough?
3. Is PR-to-`knowledge-staging/` sufficient transport for EAs/OpenClaw/Hermes candidate packets?
4. Are batched receipts acceptable without weakening auditability?
5. Is the Phase 1 retrieval script/skill enough to enforce two-pass retrieval before physical indexes?
6. Is `memory/agents/<agent_name>/` sufficient to avoid agent-local memory collision?
7. Are synthetic examples clearly separated from real durable memory?
8. Should the canonical repo path be changed before Phase 1 implementation?

## 26. Approval posture

This architecture is suitable to proceed to Phase 1 implementation planning if reviewers agree that:

- Phase 1 COO identity is explicit
- store boundaries are clear
- COO sole-writer invariant is enforceable
- durable write receipts are enforceable without Phase 1 overbuild
- batched receipts preserve candidate-level disposition auditability
- candidate packet boundaries and transport are clear
- Hermes native memory is superseded for LifeOS durable memory
- authority ordering is enforceable
- automatic memory writes are sufficiently constrained and deferred to enforceable tooling
- durable records have mandatory provenance
- conflict and supersession are first-class
- retrieval uses authority envelope before working context
- Phase 1 avoids premature physical indexing
- canon remains separate from memory and wiki lore
- canonical source lands in the LifeOS repo before Phase 1 activation

---

# Review Prompt for v0.5

You are reviewing "LifeOS Memory and Knowledge Architecture v0.5".

Review goal:
Determine whether v0.5 is now sound enough to proceed to Phase 1 implementation planning and repo landing.

Focus areas:

1. Phase 1 COO identity and write authority
2. Hermes native-memory migration
3. EA/OpenClaw/Hermes candidate-packet transport via GitHub PR
4. Durable write receipt model and batched receipt allowance
5. Phase split realism
6. Ontology collapse and retained `state` record kind
7. Automatic write policy mechanical enforceability
8. Evidence embedding/extraction rule
9. Conflict materiality and escalation model
10. Phase 1 scaffolding: wizard, validator, retrieval script
11. Repo target and canonicalization

Return:

- Verdict: approve / approve with amendments / block
- Blocking issues only if they would make Phase 1 unsafe or likely to stall
- Non-blocking issues
- Minimal amendment block, if needed
- Phase 1 implementation risks
- Any simplification that reduces maintenance burden without weakening authority, provenance, or retrieval safety

Do not rewrite the whole architecture unless necessary. Prefer precise amendments.
