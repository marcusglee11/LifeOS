# LifeOS Authority Audit — Pro-Level Launch Prompt

Use this only after `docs/audit/LIFEOS_AUTHORITY_AUDIT_PREFLIGHT_PROMPT.md` returns `SUFFICIENT` or `PARTIAL` with no blocking context gaps.

```text
You are acting as a formal architecture auditor for my LifeOS / COO Operating Console project.

Source context:
Use the connected GitHub repo as the source of truth.

Audit target:
- Repo: marcusglee11/LifeOS
- Branch: main
- Commit SHA: d94e51afd1c076393a32d7d7e94e893a33e82185
- Manifest: docs/audit/LIFEOS_AUTHORITY_AUDIT_MANIFEST.md

Before auditing, inspect the manifest and confirm context sufficiency.

Mission:
Derive the smallest coherent authority, approval, evidence, delegation, pushback, and execution-state model that can govern the whole system without ambiguity, circular authority, silent bypasses, or false agency.

This is not a literature review.
Do not perform broad web research.
Do not give generic governance or agent-framework advice.
Use only the connected repo context and the manifest.
Do not rely on prior memory.
Where artefacts conflict, identify the conflict explicitly.
Where required artefacts are missing, mark the issue as UNKNOWN rather than inventing a rule.

If categories A–F in the manifest are not sufficiently provided, stop and return:

CONTEXT INSUFFICIENT FOR 10/10 AUDIT

Then list the missing artefacts required to make the audit valid.

If representative examples are weak or missing, proceed only if A–F are sufficient, and mark the practical-example coverage as weak.

Project context:
I am building LifeOS / COO Operating Console: a governance-aware COO/Chief-of-Staff interface that converts intent into bounded, auditable, fail-closed actions. The system uses deterministic execution loops, StepGate approval semantics, typed workflows, receipt-based evidence, state transitions, agent delegation, and multi-agent review.

Major streams:

1. LifeOS / COO Operating Console
- Governance-aware COO/Chief-of-Staff interface
- Deterministic execution loops
- StepGate approval semantics
- Receipts-first CI/CD
- Fail-closed governance
- Typed workflows such as execution_order.v1, task_proposal.v1, escalation_packet.v1
- Auditability, evidence gates, deterministic state transitions

2. Council Runtime / Governance Architecture
- Multi-agent review protocol
- Policy packs
- FSM orchestration
- Independence constraints
- Schema enforcement
- Contradiction ledgers
- Canonical hashes / RFC 8785-style signing
- Proportional tiering T0–T3

3. OpenClaw / Hermes / Agent Runtime Operations
- COO/ingress/router/status rendering
- External execution harnesses
- Agent authority
- Proxy approval
- Pushback rights
- Bus/communication architecture
- Low-friction ops via Windows Terminal, WSL2, GCP, GitHub, Codex/Claude/Copilot agents

Core audit question:
What is the single canonical model of authority, approval, delegation, pushback, evidence, and execution-state advancement that should govern this whole system?

Audit tasks:

1. Authority taxonomy

Define the precise difference between:
- user intent
- CEO approval
- delegated/proxy approval
- COO direction
- agent recommendation
- agent execution order
- reviewer finding
- reviewer veto
- escalation
- pushback
- advisory comment
- runtime status report
- evidence receipt

For each term, specify:
- whether it is binding
- who or what may issue it
- what evidence is required
- what state transition, if any, it can authorize

2. Authority hierarchy

Determine who or what can bind whom:
- user / CEO
- COO layer
- Council reviewers
- OpenClaw
- Hermes
- execution agents
- coding agents
- CI/runtime validators
- schemas/policy packs
- receipts and state machines

Identify where authority is:
- human
- delegated
- mechanical
- advisory
- evidentiary
- invalid

3. Approval semantics

Define exactly when human approval is required, when it can be proxied, when it cannot be proxied, and what evidence must exist for approval to be valid.

Resolve:
- Can COO approve on behalf of the CEO?
- Can OpenClaw or Hermes relay an approval?
- Can an agent infer approval from prior context?
- Can a Council recommendation become binding?
- Can a validator block a human-approved action?
- Can an agent push back against a CEO-approved task?
- What makes a StepGate transition valid?
- What makes approval invalid, stale, ambiguous, or non-transferable?

4. Pushback rights

Define when an agent or reviewer:
- must comply
- may recommend changes
- must push back
- must refuse
- must escalate
- may block execution
- may only record a warning

Separate:
- safety pushback
- governance pushback
- correctness pushback
- scope pushback
- preference pushback
- cost/efficiency pushback

5. Evidence and receipt semantics

Define the minimum evidence required for:
- task creation
- triage
- dispatch
- execution start
- review return
- fixes requested
- approval
- closure
- rejection
- escalation
- deployment
- post-run reconciliation

Distinguish:
- claim
- observation
- receipt
- proof
- validator result
- audit record

6. State-machine implications

Audit the work item lifecycle and StepGate model for:
- missing transitions
- overloaded states
- ambiguous states
- invalid shortcuts
- review-return gaps
- closure-evidence weakness
- dispatch/in-progress ambiguity
- blocked/awaiting-agent ambiguity
- bypass paths

Propose a corrected minimal transition model.

7. Contradiction ledger

Produce a ledger of contradictions, tensions, or unresolved ambiguities across the artefacts.

For each item include:
- ID
- source artefacts / sections
- conflicting claims
- why it matters
- severity: BLOCKING / MAJOR / MINOR
- proposed resolution
- invariant or schema/test that would prevent recurrence

8. Canonical invariant set

Derive the smallest set of non-negotiable invariants needed to make the system fail-closed and auditable.

Each invariant must be:
- short
- testable
- enforceable by schema, state machine, CI, receipt check, or explicit human gate
- mapped to the failure mode it prevents

9. Minimal schema amendments

Recommend minimal amendments to:
- execution_order.v1
- task_proposal.v1
- escalation_packet.v1
- review packet structures
- receipt structures
- lifecycle state records
- approval records

Do not over-design.
Only include fields required to remove ambiguity or enforce invariants.

10. Acceptance tests / proof cases

Design concrete proof cases for:
- valid human approval
- invalid inferred approval
- proxy approval attempt
- relayed approval
- stale approval
- ambiguous approval
- reviewer requests fixes
- reviewer veto
- agent pushback against unsafe task
- agent pushback against merely suboptimal task
- CI validator blocks an approved task
- closure without sufficient receipt
- OpenClaw/Hermes authority conflict
- StepGate advancement without explicit “go”

Output format:

A. Context sufficiency verdict
- CONTEXT SUFFICIENT FOR 10/10 AUDIT
- CONTEXT PARTIAL — AUDIT VALID BUT LIMITED
- CONTEXT INSUFFICIENT FOR 10/10 AUDIT

B. Executive verdict
- Is the current authority/evidence model coherent?
- If not, what is the main architectural defect?

C. Canonical authority model
- taxonomy
- hierarchy
- binding/non-binding distinction
- invalid authority forms

D. Approval and proxy-approval model
- allowed cases
- prohibited cases
- required evidence
- invalid approval patterns

E. Pushback and escalation model
- comply
- warn
- recommend
- push back
- refuse
- escalate
- block

F. Evidence and receipt model
- claim vs observation vs receipt vs proof
- minimum evidence by lifecycle stage
- evidence insufficient for closure

G. Corrected lifecycle/state-machine model
- states
- transitions
- guards
- required fields
- terminal states
- prohibited shortcuts

H. Contradiction ledger
Table columns:
- ID
- source artefact / section
- conflict
- severity
- why it matters
- proposed fix
- invariant/test

I. Minimal invariant set
For each invariant:
- invariant ID
- statement
- enforcement mechanism
- failure mode prevented

J. Minimal schema amendments
For each amendment:
- target artefact/schema
- exact field/enum/rule change
- reason
- enforcement mechanism

K. Acceptance test suite
For each test:
- test name
- scenario
- expected result
- enforcement layer

L. Implementation sequence
- surgical amendment order
- what to change first
- what to defer
- what not to build yet

Constraints:
Be blunt.

Prefer a smaller coherent model over a comprehensive but unwieldy model.

Do not preserve existing terminology if it causes ambiguity; rename it.

Do not invent authority where no artefact supports it.

Do not let convenience override fail-closed governance.

Any proposed rule must be enforceable or explicitly marked as advisory.

Any unresolved issue must be listed as an open decision, not buried in prose.

When citing evidence, cite artefact names and section headings or line references where available.

The success condition is not “more architecture.”
The success condition is a smaller, stricter, enforceable authority and evidence model that prevents ambiguity, bypass, false agency, and invalid state advancement.
```
