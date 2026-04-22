````markdown
# LifeOS Target Architecture — v2.3c

**Date:** 2026-04-17  
**Status:** Canonical pass draft — ready for ratification  
**Supersedes:** LifeOS Target Architecture v2.3 (2026-04-17)  
**Purpose:** Define the operational architecture for LifeOS agent orchestration  
**Changes from v2.3:** Resolves remaining post-review blockers and micro-integration gaps: fixes CEO/COO authority contradiction in transition law, aligns state machine vocabulary to EA result schema, adds `attempt_id` to the EA result payload, restores missing `running → blocked` and `running → needs_decision` transitions, normalises the Commons Phase 1 interface model to in-process validation plus direct file reads from the local clone, makes `workflow_run_id` provenance explicit in the idempotency model, and adds malformed-result handling while still in `dispatched`.

---

## 1. Problem statement

LifeOS has a working autonomous build spine (validated W5-T01, 2026-02-14: hydrate → policy → design → build → review → steward, 1527 passing tests). The spine is not the problem.

The problem is that nothing can reliably trigger the spine and receive its outputs without the CEO manually acting as the context bus between agents. The CEO is currently the integration layer — copying prompts, pasting results, carrying state between sessions. This is the binding constraint on the entire system.

The target architecture solves this by introducing a COO agent layer that creates work orders, monitors execution, and reports results, reducing the CEO’s role from operational relay to direction, approval, and escalation authority.

---

## 2. Actors

### 2.1 CEO (human)

- Sets objectives and strategic direction
- Holds ultimate authority over all decisions (Constitution: CEO Supremacy invariant)
- Issues commands via messaging channel (Telegram or CLI)
- Commands are structured (slash commands with typed parameters in early phases, progressing to natural language in later phases)
- Receives reports and escalations from COO
- Consults advisory agents (Claude.ai, ChatGPT) for strategy, research, and review — these are not in the operational loop

### 2.2 COO (OpenClaw or Hermes, replaceable via adapter)

The COO is not a pure router. It is an **operational decision-maker with bounded, phase-scoped discretion**. Its authority expands across phases; in Phase 1 it is tightly constrained.

Responsibilities common to all phases:

- Receives CEO commands via messaging channel
- Validates commands against canonical command schema and known task templates
- Creates GitHub issues with structured prompts and labels
- Monitors GitHub for execution results (via COO Commons webhook forwarding, with cron as fallback for proactive work — see Section 2.6)
- Reports results and escalations to CEO via messaging channel
- Performs tool and API actuation, GitHub state mutations — the COO does not execute task work or modify repository contents as an EA; it does perform GitHub API mutations required for orchestration
- Reads phase configuration and policy rules from COO Commons (Section 2.6) as data inputs. Does not define these assets internally.
- Performs deterministic schema validation via the COO Commons validation library before any schema-dependent state transition. Does not substitute substrate reasoning for schema validation.
- Replaceable via adapter layer — true hot-swap requires stable contracts (command schema, state-read contract, result interpretation, escalation schema, retry rules). The GitHub bus alone does not make the COO interchangeable. COO Commons (Section 2.6) provides the shared deterministic assets that make replacement tractable; it does not eliminate substrate-specific judgment behaviour.
- The operational constraints in this role are architectural rules imposed by LifeOS operating policy. They are not intrinsic substrate limitations.

Phase-specific authority — see Section 5.

### 2.3 GitHub (deterministic relay bus and evidence surface)

- Central communication channel for all operational traffic
- Issues = **canonical work-order objects** (see Section 4)
- Workflows = event-driven dispatch (trigger on issue creation/labeling)
- PRs and commits = execution evidence
- Issue/PR comments = structured status reports from executing agents
- GitHub Projects v2 = **projection/index over canonical issue state**, used for planning and visibility (NOT the deepest source of truth)
- Webhooks = push notifications to COO Commons ingestion service for relevant workflow, issue, and result events
- GitHub-resident work-order state transitions are visible, versioned, and auditable

### 2.4 Executing agents (EAs)

- Stateless workers. They exist only for the duration of a workflow run.
- Receive a self-contained prompt from the issue body
- Execute in a shell environment on the self-hosted runner (local machine initially, hosted later)
- Write results back to GitHub (PR, commit, structured issue comment conforming to the COO ↔ EA schema in Section 4.5)
- Do not poll, do not choose work, do not maintain state between runs
- Do not modify the structured state block in the issue body (Section 2.6.3.6). EAs are evidence producers, not state mutators.
- Current lanes:
  - Claude Code lane: GitHub Actions workflow → claude CLI → PR
  - Codex lane (Path B): GitHub Actions workflow → codex exec --full-auto → PR
- Additional lanes can be added by defining new workflow files and label routing

### 2.5 Advisory agents (Claude.ai, ChatGPT)

- Consulted by CEO for strategy, research, architecture review, adversarial analysis
- Read operational state from GitHub (via API, MCP, or Drive mirror) at session start
- Not in the operational loop — they do not trigger workflows, create issues, or receive webhooks
- The CEO is the bridge between advisory and operational layers (this manual handoff remains but shrinks from full context transplant to a short message)

### 2.6 COO Commons (shared services layer)

#### 2.6.1 Purpose

The COO substrate (Section 2.2) is explicitly designed to be replaceable. Replacement is only viable if the deterministic logic required to meet LifeOS operational requirements is not embedded inside the substrate.

COO Commons is a substrate-independent shared services layer that:

- Contains deterministic shared assets consumed by any COO substrate — schemas, validators, policy data, and webhook ingress
- Exposes stable, versioned interfaces that substrates call; substrates do not own the authoritative definitions of these assets. Thin substrate-side adapter logic to consume Commons outputs is permitted and expected; substrate-internal redefinition of the assets themselves is not.
- Is version-controlled in the LifeOS GitHub repository, independent of any substrate's upgrade path

COO Commons is not a second COO. The COO substrate remains the operational decision-maker with bounded, phase-scoped discretion (Section 2.2). Commons supplies deterministic inputs to those decisions; it does not make them. If Commons begins accumulating decision-making logic, that is an architectural violation, not an extension.

#### 2.6.2 Role division

**The substrate provides:** operational judgment, tool and API actuation, GitHub state mutations, message generation, and interpretation of ambiguous EA outputs.

**Commons provides:** webhook ingestion and event normalisation, formal schema definitions, deterministic schema validation, and phase and policy configuration as data.

This division is intentional and load-bearing. Deterministic shared functions belong in Commons. Interpretive, judgment-based, and communication behaviour remain in the substrate. The boundary must be actively maintained — Commons must not accumulate decision-making logic by stealth.

Command schema is part of the replaceability contract. If the structure of commands from the CEO to the COO is substrate-specific, the COO interface contract is incomplete at its entry point — substrate replacement would require re-training or reconfiguring the CEO's interaction pattern, not just rewiring Commons interfaces. Command schema therefore belongs in Commons (`/commons/schemas/commands/`) and is a first-class replaceability condition. A COO substrate that cannot consume the canonical command schema is not a conformant substrate for this architecture.

#### 2.6.3 Operational interfaces

##### 2.6.3.1 Webhook ingestion service

Commons operates the sole public-facing webhook endpoint and event preprocessing pipeline.

GitHub webhook events are ingested, deduplicated, and forwarded to the active substrate. Deduplication is performed at Commons using a local, append-only ingestion log keyed by `X-GitHub-Delivery` header. Duplicate deliveries (by header) are discarded. The ingestion log is not committed to GitHub.

Commons forwards ingested events to the active substrate only. The standby substrate receives no forwarded events. Active/standby designation is set by topology config. Routing changes only on explicit, logged switchover.

Webhook events that cannot be ingested due to malformed payloads or unrecognised event types are logged but do not cause ingestion service failure. Notable failures are escalated to the COO for GitHub-visible action.

The Commons webhook ingestion service is a readiness gate for the substrate. If the substrate declares itself ready to receive event traffic but the ingestion service cannot forward events to it, the substrate is treated as not ready. If the substrate internal ingress cannot accept forwarded events, the substrate is treated as not ready.

##### 2.6.3.2 Schema validation library

Commons provides a callable local schema-validation library for Phase 1. It is consumed in-process by the active substrate; it is not a network API in Phase 1.

The library validates:
- COO ↔ EA result payloads
- State-transition-dependent payloads
- Internal structured data exchanged across Commons-owned contracts

Schemas are versioned in the Commons schema registry. The substrate calls the validation library with a payload and schema identifier; it does not embed copies of the schemas internally. This preserves deterministic contract enforcement while keeping the Phase 1 interface surface minimal.

Schema migration policy for in-flight issues is defined per version increment.

##### 2.6.3.3 Phase and policy data

Commons defines the authoritative phase and policy configuration as repository-tracked data in the local LifeOS clone used by the active substrate.

These data include:
- Phase capability definitions (what the COO may autonomously perform per phase)
- Policy rules (timeout thresholds, retry limits, escalation triggers)
- Task template definitions (structured prompt templates per task type)

These are configuration data, not runtime policy logic. The substrate reads them directly from the local clone after repository-currency verification (Sections 2.6.3.4–2.6.3.5). Commons does not make policy decisions directly.

Configuration is versioned by canonical repository commit history. The configuration used for a decision cycle must correspond to the verified local HEAD for that cycle.

##### 2.6.3.4 Configuration access rules

The substrate must verify that the local repository clone is current (local HEAD SHA matches GitHub API) before reading Commons configuration data on each decision cycle. Failure to verify local repository currency triggers Commons unavailable status.

##### 2.6.3.5 Configuration read protocol

Before each COO decision cycle, the substrate:

1. Verifies local HEAD SHA matches GitHub API
2. Reads phase, policy, and task-template configuration directly from the verified local clone
3. Caches config data for the current cycle only
4. Does not persist cached config across cycles or restarts

This keeps the Phase 1 config path deterministic and fail-closed while avoiding an unnecessary local service boundary.

##### 2.6.3.6 State block management

The COO substrate is the sole writer of the structured state block in GitHub issue bodies.

The state block stores operational counters and tracking data:

- Current state per state machine (Section 4.4)
- Dispatch timestamp (`dispatch_started_at`)
- Attempt counters
- Retry/redirect lineage
- Deadline calculations

**Issue body update protocol:**

1. Read current issue body and record concurrency token: use issue ETag if available via GitHub API response headers; otherwise compute hash of the raw issue body text; fall back to `updated_at` only if neither is available.
2. Compute candidate state block mutation in memory.
3. Before writing, verify concurrency token is unchanged since step 1.
4. If unchanged: write.
5. If changed: re-read, recompute, retry. Maximum retries: 3.
6. If retries exhausted: do not write; escalate to CEO with last-known state, candidate mutation, and concurrency token mismatch evidence.

The schema defines the structure and constraints of the state block. The update protocol prevents clobber conflicts under concurrent automation.

#### 2.6.4 Decision-layer idempotency

**Correlation key:** `issue_id + attempt_id + workflow_run_id`

**attempt_id:** Generated by the COO at each `→ dispatched` transition (initial dispatch or retry). Written to the issue state block. Propagated into workflow dispatch inputs and required in EA result payloads. The COO is the sole generator.

**workflow_run_id:** Sourced from GitHub workflow/run webhook metadata, not generated by the EA. The active substrate joins EA result payloads to workflow events using (`issue_id`, `attempt_id`) plus the associated GitHub workflow metadata for that attempt. `workflow_run_id` is part of the decision correlation key even when it is not echoed in the EA result schema.

**Protocol:**

- Each unique correlation key may drive at most one completed decision cycle.
- On decision cycle completion, the key is recorded as decided in the decision correlation ledger (durable, survives restart, append-only).
- Second arrival for a decided key: logged and discarded at the substrate's decision-entry path. Not at ingress.
- Ingress dedup log and decision correlation ledger are separate artefacts with separate purposes.

**Ownership:** Ingress dedup is a Commons responsibility. Decision-layer idempotency is enforced at the active substrate's decision-entry/mutation path. Commons does not participate in decision idempotency.

#### 2.6.5 Fail-closed on Commons unavailable

If Commons is unavailable (webhook ingestion service down, configuration data unreachable, or local repository clone out of currency), the substrate defaults to fail-closed: no dispatch, no state transitions based on new inputs, no autonomous operation.

Substrate-internal functions that do not depend on Commons (e.g., reading past issue state, generating reports from already-available data) are not affected. Only operations that require Commons data or Commons event forwarding are halted.

**Control-plane liveness dependency:** Control-plane liveness in Phase 1 depends on GitHub API reachability for config verification. A GitHub API outage halts dispatch even when local state and webhook ingestion are healthy. Known Phase 1 constraint; revisit at Phase 2.

#### 2.6.6 Topology and switchover

Commons supports one active substrate and one standby substrate in Phase 1. The standby substrate receives no forwarded events during normal operation; it serves as a cold failover.

The standby substrate is operationally inert but remains connected to Commons for configuration access. If configuration is unavailable, both substrates are fail-closed.

**Switchover procedure:** (1) stop Commons forwarding to active, (2) drain in-flight deliveries — all deliveries received before stop signal have completed decision cycle, (3) quiesce active substrate mutation workers, (4) verify no open decision cycle on any issue, (5) activate standby, (6) resume forwarding to new active, (7) log switchover event with timestamp.

#### 2.6.7 Commons operational characteristics

COO Commons is co-hosted with the substrate in Phase 1 on the same local machine. The components are deployed together and restarted together. This avoids the independent availability requirement that would emerge from separate hosting.

The Commons webhook ingestion service has no built-in redundancy in Phase 1. Single instance failure causes control-plane unavailability.

Planned upgrade: separate Commons hosting for Phase 2 to enable substrate switchover without Commons downtime.

### 2.7 Google Drive

- Read-only mirror of key documents for human consumption
- NOT a source of operational truth
- NOT a shared state store
- Sync is periodic and one-directional: GitHub → Drive

---

## 3. Communication flows

### 3.1 Forward path (CEO → EA execution)

1. CEO sends structured command to COO via messaging channel
2. COO validates against canonical CEO→COO command schema and task template, fills parameters, selects agent lane
3. COO creates GitHub issue with structured body + agent label (e.g., `agent:claude-code`)
4. GitHub detects issue event, triggers matching workflow
5. Workflow spins up on self-hosted runner, EA executes prompt from issue body
6. EA writes results: code committed, PR opened, structured comment posted on issue (per Section 4.5 schema)

### 3.2 Return path (EA result → CEO)

1. EA posts structured result comment on issue and/or opens PR
2. GitHub fires webhook to COO Commons ingestion service (push, immediate)
3. Commons forwards webhook to active substrate (standby receives no events)
4. COO reads result, updates issue state and project projection, decides next action
5. COO messages CEO with result summary and any escalations
6. Fallback: if webhook delivery fails or arrives out of order, COO reconciliation loop (Section 3.6) catches the drift

### 3.3 Retry vs redirect (formally distinguished)

**Retry** = same task, materially same plan, transient failure.

- COO updates existing issue (comment, re-trigger workflow via label flip)
- Issue identity preserved
- Permitted without CEO approval in Phase 2B and later

**Redirect** = new approach, different plan, same underlying objective.

- COO creates a new issue with explicit parent/child link to the original
- Original issue transitions to `blocked` or `superseded`
- Requires CEO approval in Phase 1–2; permitted with escalation notice in Phase 3+

Neither retry nor redirect may exceed bounded attempt limits (default: 2 retries, 1 redirect). Beyond limits: escalate to CEO.

### 3.4 Proactive path (COO-initiated, no CEO trigger)

1. COO cron fires on schedule
2. COO reads canonical issue state (and project projection for planning views)
3. COO selects eligible work per Phase 2A routines or runs maintenance routine
4. COO creates issue, triggering EA execution
5. COO reports results to CEO on next heartbeat or immediately for high-priority items

### 3.5 Advisory path (CEO ↔ advisory agents)

1. CEO opens session with Claude.ai or ChatGPT
2. Advisory agent reads current state from GitHub or Drive mirror
3. CEO and advisory agent discuss strategy, review architecture, research options
4. CEO distills actionable outcomes into commands for COO
5. Advisory agents never write to GitHub or trigger workflows directly

### 3.6 Reconciliation loop

Beyond webhook + cron heartbeat, COO runs a periodic reconciliation pass:

- Walks all issues in non-terminal states relevant to automation and exception handling (`ready`, `dispatched`, `running`, `timed_out`, `needs_decision`)
- Verifies expected next event or decision has occurred within timeout or holding rules for each state
- Flags issues stuck in a state beyond threshold as anomalies
- Default action on anomaly: escalate to CEO (not auto-recover)

Reconciliation catches: dropped webhooks, workflow-side failures that do not post a result comment, partial completions where PR exists but result comment schema is malformed, and semantic drift detected by output validators.

---

## 4. State management

### 4.1 Canonical state hierarchy

One canonical operational record per work item. Surfaces have defined roles and cannot compete:

| **Surface** | **Role** | **Authority** |
|---|---|---|
| GitHub Issue body + state block | Canonical work-order object and lifecycle state | Single source of truth for work-order state |
| Issue labels | Typed metadata (lane, type, phase, status) | Machine-readable routing and filtering |
| Project v2 fields | Projection/index for planning views | Derived from issue state; no independent authority |
| PR and commits | Execution evidence | Immutable record of what the EA did |
| Issue comments | Status reports and results (per Section 4.5 schema) | Evidence, not state |
| Pinned STATE summary | Human-readable narrative | Derivative only; updated by COO on heartbeat |

**Conflict resolution rule:** Issue body + labels win. All other surfaces are derived. If a project field disagrees with issue state, the issue is authoritative and the projection is out of date.

### 4.2 State access patterns

- COO: reads and writes via GitHub API/GraphQL
- EAs: read repo state during workflow checkout; write results as PRs and structured comments
- Advisory agents: read via GitHub API, MCP, or Drive mirror
- CEO: reads via GitHub web UI, Projects board, or COO reports

### 4.3 State mutation rules

**CEO authority is exercised by directing the COO; the COO is the sole execution agent for all canonical state mutations.** The CEO never writes directly to canonical state surfaces (issue body, labels, state block). CEO authority is real and supreme; its expression is via COO execution, not direct mutation.

State mutations go through GitHub API (issue updates, comments, label changes) or PR (code/file changes). Markdown state files (`LIFEOS_STATE.md`, `BACKLOG.md`) are transitional — replaced by issue + project state. Narrative STATE summary is the only remaining markdown artifact.

### 4.4 Work-order transition law

Every work-order issue follows an explicit state machine. States, valid transitions, and authority are defined below.

**States:**

| State | Meaning | Entry evidence |
|---|---|---|
| `backlog` | work identified but not yet ready to dispatch | |
| `ready` | fully specified, awaiting dispatch | |
| `dispatched` | Trigger sent; awaiting GitHub acknowledgement | COO issued trigger; `dispatch_started_at` written to state block |
| `running` | GitHub acknowledged; workflow executing | `workflow_run` event with status `in_progress` received by COO |
| `succeeded` | EA completed, result accepted | |
| `failed` | EA completed with error, no recovery attempted | |
| `blocked` | external dependency or decision required | |
| `needs_decision` | COO cannot proceed without CEO input | |
| `superseded` | replaced by a redirect (parent of new issue) | |
| `timed_out` | Deadline exceeded; no valid result received | Reconciliation detects `now > dispatch_started_at + policy_timeout` |

**New event classification (not a state):**

| Classification | Meaning | Handling |
|---|---|---|
| `late_result` | Valid result received when issue is not in `running` or `dispatched` | Logged; escalated to CEO; not applied; no state transition |

**Valid transitions:**

| From | Event | To | Action |
|---|---|---|---|
| `backlog` | Parameters filled, template validated | `ready` | COO |
| `ready` | Workflow triggered | `dispatched` | COO |
| `dispatched` | `workflow_run in_progress` received | `running` | Update state block |
| `dispatched` | Valid result received, `status=succeeded` (fast execution) | `succeeded` | Compressed transition; no intermediate GitHub state write |
| `dispatched` | Valid result received, `status=failed` (fast execution) | `failed` | Compressed transition; no intermediate GitHub state write |
| `dispatched` | Valid result received, `status=blocked` (fast execution) | `blocked` | Compressed transition; no intermediate GitHub state write |
| `dispatched` | Valid result received, `status=needs_decision` (fast execution) | `needs_decision` | Compressed transition; no intermediate GitHub state write; timer halted; escalated |
| `dispatched` | Malformed result received | `needs_decision` | Schema rejection; timer halted; escalated |
| `running` | Valid result received, `status=succeeded` | `succeeded` | COO applies and closes |
| `running` | Valid result received, `status=failed` | `failed` | COO applies; retry policy evaluated |
| `running` | Valid result received, `status=blocked` | `blocked` | COO applies; escalates or waits on dependency |
| `running` | Valid result received, `status=needs_decision` | `needs_decision` | COO escalates to CEO; timer halted |
| `running` | Malformed result received | `needs_decision` | Schema rejection; timer halted; escalated |
| `running` | Deadline exceeded | `timed_out` | Reconciliation triggers |
| `failed` | Retry (same plan) | `dispatched` | CEO approval in Phase 1; COO autonomous in Phase 2B; `dispatch_started_at` overwritten; new `attempt_id` generated |
| `failed` | Redirect (new plan) | `superseded` | CEO approval in Phase 1–2; COO with escalation notice in Phase 3+ |
| `timed_out` | CEO approves retry | `dispatched` | `dispatch_started_at` overwritten; new `attempt_id` generated |
| `timed_out` | Valid result arrives late | — | Classified as `late_result`; logged; escalated to CEO; not applied |
| `needs_decision` | CEO provides direction | `ready` or `blocked` | COO executes the directed mutation |

**Timeout anchor:** `dispatch_started_at` is written to the state block at every `→ dispatched` transition, including retries. It is overwritten, not preserved, on retry. All timeout calculations reference the current value of this field.

**`timed_out` is not a terminal state:** it is a holding state. Outbound path is `→ dispatched` via CEO-approved retry only in Phase 1. No autonomous recovery.

**`late_result` is an event classification, not a state:** it does not appear in the state machine as a reachable state from normal transitions. It is a label applied to an incoming event when the issue is not in `running` or `dispatched`.

**Evidence requirements for each transition are documented in the issue template and enforced by output validators (see Sections 7.1 and 11.1).**

### 4.5 COO ↔ EA interface contract

All EA result comments conform to a strict JSON schema embedded in the issue comment. This prevents silent semantic drift at the interface boundary and supplies the fields required for decision-layer idempotency.

```json
{
  "schema_version": "1.0",
  "issue_id": "<github_issue_number>",
  "attempt_id": "<coo_generated_attempt_id>",
  "status": "succeeded | failed | blocked | needs_decision",
  "summary": "<brief human-readable result>",
  "evidence": {
    "pr_url": "<if applicable>",
    "commit_sha": "<if applicable>",
    "artifacts": ["<paths>"],
    "test_results": "<pass/fail summary>"
  },
  "next_action_hint": "retry | redirect | escalate | none",
  "failure_details": "<structured failure info if status != succeeded>"
}
````

`attempt_id` is required. It is injected by the COO into workflow dispatch inputs at each `→ dispatched` transition and is passed through the workflow to the EA result payload unchanged.

`workflow_run_id` is sourced from GitHub workflow webhook metadata rather than generated by the EA. The COO joins result payloads to workflow events using (`issue_id`, `attempt_id`) plus the associated workflow metadata for that attempt.

COO validates every EA result comment against this schema via the Commons validation library. Malformed comments are treated as anomalies and escalated — they do not produce state transitions.

Similarly, COO commands to EAs (via issue body) follow a strict task template schema per task type (`build`, `test`, `stewardship`, `research`, `data-refresh`, `backtest`). Issue creation that fails schema validation is rejected before dispatch.

---

## 5. Phased capability rollout

The COO's authority is introduced incrementally. Each phase requires explicit capability qualification before progressing.

### Phase 1: Deterministic dispatcher (CEO is the brain)

**COO authority:**

* Validate typed commands against canonical command schema and known templates
* Create issues from strict templates with no creative rewriting
* Post structured summaries per schema
* Update minimal set of project projection fields

**COO explicitly may NOT:**

* Rewrite prompts creatively
* Choose alternate approaches
* Infer missing parameters (escalate instead)
* Manage ambiguous retries (escalate instead)

**CEO responsibilities:**

* Issue slash commands with typed parameters
* Approve all retries and redirects
* Review any escalation

**Qualification to advance:** reliable dispatch determinism — commands map to correct issues with correct templates, labels, and parameters, measured over a representative task set.

### Phase 2A: Scheduled deterministic routines

**Added COO authority:**

* Execute pre-defined cron routines (backlog scan, state summary, scheduled data refresh)
* Select eligible work from backlog per defined priority rules
* Report routine outcomes on heartbeat

**Still requires CEO approval:** any retry, any redirect, any task not in the pre-defined routine set.

**Qualification to advance:** routines run reliably over a defined period with all failures escalated correctly (no silent failures).

### Phase 2B: Bounded recovery routines

**Added COO authority:**

* Retry failed tasks under bounded limits for known transient failure types (network timeout, rate limit, runner unavailable)
* Apply known recovery patterns from a whitelist

**Still requires CEO approval:** any redirect, any recovery not matching a whitelisted pattern.

**Qualification to advance:** recovery decisions are correct in a representative sample and escalation threshold is calibrated (neither too eager nor too passive).

### Phase 3: Intent interpretation

**Added COO authority:**

* Parse natural language commands for known task types
* Infer templates and parameters from context
* Dispatch low-stakes tasks without approval
* Request CEO approval for medium-stakes tasks (approval gate)

**Still requires CEO approval:** novel task types, high-stakes tasks (defined by stakes field in template).

**Qualification to advance:** intent-to-template mapping accuracy exceeds threshold on a representative set, and the system demonstrates correct behavior on ambiguous inputs (escalates rather than guesses).

### Phase 4: Decomposition and planning

**Added COO authority:**

* Decompose novel objectives into task sequences
* Manage dependencies between tasks
* Handle multi-step orchestration

**CEO responsibilities:**

* Approve plans, not individual tasks
* Review distilled recommendations

**Qualification:** decomposition quality demonstrated on representative problems with acceptable failure modes.

---

## 6. Infrastructure

### 6.1 Self-hosted runner (local machine, initial phase)

* Runs GitHub Actions workflows locally
* Hosts EA execution (Claude Code CLI, Codex CLI)
* Must be on and awake for execution to occur
* Overnight autonomy requires machine to stay running
* Migration to hosted runner (GCP or GitHub-hosted) planned for hardening phase

### 6.2 COO hosting (local machine, initial phase)

Commons owns and operates the sole public-facing webhook endpoint. The active substrate has no public-facing endpoint. All inbound GitHub webhook traffic enters exclusively via Commons. The substrate receives only events that Commons has ingested, deduplicated, and forwarded.

COO Commons is co-hosted with the substrate in Phase 1. Migration to GCP or VPS planned for always-on operation.

### 6.3 GitHub (SaaS, free tier)

* Issues, Projects v2, Actions, webhooks, API — all included in free plan
* Self-hosted runner execution does not consume Actions minutes quota
* 2,000 free Actions minutes/month available if GitHub-hosted runners are used later

### 6.4 API costs (variable)

* Claude API (for Claude Code EA lane)
* OpenAI API (for Codex EA lane)
* COO model API (depends on which COO platform is used)

### 6.5 Commons infrastructure

COO Commons components are co-hosted with the substrate on the local machine in Phase 1:

* Webhook ingestion service (HTTP endpoint, event preprocessing)
* Schema validation library (in-process, called by the active substrate)
* Configuration files in the local verified git clone (`phase`, `policy`, task templates)
* Dedup ledgers (local append-only files)

Commons and substrate restart together. Commons unavailability = substrate fail-closed.

---

## 7. Known risks and open problems

### 7.1 Semantic drift (highest risk)

The most likely damaging failure mode is not a system crash or dropped webhook. It is the COO emitting issues that are syntactically valid but semantically off-target. Because the pipeline executes cleanly, the system appears healthy while doing the wrong work.

**Mitigations:**

* Strict schema validation at the COO ↔ EA boundary (Section 4.5)
* Output validators on EA results (verifying results match task intent, not just schema)
* Reconciliation loop flags anomalies rather than auto-recovering
* Phase 1 scripted routing prevents most drift at source; drift risk increases in Phase 3 and 4

This is the primary adversarial concern and warrants dedicated detection tooling before Phase 3.

### 7.2 Task decomposition quality

Whether the COO can reliably turn high-level intent into self-contained prompts that execute without human context. Deferred to Phase 4 and mitigated by phased rollout starting with scripted templates.

### 7.3 EA output interpretation

When an EA returns ambiguous, partial, or conflicting results. Early phases default to escalation. Structured result schema (Section 4.5) makes most cases mechanically disambiguable.

### 7.4 Cross-agent memory

EAs start clean every run. Learning persists only if committed to the repo. Workflow prompts include standard instruction to write findings to designated artifact paths. COO accumulates operational context across runs via issue threads and project state.

### 7.5 Self-hosted runner as single point of failure

Local machine off = no EA execution. Acceptable for initial phase. First hardening step is migration to always-on hosted infrastructure.

### 7.6 Webhook reliability

GitHub webhook delivery is not guaranteed. Webhooks can be delayed, dropped, or delivered out of order. Mitigated by: Commons-level dedup at ingestion (Section 2.6.3.1), decision-layer idempotency (Section 2.6.4), reconciliation loop (Section 3.6), cron heartbeat fallback, and explicit timeout windows per state.

### 7.7 Multi-step orchestration

If task A depends on task B's output, COO must sequence them. GitHub does not do this natively. COO handles it via transition law and parent/child issue links. Complex dependency chains deferred to Phase 4 with potential use of spine's checkpoint/resume capability.

### 7.8 Phase boundary leakage

Phase boundaries are conceptually clean but operationally leaky. Even Phase 1 requires some interpretation for malformed inputs. Mitigated by: hard escalation defaults when in doubt, explicit qualification gates between phases, and clear authority tables (Section 5) that specify what each phase permits.

### 7.9 COO Commons as single point of failure

COO Commons — specifically the webhook ingestion service — is a new always-on dependency. If Commons is unavailable, the COO is fail-closed and cannot dispatch (Section 2.6.5). In Phase 1, Commons is co-hosted with the substrate; a machine restart takes both down simultaneously, which is acceptable. The risk increases when Commons and substrate are hosted separately in later phases — Commons availability becomes an independent requirement. Mitigated for Phase 1 by co-location; revisited at hosting migration.

---

## 8. What this architecture does NOT solve

1. The manual handoff between advisory sessions and the operational loop remains (shrinks but does not disappear)
2. Revenue generation is a separate workstream that uses this operational capacity
3. The governance framework (Constitution, audit completeness, reversibility) applies to spine-connected tasks but not to raw CLI execution — reconnecting governance is a future step
4. Real-time or long-running processes (live trading bots, persistent services) are outside the request/response model of GitHub Actions
5. Full identity/credential/audit separation (actor identity model, scoped credentials, mutation scope enforcement) deferred to hardening phase
6. Substrate replaceability is partial — COO Commons standardises deterministic interfaces but does not standardise judgment quality (Section 2.6.2)

---

## 9. Deferred complexity

The following were considered and rejected for early phases:

* **Dedicated message broker (Redis, RabbitMQ, SQS):** GitHub webhook + Commons dedup + reconciliation loop is sufficient at current scale. Revisit if volume exceeds 100 tasks/day or latency becomes a binding constraint.
* **Dedicated state database (PostgreSQL, Temporal):** GitHub issues + projects is sufficient at current scale. Revisit if concurrency or transactional requirements emerge that GitHub cannot serve.
* **Full idempotency keys and dead-letter queues:** Commons dedup window + decision-layer idempotency + reconciliation loop + escalation on anomaly serves the same purpose with less machinery. Revisit if silent duplicate execution becomes observed at scale.
* **Full identity/credential model:** one human, one COO, one EA lane does not need it yet. Revisit when adding second CEO-level actor or opening access to others.
* **COO Commons as control-plane policy engine:** Commons is scoped to deterministic shared assets in Phase 1. A policy engine that evaluates runtime decisions belongs in Phase 2+ if the pattern proves necessary. Expanding Commons into a decision-maker before Phase 1 proves basic dispatch reliability is an architectural risk.
* **Technical lease/lock for active substrate:** deferred to Phase 2. Phase 1 single-writer discipline is enforced by topology (standby is operationally inert) rather than by GitHub-level locking mechanism.

These are not rejections of the patterns — they are deferrals based on current scale. Each has a defined trigger for reconsideration.

---

## 10. Command schema specification

Command schema design is resolved as follows:

### 10.1 Schema A — CEO→COO command (what the CEO sends to initiate work)

| Field            | Type          | Required | Notes                              |
| ---------------- | ------------- | -------- | ---------------------------------- |
| `command_id`     | string (uuid) | yes      | CEO or system-generated            |
| `task_type`      | enum          | yes      | Defined in Commons schema registry |
| `inputs`         | object        | yes      | Task-type-specific payload         |
| `schema_version` | string        | yes      | Pinned at command time             |

### 10.2 Schema B — COO→EA dispatch (what the COO constructs after GitHub issue creation)

| Field            | Type          | Required | Notes                                           |
| ---------------- | ------------- | -------- | ----------------------------------------------- |
| `command_id`     | string (uuid) | yes      | Carried from originating CEO command            |
| `issue_id`       | integer       | yes      | GitHub issue number, COO-assigned               |
| `attempt_id`     | string        | yes      | COO-generated at each `→ dispatched` transition |
| `task_type`      | enum          | yes      | Carried from Schema A                           |
| `inputs`         | object        | yes      | Carried from Schema A                           |
| `schema_version` | string        | yes      | Pinned at dispatch time                         |

Schema A is the Commons-owned canonical CEO interface. Schema B is the Commons-owned dispatch envelope. Both are versioned in the Commons schema registry. Phase 3 NL-to-schema mapping translates natural language into Schema A. It does not touch Schema B.

---

## 11. Known gaps

The following issues are acknowledged but not resolved in this document. Each requires a separate decision before the relevant capability is operational.

### 11.1 Output semantic validation

Schema validation catches shape, not truth. Whether a well-formed EA result is semantically correct relative to task intent is a separate concern. Output validators are referenced in Section 7.1 but their location, ownership, and implementation are not defined. This gap has increasing urgency as phase complexity grows.

### 11.2 Idempotency post-Commons-restart

The Commons dedup log is not persisted across ingestion service restarts. Duplicate webhook delivery immediately after restart will pass the dedup check. Accepted for Phase 1; revisit if restart frequency is non-negligible.

### 11.3 EA identity and provenance

Schema validation catches shape, not origin. A well-formed result from an unexpected actor passes validation. Output semantic validators (Section 11.1) partially address this. Full EA identity model is deferred to hardening phase.

### 11.4 Primary substrate designation

Not decided in this document. Requires a Phase 1 readiness assessment covering stability, deployment complexity, and known failure modes for each candidate substrate.

---

## 12. Architectural posture

This document describes a **constrained control-plane prototype**, not a final target state. The intent is to prove:

1. Reliable dispatch from CEO command to EA execution
2. Reliable return path from EA result to CEO notification
3. Bounded COO discretion within defined authority limits
4. Mechanical detection of semantic drift before it propagates
5. Substrate replaceability at the deterministic interface level (judgment replaceability is a later and harder problem)

It is NOT yet intended to prove:

* Dependable long-horizon autonomy
* Robust decomposition of novel work
* Trustworthy planning
* Full substrate interchangeability including judgment parity

Those capabilities are phased in with explicit qualification gates, not assumed.

---

**END OF ARCHITECTURE v2.3c**

```
```
