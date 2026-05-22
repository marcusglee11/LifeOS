# LifeOS Multi-Agent Protocol v1.0 — Message Schema & Communication Spec

**Status:** Active reference — PROTOCOL
**Version:** v1.0
**Binding class:** PROTOCOL (binding for agents and runtime per ratified parent components)
**Canonical source:** This document
**Consolidates:** TransportEnvelope schema, compact YAML protocol (protocol.md), Delegated Authority Protocol v0.3 governance rules, bilateral protocol requirements, current-protocol.json surface map
**Supersedes:** `protocol.md` (minimal agent conversation protocol v1)
**Governance parent:** Delegated Authority Protocol v0.3 (ratified)

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Agent Identity & Addressing](#2-agent-identity--addressing)
3. [Message Envelope](#3-message-envelope)
4. [Message Types](#4-message-types)
5. [Payload Contracts](#5-payload-contracts)
6. [Addressing & Routing](#6-addressing--routing)
7. [Message Lifecycle](#7-message-lifecycle)
8. [Transport Bindings](#8-transport-bindings)
9. [Security & Authority Integration](#9-security--authority-integration)
10. [Registry Requirements](#10-registry-requirements)
11. [Normative References](#11-normative-references)

---

## 1. Purpose & Scope

### 1.1 Purpose

This document defines the **message schema and communication protocol** for all inter-agent communication within LifeOS. It provides:

- A formal JSON Schema for message envelopes and payloads
- A typed message system (request, response, event) mapped to transport turn types
- An addressing scheme for agent identity and routing
- A message lifecycle state machine
- Transport bindings for each supported channel
- Integration rules with the Delegated Authority Protocol

### 1.2 Relationship to Existing Protocols

| Document | Role | Relationship |
|---|---|---|
| Delegated Authority Protocol v0.3 (ratified) | Governance | Parent protocol — defines sovereignty, channel classes, authority modes, admission rules. This spec implements those rules at the message level. |
| `protocol.md` (compact YAML) | Wire format | Superseded by this spec. The compact YAML is preserved as one **compact serialization profile** of this spec's envelope. |
| `current-protocol.json` | Surface map | Registry of communication surfaces, claim tags, and probe policy. This spec references and extends the surface map. |
| `schemas/transport_envelope.schema.json` | Schema | Canonical JSON Schema for the transport envelope. This spec lifts it to a full specification. |
| `standards/bilateral-protocol/REQUIREMENTS.md` | Requirements | Normative requirements adopted and expanded here. |

### 1.3 Key Design Principles

1. **Transport neutrality** — The same message schema works across GitHub Issues, direct CLI, webhooks, or file handoffs.
2. **Layered interpretation** — Every message carries transport turn type, semantic class, and authority mode (per DAP §5).
3. **Fail-closed by default** — Missing fields, unknown types, expired messages → reject.
4. **Exact matching** — Agent identities, targets, and registries use exact string matching (DAP §11.5).
5. **Auditability** — Every message carries causation chain, correlation, and idempotency key for replay-safe audit.

---

## 2. Agent Identity & Addressing

### 2.1 Agent Identities

Each LifeOS agent has a canonical **agent id** — a short, stable string registered in the LifeOS agent registry:

| Agent ID | Display Name | Role |
|---|---|---|
| `cabra` | Marcus (CEO) | Sovereign operator |
| `hermes` | Hermes | Execution surface |
| `openclaw` | OpenClaw | Coordination surface |
| `codex` | Codex | Execution agent |
| `claude-code` | Claude Code | Execution agent |
| `hermes-gw` | Hermes Gateway | Gateway daemon |

Agent IDs are:
- Globally unique within LifeOS
- Case-sensitive, kebab-case, max 32 chars
- Declared in the agent identity registry (see §10)

### 2.2 Addressing Format

Messages use a simple direct addressing scheme:

```
agent_id[/subcomponent]
```

Examples:
- `hermes` — addressed to the Hermes surface
- `hermes/bus-watcher` — addressed to Hermes's bus-watcher subcomponent
- `codex` — addressed to the Codex EA lane

### 2.3 Addressing Properties

| Property | Schema | Description |
|---|---|---|
| `sender_actor` | `string` (agent_id) | Who sent this message |
| `sender_role` | `string` | Role at time of dispatch (e.g. `coordinator`, `executor`, `ceo`) |
| `intended_recipient` | `string` (agent_id[/sub]) | Intended target |
| `cc_recipients` | `string[]` (agent_id) | CC list for visibility (optional) |

### 2.4 Message Threading

Messages are threaded by **correlation_id** + **thread_id**:

| Field | Purpose |
|---|---|
| `correlation_id` | Groups all messages in one logical conversation or workflow |
| `causation_id` | Points to the `message_id` of the message that caused this one |
| `root_objective_id` | Top-level LifeOS objective this message serves |
| `thread_id` | Human-readable short thread label (e.g. `s004`, `pr-issue-72`) |

---

## 3. Message Envelope

### 3.1 Canonical JSON Schema

Every inter-agent message MUST be wrapped in a `transport_envelope` conforming to `schemas/transport_envelope.schema.json`.

```json
{
  "message_id": "01J2XYZ...",
  "correlation_id": "wf-20260521-rate-limiter",
  "causation_id": "01J2XYZ...",
  "root_objective_id": "obj-phase6-impl",
  "sender_actor": "openclaw",
  "sender_role": "coordinator",
  "intended_recipient": "hermes",
  "cc_recipients": ["cabra"],
  "authority_scope": "delegated_execute",
  "transport_kind": "github_issue",
  "schema_name": "lifeos.agent_dispatch/v1",
  "schema_version": "1",
  "hub_commit_sha": "a1b2c3d4e5f6...",
  "created_at": "2026-05-21T12:00:00Z",
  "expires_at": "2026-05-21T14:00:00Z",
  "idempotency_key": "ik-rate-limiter-impl-001",
  "attempt_number": 1,
  "payload_hash": "sha256hex...",
  "payload": { ... }
}
```

### 3.2 Required Fields

All fields in `transport_envelope.schema.json` are **required** unless explicitly nullable:

| Field | Always required? | Notes |
|---|---|---|
| `message_id` | Yes | UUID v7 or ULID |
| `correlation_id` | Yes | Groups conversation |
| `causation_id` | Yes | First message in a thread uses its own `message_id` |
| `root_objective_id` | Yes | May be omitted only for discovery/heartbeat |
| `sender_actor` | Yes | Registered agent id |
| `sender_role` | Yes | Semantic role |
| `intended_recipient` | Yes | Target agent id |
| `authority_scope` | Yes | One of DAP §8 authority values |
| `transport_kind` | Yes | Transport mechanism |
| `schema_name` | Yes | Identifies payload schema |
| `schema_version` | Yes | Payload schema version |
| `hub_commit_sha` | Yes | SHA of lifeos-common-hub at dispatch |
| `created_at` | Yes | UTC ISO 8601 |
| `expires_at` | Yes | Nullable; null = no expiry |
| `idempotency_key` | Yes | Deduplication key |
| `attempt_number` | Yes | >= 1 |
| `payload_hash` | Yes | SHA-256 hex of serialized payload |
| `payload` | Yes | Content object |

### 3.3 Compact Serialization Profile (GitHub Bus)

For GitHub Issues where space is constrained, the envelope MAY be serialized as a compact YAML block. This is a lossless projection of the JSON schema:

```yaml
v: 1
from: openclaw
to: hermes
th: s004
cid: wf-20260521-rate-limiter
msg_id: 01J2XYZ...
causation_id: 01J2XYZ...
root: obj-phase6-impl
t: do
scope: delegated_execute
sum: Implement rate limiter per spec
sch: lifeos.agent_dispatch/v1
sch_v: "1"
hub: a1b2c3d4e5f6...
iat: "2026-05-21T12:00:00Z"
exp: "2026-05-21T14:00:00Z"
ik: ik-rate-limiter-impl-001
att: 1
rr: 1
msg: |
  Implement the rate limiter module per the attached spec.
  All tests must pass before PR.
```

**Compact field mapping to envelope:**

| Compact | Canonical | Notes |
|---|---|---|
| `v` | envelope version | Always `1` |
| `from` | `sender_actor` | |
| `to` | `intended_recipient` | |
| `cc` | `cc_recipients` | Comma-separated, optional |
| `th` | `thread_id` | |
| `cid` | `correlation_id` | |
| `msg_id` | `message_id` | |
| `causation_id` | `causation_id` | |
| `root` | `root_objective_id` | |
| `t` | turn type | `q`, `a`, `ack`, `do`, `done`, `blk`, `dec` |
| `scope` | `authority_scope` | |
| `sum` | summary | Target <= 80 chars |
| `sch` | `schema_name` | |
| `sch_v` | `schema_version` | |
| `hub` | `hub_commit_sha` | |
| `iat` | `created_at` | |
| `exp` | `expires_at` | |
| `ik` | `idempotency_key` | |
| `att` | `attempt_number` | |
| `rr` | response required | `1` or `0` |
| `role` | `sender_role` | Optional in compact |
| `msg` | payload | Free text or structured YAML |

### 3.4 Envelope Validation Rules

1. `created_at` MUST be a valid UTC ISO 8601 timestamp
2. `expires_at` MUST be null or a UTC timestamp > `created_at`
3. `message_id` MUST be unique per sender — receivers MUST reject duplicates within the expiry window
4. `payload_hash` MUST match SHA-256 of the serialized `payload`
5. `idempotency_key` MUST be used for deduplication: same key within expiry = same logical operation
6. `attempt_number` MUST be >= 1 and MUST increment on retry

---

## 4. Message Types

### 4.1 Three Canonical Classes

Every payload belongs to one of three canonical message classes:

| Class | Expects Response? | Durable? | Transport Turn Types |
|---|---|---|---|
| **Request** | Yes (`rr: 1`) | Yes | `q`, `do` |
| **Response** | No (is the response) | Yes | `a`, `ack`, `done` |
| **Event** | No (fire-and-forget) | Optional | `done`, `blk`, `dec` |

### 4.2 Request

A **Request** expects a response from the recipient. It MUST set `rr: 1`.

**Sub-types:**

| Turn Type | Semantic | Authority Required? | DAP Class |
|---|---|---|---|
| `q` | Question / query | No — informational | `inform` |
| `do` | Action request | Yes — delegation required | `authorize` (with delegation) |

**Rules:**
- A `do` without a valid delegation MUST be rejected as `non_authoritative`
- A `q` MUST NOT trigger execution — answer only
- Requests MUST include `causation_id` pointing to the initiating context
- The sender MUST expect a matching `a` or `done` response before the `expires_at` window

**Example — information request:**
```yaml
v: 1  from: openclaw  to: hermes  th: s005
t: q  scope: informational  rr: 1
sum: Query bus watcher status
msg: What is the current status of the bus watcher on issue 72?
```

**Example — action request with delegation:**
```yaml
v: 1  from: openclaw  to: hermes  th: s006
t: do  scope: delegated_execute  rr: 1
sum: Create PR per spec
msg: |
  delegation_id: del-006
  allowed_actions: [write_repo_file, open_issue, post_bus_reply]
  allowed_targets: [marcusglee11/lifeos-operational-bus]
```

### 4.3 Response

A **Response** is the reply to a prior Request. It MUST NOT set `rr: 1` (unless follow-up is needed). It MUST reference the triggering request's `message_id` in `causation_id`.

**Sub-types:**

| Turn Type | Semantic | When to Use |
|---|---|---|
| `a` | Answer | Response to a `q` — informational |
| `ack` | Acknowledge | Transport receipt only — NOT admission or approval |
| `done` | Completion claim | Work is done (requires evidence per DAP §19) |

**Rules:**
- `ack` is the minimum response — it confirms receipt but NOT admission or verification
- `done` is a **claim** only — it does not certify correctness (DAP §9.7)
- Responses MUST carry the same `correlation_id` as the request
- Responses SHOULD include a summary of what changed or was learned

**Example — acknowledgment:**
```yaml
v: 1  from: hermes  to: openclaw  th: s005
t: ack  scope: informational  rr: 0
sum: Bus watcher status received
msg: Bus watcher on issue 72 is operational. Last check: 2026-05-21T11:55:00Z.
```

**Example — completion with evidence:**
```yaml
v: 1  from: hermes  to: openclaw  th: s006
t: done  scope: delegated_execute  rr: 0
sum: Rate limiter PR submitted
msg: |
  evidence:
    pr_url: https://github.com/marcusglee11/lifeos-operational-bus/pull/189
    tests_run: 14
    tests_passed: 14
    head_sha: 660272d4f8d8557141d6c0ce27c0492d69915926
```

### 4.4 Event

An **Event** is a fire-and-forget notification. It expects no response. It MAY carry `rr: 0` or omit it.

**Sub-types:**

| Turn Type | Semantic | When to Use |
|---|---|---|
| `done` | State notification | Non-blocking status update |
| `blk` | Blocked | Terminal state: cannot proceed |
| `dec` | Decision needed | Escalation: needs higher-layer decision |

**Rules:**
- Events are non-blocking by default — the recipient MAY act or ignore
- `blk` and `dec` are terminal-state reports per DAP §6.6 and §6.7
- Events SHOULD carry enough context for the recipient to decide whether to escalate

**Example — blocked event:**
```yaml
v: 1  from: hermes  to: openclaw  th: s006
t: blk  scope: delegated_execute  rr: 0
sum: Rate limiter blocked — test flake
msg: |
  Tests 9/14 pass. Test_rate_limiter_concurrent() fails intermittently.
  Likely race in token bucket implementation. Needs investigation.
```

### 4.5 Type Mapping — Layered Model

Per DAP §5, every message exists at four layers:

| Layer | Field | Values |
|---|---|---|
| L1: Transport turn | `t` (compact) | `q`, `a`, `ack`, `do`, `done`, `blk`, `dec` |
| L2: Semantic class | Inferred from `t` + `scope` | `inform`, `propose`, `authorize`, `report`, `escalate` |
| L3: Authority mode | `scope` (compact) / `authority_scope` (JSON) | `none`, `informational`, `proposal_only`, `delegated_execute`, `escalation_only` |
| L4: Action set | `payload` content | Per-payload schema |

**Mapping table:**

| L1 (turn) | L2 (semantic) | L3 (authority) |
|---|---|---|
| `q` | `inform` | `informational` |
| `a` | `report` | `informational` |
| `ack` | `report` | `none` |
| `do` + no delegation | `propose` | `proposal_only` |
| `do` + valid delegation | `authorize` | `delegated_execute` |
| `done` (with evidence) | `report` | `informational` |
| `done` (claim only) | `report` | `informational` |
| `blk` | `escalate` | `escalation_only` |
| `dec` | `escalate` | `escalation_only` |

---

## 5. Payload Contracts

### 5.1 Schema Registry

Every message payload is identified by `schema_name` + `schema_version`. Payload schemas live in `lifeos-common-hub/schemas/`.

### 5.2 Registered Payload Schemas

| Schema Name | Version | Description | Required Fields |
|---|---|---|---|
| `lifeos.agent_dispatch/v1` | `1` | Agent dispatch contract | `contract_kind`, `payload` (typed by kind) |
| `lifeos.evidence_manifest/v1` | `1` | Evidence manifest for EA runs | `lane`, `task_scope`, `repo`, `files_changed`, etc. |
| `lifeos.workstream_capsule/v1` | `1` | Workstream state capsule | Per capsule schema |
| `lifeos.coo_command/v1` | `1` | COO operation proposal | `action_id`, `args` |
| `lifeos.state_read/v1` | `1` | State read contract | `contract_id`, `canonical_surfaces` |
| `lifeos.escalation_item/v1` | `1` | Escalation packet | `type`, `options` |
| `lifeos.proposal_item/v1` | `1` | Proposal packet | `proposal_id`, `rationale` |
| `lifeos.adapter_manifest/v1` | `1` | Adapter manifest | `adapter_id`, `transport` |
| `lifeos.retry_policy/v1` | `1` | Retry policy | `max_attempts`, `backoff` |

### 5.3 Payload Rules

1. Payload MUST conform to the schema identified by `schema_name` + `schema_version`
2. Receiver MUST validate payload against the schema before processing
3. Unknown `schema_name` or mismatched `schema_version` → reject with `schema_mismatch`
4. Payload MAY be empty for pure acknowledgement messages (`ack` with no semantic content)

### 5.4 Inline Payload Convention

For simple messages, the payload MAY be a plain-text string or YAML/JSON object rather than a typed schema. This is permitted only for:
- Informational `a` responses
- `ack` receipts
- Ad-hoc `q` questions without a formal schema

Formal typed payloads are REQUIRED for:
- Any `do` with `scope: delegated_execute`
- Any `done` making a completion claim
- Any `blk` or `dec` escalation

---

## 6. Addressing & Routing

### 6.1 Direct Addressing

The simplest route: `sender_actor` → `intended_recipient`.

A message from `openclaw` to `hermes` is delivered to the Hermes surface via whatever transport the sender chose.

### 6.2 Subcomponent Routing

Subcomponent addressing uses the `/` separator:

- `hermes/bus-watcher` → Hermes Bus Watcher
- `hermes/gateway` → Hermes Gateway

The top-level agent ID is responsible for routing to its subcomponents. Subcomponent addresses are registered in the agent registry (§10).

### 6.3 Broadcast & CC

- **CC recipients** (`cc_recipients`) are informational — they receive a copy but MUST NOT act without explicit addressing
- There is no wildcard/broadcast addressing in v1; `cc_recipients` is the only multi-target mechanism

### 6.4 Cross-Transport Routing

When a message originates on one transport and must reach a recipient on another, a **bridge** performs the projection:

```
Transport A → Bridge Adapter → Transport B
```

Bridges MUST:
- Preserve all envelope fields (no lossy translation)
- Record the provenance: original `transport_kind` + original `message_id`
- Append bridge metadata to the envelope (not replace)
- Be registered in the bridge registry (§10)

### 6.5 Thread-Based Addressing (GitHub Bus)

On the GitHub Issues transport, each issue is a thread. Addressing is determined by:

- `intended_recipient` determines which agent's watcher picks up the issue
- Issue labels carry state routing: `status:awaiting-hermes`, `status:awaiting-cabra`, `agent:hermes`, etc.
- Label flip rules (see §8.1.3) enforce deterministic routing

---

## 7. Message Lifecycle

### 7.1 Message States

Every message passes through a lifecycle of processing states:

```
                    ┌──────────────┐
                    │   DRAFTED    │
                    └──────┬───────┘
                           │ send
                           ▼
                    ┌──────────────┐
                    │   SENT       │
                    └──────┬───────┘
                           │ transport delivery
                           ▼
                    ┌──────────────┐
              ┌────▶│   RECEIVED   │
              │     └──────┬───────┘
              │            │ parse & authenticate
              │            ▼
              │     ┌──────────────┐
              │     │ VALIDATED    │── schema, auth, fresh check
              │     └──────┬───────┘
              │            │ classify
              │            ▼
              │     ┌──────────────┐
              │     │  CLASSIFIED  │── turn type, semantics, authority mode
              │     └──────┬───────┘
              │            │ admission
              │            ▼
              │     ┌──────────────┐
              │     │  ADMITTED    │
              │     └──────┬───────┘
              │            │ execute (if executable)
              │            ▼
              │     ┌──────────────┐
              │     │  EXECUTING   │
              │     └──────┬───────┘
              │            │ complete
              │            ▼
              │     ┌──────────────┐
              │     │  COMPLETED   │
              │     └──────┬───────┘
              │            │ verify
              │            ▼
              │     ┌──────────────┐
              │     │  VERIFIED    │── terminal success
              │     └──────────────┘
              │
              │     ┌──────────────┐
              └─────│  REJECTED    │── any denial, quarantine, schema fail
                    └──────────────┘

                    ┌──────────────┐
                    │  FAILED      │── execution failure
                    └──────────────┘
```

### 7.2 Admission Verdicts

Per DAP §15.5, the admission verdict is one of:

| Verdict | Description | Proceeds to Execute? |
|---|---|---|
| `non_authoritative` | Message valid but lacks authority | No |
| `admitted` | All checks pass | Yes (if executable) |
| `denied` | Sender unauthorized or scope exceeded | No |
| `quarantined` | Suspicious or malformed | No |
| `escalated` | Needs higher-layer decision | No |

### 7.3 Execution Statuses

Per DAP §15.6, execution status is one of:

| Status | Description | Action Required |
|---|---|---|
| `not_started` | Waiting to begin | No |
| `deferred` | Will execute later | No |
| `running` | Currently executing | No |
| `completed` | Execution finished | Verification |
| `failed` | Execution failed | Remediation or escalation |
| `abandoned` | Execution was abandoned | Investigation |

### 7.4 Verification Statuses

Per DAP §15.7, verification status is one of:

| Status | Description |
|---|---|
| `unverified` | Not yet checked |
| `pending_review` | Under review |
| `insufficient_evidence` | Evidence does not meet policy requirements |
| `verified` | All checks pass |
| `rejected` | Evidence fails verification |

### 7.5 Lifecycle Integration with Turn Types

| Turn Type | Typical Lifecycle Path |
|---|---|
| `q` | DRAFTED → SENT → RECEIVED → VALIDATED → CLASSIFIED → ADMITTED (informational) → COMPLETED (answer given) |
| `do` | DRAFTED → SENT → RECEIVED → VALIDATED → CLASSIFIED → ADMITTED (if delegation valid) → EXECUTING → COMPLETED → VERIFIED |
| `a` | DRAFTED → SENT → RECEIVED → (informational processing, no execution) |
| `ack` | DRAFTED → SENT → RECEIVED → (transport receipt, no execution) |
| `done` | DRAFTED → SENT → RECEIVED → VALIDATED → (evidentiary claim, verification required) |
| `blk` | DRAFTED → SENT → RECEIVED → (fail-closed terminal) |
| `dec` | DRAFTED → SENT → RECEIVED → (fail-closed terminal, escalation) |

---

## 8. Transport Bindings

### 8.1 GitHub Issues (Canonical Control Plane)

#### 8.1.1 Mapping

The canonical control-plane channel is the GitHub Issues bus on `marcusglee11/agent-control-plane`.

| Envelope Field | GitHub Mapping |
|---|---|
| Full envelope JSON | Issue body top comment (in YAML compact profile) |
| `message_id` | Comment ID (auto-assigned by GitHub) |
| `created_at` | Comment timestamp |
| Threading | Each issue = one thread; `thread_id` = issue number |
| State routing | Issue labels: `status:*`, `agent:*` |

#### 8.1.2 Label Protocol

Routing labels:
- `agent:cabra`
- `agent:hermes`
- `agent:openclaw`

State labels:
- `status:awaiting-cabra`
- `status:awaiting-hermes`
- `status:awaiting-openclaw`
- `status:done`
- `status:blocked`
- `status:needs-decision`

#### 8.1.3 Label Flip Rules

When `to: hermes` (or any `intended_recipient`):
- Add `agent:<recipient>` label
- Add `status:awaiting-<recipient>`
- Remove all other `status:awaiting-*` and `status:done` labels

When `t: done`:
- Add `status:done`
- Remove all `status:awaiting-*` labels

When `t: blk`:
- Add `status:blocked`
- Remove all `status:awaiting-*`

When `t: dec`:
- Add `status:needs-decision`
- Remove all `status:awaiting-*`

#### 8.1.4 Watcher Contract

Each agent runs a bus watcher service that:
1. Polls or watches the canonical repo for new issues or comments
2. Filters by `agent:<self>` label or `to: <self>` field
3. Handles the message per this spec's lifecycle
4. Posts response as a new comment
5. Flips labels per §8.1.3

### 8.2 Direct CLI (Local Coordination)

#### 8.2.1 Mapping

The direct CLI channel is for ephemeral coordination between agents in local sessions.

| Envelope Field | CLI Mapping |
|---|---|
| Full envelope JSON | Injected as a structured message block |
| Delivery | In-process via agent-to-agent API or stdin/stdout |
| Durability | Ephemeral — no persistence guarantee |

#### 8.2.2 Authority Rules (DAP §4.6.2)

- CLI messages are **non-authoritative by default**
- If delegated authority is first exchanged on CLI, it MUST be projected to GitHub before execution
- Exception: ratified standing lanes MAY permit local inter-surface execution (§10.3)

#### 8.2.3 Delegation Projection

When a CLI message carries a `scope: delegated_execute`:

1. The sender MUST post a projection comment on the canonical GitHub issue
2. The projection comment carries the same `idempotency_key` and `message_id`
3. The receiver MUST NOT execute until the projection is confirmed on the canonical bus
4. The receiver SHOULD verify the projection's `hub_commit_sha` matches

### 8.3 Webhook (Event Channel)

#### 8.3.1 Mapping

Webhooks are used for asynchronous event delivery (e.g., GitHub webhooks → gateway).

| Envelope Field | Webhook Mapping |
|---|---|
| Full envelope JSON | POST body |
| `transport_kind` | `webhook` |
| Delivery | HTTP callback or gateway subscription |

#### 8.3.2 Rules

- Webhooks MUST carry `idempotency_key` for deduplication
- Webhook receivers MUST validate sender authenticity (HMAC or JWT)
- Webhook delivery is best-effort — senders SHOULD have a retry/backup mechanism
- Webhooks MUST NOT carry `scope: delegated_execute` unless the channel is explicitly authorized by a standing lane

### 8.4 File Handoff (Offline / Batch)

#### 8.4.1 Mapping

File handoffs are used for batch message exchange when agents are not simultaneously online.

| Envelope Field | File Mapping |
|---|---|
| Full envelope JSON | Written to a shared file |
| `transport_kind` | `file_handoff` |
| Delivery | File system polling or watcher |

#### 8.4.2 Rules

- File handoffs MUST include `expires_at` — stale files MUST be rejected
- File naming convention: `<correlation_id>_<attempt_number>_<message_id>.msg.json`
- Multiple messages in one file: JSONL format, one envelope per line
- Receivers MUST delete or archive processed files (idempotency prevents double-processing)

---

## 9. Security & Authority Integration

### 9.1 Delegation Carriage

A `do` message carrying authority MUST either:

**Option A — Inline delegation:**
The payload includes a `delegation` object conforming to DAP §10.3 fields.

**Option B — Delegation reference:**
The message references a pre-ratified standing lane:
```yaml
t: do
scope: delegated_execute
msg: |
  standing_lane_id: lane-health-checks-001
  action: run_smoke_test
  target: marcusglee11/lifeos-operational-bus
```

### 9.2 Admission Gate

Per DAP §14, every executable message (`do` with `scope: delegated_execute`) MUST pass the admission gate before execution:

1. **Sender authenticity** — Is `from` a known agent?
2. **Message validity** — Does the envelope conform to this spec?
3. **Delegation validity** — Does the delegation object have all required fields?
4. **Freshness** — Is `created_at` + `expires_at` window valid?
5. **Replay check** — Has `idempotency_key` been seen before?
6. **Channel admissibility** — Is `transport_kind` permitted for this authority scope?
7. **Target match** — Does `intended_recipient` match the receiver?
8. **Action scope** — Is the requested action within `allowed_actions`?
9. **Constraint satisfaction** — Are all constraints (repo, path, budget, etc.) met?
10. **Protected boundary** — Does this cross a protected boundary without CEO authorization?

### 9.3 Evidence Requirements

Per DAP §19, any `done` message claiming completion MUST include:
- Artifact path or URL (PR, commit, issue URL)
- Test results (pass/fail counts)
- Head SHA or equivalent identifier
- Evidence manifest conforming to `evidence_manifest_v1` schema for EA work

### 9.4 Channel Authority Rules

| Channel | Default Authority | Delegation Bearer? | Projection Required? |
|---|---|---|---|
| GitHub Issues | Authority-bearing | Yes | N/A (canonical) |
| Direct CLI | Non-authoritative | Yes, with projection | Yes |
| Webhook | Non-authoritative | Standing lane only | N/A |
| File Handoff | Non-authoritative | Standing lane only | N/A |

---

## 10. Registry Requirements

Per DAP §11.5, the following registries MUST exist and MUST use exact matching:

### 10.1 Agent Identity Registry

Declares all valid `sender_actor` / `intended_recipient` values.

```json
{
  "registry": "agent-identities",
  "version": "1",
  "agents": [
    {"id": "cabra", "display_name": "Marcus (CEO)", "role": "ceo"},
    {"id": "hermes", "display_name": "Hermes", "role": "executor",
     "subcomponents": ["bus-watcher", "gateway"]},
    {"id": "openclaw", "display_name": "OpenClaw", "role": "coordinator"},
    {"id": "codex", "display_name": "Codex", "role": "ea"},
    {"id": "claude-code", "display_name": "Claude Code", "role": "ea"},
    {"id": "hermes-gw", "display_name": "Hermes Gateway", "role": "daemon"}
  ]
}
```

### 10.2 Communication Surface Registry

Declares all valid `transport_kind` values and their bindings. Source: `current-protocol.json`.

### 10.3 Bridge Registry

Declares all valid bridge adapters for cross-transport routing.

### 10.4 Policy Basis Registry

Declares all recognized `policy_basis` identifiers per DAP §11.5.

---

## 11. Normative References

| Ref | Document | Location |
|---|---|---|
| DAP | Delegated Authority Protocol v0.3-ratified | `agent-control-plane/docs/delegated-authority-protocol-v0.3-ratified.md` |
| Env | Transport Envelope schema | `lifeos-common-hub/schemas/transport_envelope.schema.json` |
| BPR | Bilateral Protocol Requirements | `lifeos-common-hub/standards/bilateral-protocol/REQUIREMENTS.md` |
| SM | Surface Map | `agent-control-plane/contracts/current-protocol.json` |
| ADC | Agent Dispatch Contract | `lifeos-common-hub/schemas/agent_dispatch_contract.schema.json` |
| EM | Evidence Manifest | `lifeos-common-hub/schemas/evidence_manifest_v1.schema.json` |
| SRC | State Read Contract | `lifeos-common-hub/schemas/state_read_contract.schema.json` |

---

## Appendix A: Quick Reference

### A.1 Envelope Field Summary

| Field | Required? | Compact Key | Type | Notes |
|---|---|---|---|---|
| `message_id` | Yes | `msg_id` | string (ULID/UUID) | Unique per sender |
| `correlation_id` | Yes | `cid` | string | Thread grouping |
| `causation_id` | Yes | `causation_id` | string | Points to cause |
| `root_objective_id` | Yes | `root` | string | Top-level objective |
| `sender_actor` | Yes | `from` | agent_id | Registered identity |
| `sender_role` | Yes | `role` | string | Semantic role |
| `intended_recipient` | Yes | `to` | agent_id[/sub] | Target |
| `cc_recipients` | No | `cc` | agent_id[] | Visibility |
| `authority_scope` | Yes | `scope` | enum | DAP §8 values |
| `transport_kind` | Yes | (implicit) | enum | github_issue, webhook, etc. |
| `schema_name` | Yes | `sch` | string | Payload schema ID |
| `schema_version` | Yes | `sch_v` | string | Payload schema version |
| `hub_commit_sha` | Yes | `hub` | string (hex) | lifeos-common-hub pin |
| `created_at` | Yes | `iat` | ISO 8601 UTC | Message creation time |
| `expires_at` | Yes (nullable) | `exp` | ISO 8601 UTC | Expiry or null |
| `idempotency_key` | Yes | `ik` | string | Deduplication |
| `attempt_number` | Yes | `att` | integer >= 1 | Retry counter |
| `payload_hash` | Yes | (computed) | string (hex) | SHA-256 of payload |
| `payload` | Yes | `msg` | object/string | Message content |

### A.2 Turn Type Decision Matrix

| You want to... | Use turn | rr | Valid responses |
|---|---|---|---|
| Ask a question | `q` | 1 | `a` |
| Request action (with delegation) | `do` | 1 | `ack` → `done` |
| Propose a plan (no authority) | `do` | 1 | `a` (accept/reject) |
| Answer a question | `a` | 0 | — |
| Confirm receipt | `ack` | 0 | — |
| Report completion | `done` | 0 | — |
| Report blocked | `blk` | 0 | — |
| Escalate for decision | `dec` | 1 (to CEO) | — |

### A.3 State Labels Quick Map

| State | Label | Turn That Produces It |
|---|---|---|
| Awaiting sender | `status:awaiting-<actor>` | Sender posts, flips to recipient |
| Done | `status:done` | `t: done` |
| Blocked | `status:blocked` | `t: blk` |
| Needs decision | `status:needs-decision` | `t: dec` |
