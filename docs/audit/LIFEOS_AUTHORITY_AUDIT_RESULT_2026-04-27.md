# LifeOS Authority Audit Result - 2026-04-27

Repo: `marcusglee11/LifeOS`
Branch: `main`
Operative source baseline: post-PR #42 main at merge SHA `c2e78dab7f1e7eb0968c8edc177d6a9d047ee918`
Requested output path: `docs/audit/LIFEOS_AUTHORITY_AUDIT_RESULT_2026-04-27.md`

Important baseline note: the in-repo audit prompt and manifest still name the older pinned SHA `d94e51afd1c076393a32d7d7e94e893a33e82185`. The user instruction for this audit explicitly supersedes that metadata with PR #42 merge SHA `c2e78dab7f1e7eb0968c8edc177d6a9d047ee918`. This audit treats the old SHA references in `docs/audit/LIFEOS_AUTHORITY_AUDIT_PRO_PROMPT.md` and `docs/audit/LIFEOS_AUTHORITY_AUDIT_MANIFEST.md` as stale launch metadata, not as the operative target.

Evidence style: citations below use repository paths and line/section references observed at the operative tree or PR #42 commit view. Where exact rendered line numbers were available, they are included. Draft/proposal-only documents are used only as pressure sources unless ratified by canonical docs.

---

## A. Context sufficiency verdict

**CONTEXT PARTIAL - AUDIT VALID BUT LIMITED**

Categories A-F in the audit manifest are sufficiently populated for a valid authority audit, and the required canonical/draft distinction is clear enough to proceed. The limitation is not that the core authority artefacts are missing; the limitation is practical example depth and repo-write access. Category G representative examples should be treated as weak coverage unless PR bodies, review-packet bodies, merged commits, and final main-line content are reconciled in a follow-up evidence pass. The main audit is still valid because the authoritative decisions are present in the final main-line documents and ADR/control surfaces.

Key context checks:

- PR #42 is present as commit `c2e78da`, titled `docs: prepare Pro authority audit context (#42)`, with parent `d94e51a` and three audit files added. Ref: GitHub commit view for `c2e78dab7f1e7eb0968c8edc177d6a9d047ee918`, lines 172-190.
- The manifest itself says it is a launch surface and not a canonical architecture decision. Ref: `docs/audit/LIFEOS_AUTHORITY_AUDIT_MANIFEST.md`, manifest diff lines 248-260.
- The manifest's canonicality priority is explicit: Constitution/governance rulings, Architecture Source of Truth/ADRs, COO Operating Contract, operational architecture, current protocols, schemas/tests, trackers, fresh wiki, then drafts/proposals. Draft/proposal documents lose to canonical docs. Ref: manifest diff lines 319-387.
- Categories A-F are populated. Ref: manifest diff lines 400-696.
- The manifest itself warns that Category G has representative examples and requires checking agreement between PR bodies, merged commits, and current main-line files. Ref: manifest diff lines 703-754 and 886-902.

Audit limitation recorded as open evidence issue, not as a blocker:

- **OE-001:** Category G examples are representative, not exhaustive. Acceptance of this audit does not certify that every historical PR body agrees with current final main content. Resolution: add a separate `authority_example_reconciliation` evidence packet if historical PR lineage becomes enforcement-critical.

---

## B. Executive verdict

**The current authority/evidence model is directionally coherent but not yet mechanically coherent.**

The core prose model has converged around the right invariants:

- CEO authority is supreme, but operational action must be captured into canonical receipts.
- Exactly one active COO substrate may write operational state.
- Standby COOs, Hermes/OpenClaw peer agents, Drive/Workspace material, wiki pages, comments, reviewers, and execution agents are not independent sources of operational authority.
- GitHub operational state is the canonical approval receipt and work-order state store.
- Approval is source-channel agnostic but storage-bound.
- Ambiguity fails closed.

The main architectural defect is that **canonical prose is ahead of enforceable state and schema mechanics**. The docs say the right things, but the runtime-facing schemas/parser/tracker surfaces do not yet carry enough authority, approval, lifecycle, and receipt fields to prevent invalid dispatch, inferred approval, stale approval, reviewer-result-as-closure, or peer/standby bypass.

Concrete defect pattern:

1. `COO_Operating_Contract_v1.0.md` defines a strong approval tuple and sole-writer rule. Ref: `docs/01_governance/COO_Operating_Contract_v1.0.md`, sections 7-9, observed lines 5-21.
2. ADR-001 through ADR-004 ratify active/standby, inter-agent directionality, human approval capture, and Drive/Workspace non-canonicality. Ref: `docs/10_meta/architecture_decisions/INDEX.md`, observed lines 0-11.
3. Target architecture defines a work-order FSM and fail-closed state semantics. Ref: `docs/00_foundations/LifeOS_Target_Architecture_v2.3c.md`, observed lines 25-56.
4. But `artifacts/coo/schemas.md` and `runtime/orchestration/coo/parser.py` do not yet encode the approval tuple, active COO identity, authority path, state preconditions, validator requirements, or closure receipt rules into `execution_order.v1` / `task_proposal.v1` / `escalation_packet.v1`. Ref: `artifacts/coo/schemas.md`, observed lines 0-12; `runtime/orchestration/coo/parser.py`, observed lines 1-15.
5. `LIFEOS_STATE.md` and `BACKLOG.md` still appear stale against the ratified ADR/source-of-truth state: the normalization decisions appear open in the trackers while Source of Truth / ADR / changelog surfaces mark them resolved. Ref: `docs/11_admin/LIFEOS_STATE.md`, observed lines 0-12; `docs/11_admin/BACKLOG.md`, observed line 0; `docs/10_meta/ARCHITECTURE_CHANGELOG.md`, observed lines 0-17.

Blunt conclusion: **LifeOS has a good normative authority design, but it is not yet an authority system. It becomes an authority system only when the approval receipt, lifecycle state, execution order, and parser/CI gates make invalid authority unrepresentable or non-actionable.**

---

## C. Canonical authority model

### C1. Authority taxonomy

| Term | Binding? | May issue | Required evidence | Authorized transition/effect |
| --- | --- | --- | --- | --- |
| User intent | Not directly binding unless the user is the CEO and intent is converted into a valid command/approval/proposal | CEO/user | Source event reference, captured summary, channel, timestamp | Intake/triage only; cannot dispatch or mutate canonical operational state by itself |
| CEO approval | Normatively binding, operationally actionable only after canonical receipt capture | CEO | Approval receipt tuple: `proposal_id`, `proposal_fingerprint`, `rendered_summary_hash`, `approval_action`, `captured_from_channel`, `captured_at`, `captured_by`, plus `policy_version`, `phase`, `work_order_id`, `issue_id` where applicable | Moves an eligible item to `ready`, authorizes active COO path, or authorizes exception/override if explicitly scoped |
| Delegated/proxy approval | Binding only if explicit CEO delegation exists and is captured | Explicitly delegated operator or active COO only within delegated envelope | Delegation receipt plus approval receipt; must identify delegated scope and expiry | Same effect as scoped approval, never global CEO authority |
| COO direction | Binding to workers only when issued by active COO path, inside phase/policy envelope | Active COO substrate or explicitly CEO-authorized operator through active COO path | Execution order/work order, active COO id, authority path, scope, state precondition, approval ref if required | Dispatches or redirects work; may mutate canonical operational state if sole-writer guard passes |
| Agent recommendation | Advisory | Hermes, OpenClaw, execution agents, reviewers, coding agents | Comment/proposal/result packet, actor identity, timestamp, source artefacts | No direct transition; can trigger triage, hold, or escalation |
| Agent execution order | Binding task envelope only if issued by active COO path | Active COO to execution/coding agent | `execution_order.v1` with work_order_id, attempt_id, scope_paths, constraints, policy_version, state precondition, approval_ref as needed | `ready -> dispatched` or retry/redirect transitions when guards pass |
| Reviewer finding | Advisory unless attached to a protocol gate that gives it blocking effect | Council reviewer, QA/reviewer role, validator wrapper | Review packet, finding id, severity, evidence refs, scope | May move to `review_returned`, `fixes_requested`, `needs_decision`, or `blocked` depending on gate |
| Reviewer veto/reject | Blocking where protocol says seat rejection/veto blocks synthesis/closure | Reviewer or Council seat under applicable protocol | Seat output with verdict, reason, evidence refs, protocol version | Blocks closure/approval path until CEO/council resolution; cannot by itself approve an alternate action |
| Escalation | Binding halt/decision request | Any actor detecting boundary/safety/governance ambiguity; mandatory in some cases | Escalation packet with trigger, authority issue type, options, evidence refs | Moves to `needs_decision` or `blocked`; prevents further action until resolved |
| Pushback | Mandatory or permitted resistance to instruction depending on risk | Any actor inside its role | Pushback record with reason, rule, severity, proposed safe path | May warn, recommend, refuse, block, or escalate; no direct execution unless resolved |
| Advisory comment | Non-binding | Any advisory channel or peer agent | Comment/proposal source ref | Intake only; no operational transition |
| Runtime status report | Evidentiary observation, not authority | Runtime, worker, OpenClaw gateway, CI, agent | Status event, run id, attempt id, timestamp | Updates evidence/logging; may trigger timeout/reconcile/escalation; cannot approve or close |
| Evidence receipt | Evidentiary, not authority | Active COO, runtime, CI, validator, operator | Receipt id, actor, event type, hashes/refs, timestamp, canonical store ref | Satisfies guards or blocks closure if missing; cannot authorize by itself unless it is an approval receipt from valid authority |
| Validator result | Mechanical gate | CI, schema validator, policy check, semantic validator | Validator name/version, input hash, output, pass/fail, timestamp | Can allow, hold, block, or escalate; cannot create human authority |
| Audit record | Historical proof trail | Active COO/runtime/CI/operator | Immutable/canonical log or GitHub issue/PR/comment ref | Supports review/reconciliation; does not authorize action by itself |

### C2. Authority hierarchy

Smallest coherent hierarchy:

1. **CEO / Constitution / governance rulings.** CEO is supreme in authority. However, operational action must still be captured into canonical state/receipts before it affects the system. This prevents invisible approval and preserves auditability. Ref: `COO_Operating_Contract_v1.0.md` section 9; `docs/INDEX.md` authority chain; `ARCHITECTURE_SOURCE_OF_TRUTH.md` truth hierarchy.
2. **Ratified architecture and governance contracts.** Architecture Source of Truth, ratified ADRs, COO Operating Contract, canonical operational architecture, current protocols. Ref: manifest canonicality priority lines 319-387; `ARCHITECTURE_SOURCE_OF_TRUTH.md` lines 4-10.
3. **Active COO path.** The active COO substrate is the sole writer of operational state. It is the only operational authority path for work-order mutation except explicitly CEO-authorized operator actions captured into the canonical store. Ref: `COO_Operating_Contract_v1.0.md` section 7; ADR-001.
4. **Mechanical gates.** Schemas, validators, state machines, CI, StepGate, policy packs. These do not outrank CEO authority, but they may prevent operational progression because approval authorizes only valid action subject to policy, phase, sole-writer, and validators. Ref: `COO_Operating_Contract_v1.0.md` section 9.5; Target Architecture state machine.
5. **Council/reviewer roles.** Council/reviewers produce findings, rejects, contradiction ledgers, and gate decisions according to protocol. A reviewer/council may block where the protocol gives it blocking force, but it cannot create CEO approval or override the CEO. Ref: `Council_Protocol_v1.3.md`, observed lines 0-33.
6. **Execution agents and coding agents.** EAs/coding agents execute scoped work and produce PRs/commits/comments/evidence. They do not mutate the canonical state block, approve work, or alter authority. Ref: Target Architecture observed lines 8-10.
7. **OpenClaw/Hermes/Drive/Workspace/wiki/advisory channels.** These are substrates, relays, drafting spaces, or derived/advisory layers. They are not canonical authority. Ref: ADR-002, ADR-004; OpenClaw integration constraints; wiki schema lines 244-274.

### C3. Binding vs non-binding distinction

Binding requires all of the following:

- Valid issuer for the claimed authority class.
- Canonical store capture or valid operational receipt.
- Scope/phase/policy envelope.
- State precondition match.
- Required approvals and validators present.
- Sole-writer path preserved.

Non-binding by default:

- Recommendations, comments, draft docs, proposal-only docs, Drive docs, Workspace docs, chat text, wiki pages, local notes, runtime observations, raw status events, PR bodies unless reflected in final main-line canonical docs, labels-only signals, Project v2 projections.

### C4. Invalid authority forms

Invalid authority forms must be mechanically rejected:

- Inferred approval from prior context.
- Approval without proposal fingerprint or rendered summary hash.
- Approval captured outside GitHub operational state without later canonical receipt.
- Standby COO mutation.
- OpenClaw/Hermes peer direction treated as command.
- Drive/Workspace document treated as approval or operational state.
- Wiki page treated as canonical source.
- Reviewer recommendation treated as approval.
- Validator pass treated as human approval.
- Labels-only state transition.
- Direct worker state-block mutation.
- Action using stale approval after proposal/material summary drift.
- COO approving on behalf of CEO without explicit delegated approval receipt.
- StepGate progression without explicit current-step `go`.

---

## D. Approval and proxy-approval model

### D1. Allowed cases

1. **Direct CEO approval captured by active COO.**
   - Source can be direct active COO interaction, ChatGPT, CLI, Telegram, GitHub issue/PR comment by CEO, or other channel listed in the contract.
   - Operational effect begins only after active COO or explicitly CEO-authorized operator captures the durable approval receipt in the canonical GitHub operational state.
   - Ref: `COO_Operating_Contract_v1.0.md` section 9.2-9.6.

2. **Direct CEO approval relayed through standby COO or agent.**
   - Valid as a source event only.
   - Standby/agent may relay or prepare capture, but may not mutate state.
   - Active COO must capture receipt before action.
   - Ref: `COO_Operating_Contract_v1.0.md` sections 7 and 9; ADR-001/ADR-003.

3. **Scoped delegated approval.**
   - Valid only when CEO explicitly delegates approval authority, scope, expiry, and subject class.
   - The delegation must itself be captured as a receipt.
   - Delegated approval cannot exceed scope or imply general CEO authority.

4. **StepGate approval for current discrete step.**
   - Valid only with explicit `go` for the current step.
   - It does not authorize future steps, different artefacts, hidden paths, global mutation, or unstated approvals.
   - Ref: `stepgate_protocol_v1.0.md`, observed lines 0-2.

5. **Council/reviewer approval where protocol gives gate effect.**
   - A council verdict can satisfy a council gate only within the protocol's specified role.
   - It cannot replace CEO approval where CEO approval is required.

### D2. Prohibited cases

- COO approval on behalf of CEO by default.
- OpenClaw/Hermes approval as independent authority.
- Agent-inferred approval from silence, prior context, apparent satisfaction, or repeated past pattern.
- Treating a PR body, changelog note, Drive doc, wiki page, local note, or status report as approval.
- Treating approval as transferable across proposal fingerprints, summary hashes, issue ids, work orders, phases, or materially changed scope.
- Treating a valid approval as permission to bypass validators, sole-writer, phase envelope, or state-machine guards.

### D3. Required approval evidence

Minimum approval receipt fields:

```yaml
approval_receipt.v1:
  receipt_id: string
  proposal_id: string
  proposal_fingerprint: string
  rendered_summary_hash: string
  approval_action: approve | reject | waive | override | go | hold
  captured_from_channel: string
  captured_at: datetime
  captured_by: string
  captured_by_role: active_coo | ceo_authorized_operator
  source_event_ref: string
  policy_version: string
  phase: string
  work_order_id: string?
  issue_id: string?
  authority_scope: string
  expires_at: datetime?
  material_change_policy: reapproval_required
  canonical_store_ref: string
```

### D4. Invalid, stale, ambiguous, or non-transferable approval

Approval is invalid if:

- Issuer cannot be identified as CEO or delegated operator.
- Approval action is ambiguous (`looks good`, `fine`, `ok` without binding proposal/action context).
- Proposal fingerprint or rendered summary hash is missing.
- Captured receipt is not in canonical GitHub operational state.
- Captured by an actor not permitted to capture operational approval.
- Approval is older than a material change in scope, summary, policy, phase, work_order_id, issue_id, or affected path.
- It attempts to approve a prohibited operation or bypass sole-writer/validator constraints.

Approval is stale if any bound element changes:

- `proposal_id`
- `proposal_fingerprint`
- `rendered_summary_hash`
- policy version
- phase
- work_order_id / issue_id
- protected path set
- risk class / approval reason
- material implementation plan

Approval is non-transferable across actors, paths, phases, tasks, or issue ids unless the approval receipt explicitly says so.

### D5. Specific resolutions requested by the prompt

| Question | Resolution |
| --- | --- |
| Can COO approve on behalf of CEO? | No by default. COO may make bounded operational decisions inside delegated phase envelope; that is not CEO approval. Explicit CEO delegation is required for proxy approval. |
| Can OpenClaw or Hermes relay an approval? | Yes as a source relay, not as authority. Active COO or CEO-authorized operator must capture canonical receipt before action. |
| Can an agent infer approval from prior context? | No. Inferred approval is invalid. |
| Can a Council recommendation become binding? | Only when a canonical protocol gate gives it binding/blocking effect. Otherwise advisory. |
| Can a validator block a human-approved action? | Yes operationally. It cannot overrule CEO authority, but it can prevent invalid progression and force escalation because approval is subject to policy, phase, state, sole-writer, and validators. |
| Can an agent push back against a CEO-approved task? | Yes, and must do so for safety, governance, authority, phase, approval, writer, or correctness violations. Pushback escalates; it does not silently veto CEO authority. |
| What makes a StepGate transition valid? | Explicit current-step `go`, exact current step, no inferred future permission, no hidden changed path/content/scope. |
| What makes approval invalid/stale/ambiguous/non-transferable? | Missing valid issuer, receipt, hash/fingerprint, scope, canonical capture, authorized capturer, or unchanged bound elements. |

---

## E. Pushback and escalation model

### E1. Decision ladder

| Outcome | When used | Actor behavior | State effect |
| --- | --- | --- | --- |
| Comply | Instruction is in envelope, approved if required, state preconditions match, validators pass, no material ambiguity | Execute exactly within scope | Normal transition |
| Warn | Low-risk preference/cost/efficiency concern, but action is valid | Record warning and continue if appropriate | No hold unless policy requires |
| Recommend changes | Action is valid but suboptimal or simpler safer path exists | Recommend alternative; do not block unless rejected alternative creates risk | Usually no hold |
| Push back | Safety/governance/correctness/scope/approval ambiguity or likely invalid state advancement | State explicit reason, cite invariant, propose safe path | Hold or transition to `needs_decision` depending severity |
| Refuse | Requested action requires bypass, unauthorized mutation, invalid approval, prohibited path, hidden state change, unsafe execution, or validator bypass | Do not execute; emit refusal receipt | `blocked` or `needs_decision` |
| Escalate | Decision owner required or ambiguity cannot be resolved locally | Create escalation packet with options and evidence | `needs_decision` |
| Block | Protocol/validator/reviewer veto gives blocking force | Stop progression until override/fix/decision receipt | `blocked`, `fixes_requested`, or `needs_decision` |

### E2. Pushback classes

- **Safety pushback:** mandatory on harmful, dangerous, privacy/security-sensitive, or unsafe operational instruction.
- **Governance pushback:** mandatory on authority/phase/approval/writer/canonicality ambiguity, protected path changes, council-gate bypass, or StepGate violation.
- **Correctness pushback:** mandatory if instruction is demonstrably wrong in a way that would corrupt evidence/state, misrepresent result, or close without proof.
- **Scope pushback:** mandatory if instruction exceeds work_order scope, protected paths, execution envelope, or approved proposal fingerprint.
- **Preference pushback:** advisory only unless it changes risk/authority/scope.
- **Cost/efficiency pushback:** advisory unless the cost/risk threshold requires approval or violates a budget envelope.

### E3. Mandatory escalation triggers

- Authority source unclear.
- Active COO identity unclear.
- Approval required but missing, stale, ambiguous, or captured by invalid actor.
- Standby/peer/agent attempts to mutate canonical state.
- Draft/proposal/wiki/Drive content conflicts with canonical docs.
- Reviewer veto/reject under blocking protocol.
- Validator/schema failure on a proposed transition.
- State precondition mismatch.
- Late or malformed result would otherwise mutate state.
- Human asks for a shortcut around evidence/receipt/StepGate.

---

## F. Evidence and receipt model

### F1. Terms

| Term | Definition | Authority effect |
| --- | --- | --- |
| Claim | Unverified assertion by actor or doc | None |
| Observation | Event or status seen by runtime/agent/human | May trigger review/reconcile; no authority |
| Receipt | Structured durable record of a state-affecting event | Can satisfy a guard if valid |
| Proof | Receipt plus reproducible or independently verifiable evidence | Supports closure/audit |
| Validator result | Mechanical pass/fail/warn with versioned input/output | Can allow/block/hold/escalate |
| Audit record | Durable chronology of decisions, evidence, and transitions | Historical accountability; no independent authority |

### F2. Minimum evidence by lifecycle stage

| Stage | Minimum evidence required | Insufficient evidence examples |
| --- | --- | --- |
| Task creation | source_event_ref, captured summary, task/proposal id, actor/channel, timestamp, risk/stakes, initial scope | chat-only intent; unscoped request; label-only issue |
| Triage | classification, owner/envelope, approval_required flag/reason, policy_version, phase, state_from/to receipt | implicit owner; undocumented risk decision |
| Dispatch | active_coo_id, execution_order id, work_order_id/issue_id, attempt_id, state precondition, scope_paths, constraints, approval_ref if required, dispatch receipt | comment saying "sent"; no attempt id; no active COO id |
| Execution start | workflow_run_id or worker_run_id, attempt_id, start timestamp, runner/agent identity, environment/sandbox info | status text without run id |
| Review return | result packet, PR/commit/artifact refs, tests, schema pass, semantic validator result, reviewer packet if applicable | worker says "done"; PR exists but no validation |
| Fixes requested | finding ids, blocking/nonblocking status, evidence refs, required changes, responsible actor, state transition receipt | informal comment not tied to state |
| Approval | `approval_receipt.v1` complete tuple, source event, canonical store ref, captured_by valid actor | "approved" in local notes; ambiguous emoji/comment |
| Closure | completion receipt, final state, validators pass, PR/commit/test evidence, unresolved issues list, state hash, closure actor | status `succeeded` without closure receipt |
| Rejection | reject/veto reason, issuer/role, evidence refs, protocol/version, remediation path | silent close; informal dislike |
| Escalation | trigger, authority issue type, decision owner, options/effects, evidence refs | vague "needs input" |
| Deployment | approved commit, environment, deploy actor/path, test receipts, rollback/compensation plan/receipt | deploy note with no commit/environment |
| Post-run reconciliation | old/new state, detected conflict, source-of-truth priority applied, correction receipt, actor | overwriting tracker silently |

### F3. Evidence insufficient for closure

Closure is invalid if any of these are missing:

- Final lifecycle state and closure receipt.
- Proof that required validators/gates passed or were explicitly overridden by valid CEO receipt.
- PR/commit/artifact/test refs for build work.
- Approval receipt for protected or approval-required work.
- Review disposition for reviewer-requested changes.
- Reconciliation receipt for projection/tracker conflicts.
- Open-decision list for unresolved issues.

`Succeeded` is not the same as `closed`. A worker can succeed technically while the work item remains unclosed because review, validation, approval, reconciliation, or evidence is incomplete.

---

## G. Corrected lifecycle/state-machine model

### G1. Problem in current lifecycle

The current target architecture has useful work-order states (`backlog`, `ready`, `dispatched`, `running`, `succeeded`, `failed`, `blocked`, `needs_decision`, `superseded`, `timed_out`) and correctly treats `late_result` as an event classification rather than a state. Ref: Target Architecture, observed lines 51-56.

However, it under-specifies the review-return and closure gap. It allows people to read `running -> succeeded` as if worker success equals accepted/closed work. The manifest itself flags possible review-return and closure-evidence gaps as OD-002. Ref: manifest open decisions lines 826-839.

### G2. Corrected minimal states

Use a single canonical lifecycle vocabulary:

| State | Meaning | Mutator |
| --- | --- | --- |
| `intake` | raw intent/proposal observed; not yet operational | active COO or intake adapter, no work mutation |
| `triaged` | typed and classified; approval/risk/envelope decided | active COO |
| `awaiting_approval` | human/council/StepGate approval required | active COO |
| `ready` | required approvals/inputs present; dispatchable | active COO |
| `dispatched` | execution order issued; attempt id exists | active COO |
| `running` | worker/runtime acknowledged start | runtime/active COO receipt path |
| `review_returned` | worker result received; not yet accepted | active COO/reviewer path |
| `under_validation` | mechanical/semantic validation in progress | validator path |
| `fixes_requested` | review/validator requires changes | active COO/reviewer gate |
| `blocked` | cannot proceed due external dependency or hard gate | active COO/gate |
| `needs_decision` | CEO/council/owner decision required | active COO/escalation path |
| `timed_out` | deadline elapsed; late results do not mutate | active COO/runtime timeout |
| `superseded` | replaced by another work item/attempt | active COO |
| `withdrawn` | intentionally removed before completion | active COO/CEO approval as required |
| `rejected` | rejected/vetoed and not proceeding | active COO/gate |
| `failed` | terminal technical failure after permitted retries | active COO/runtime |
| `closed` | terminal accepted completion with closure receipt | active COO |

### G3. Allowed transition skeleton

| From | To | Guard |
| --- | --- | --- |
| `intake` | `triaged` | typed proposal/task exists; source event captured |
| `triaged` | `awaiting_approval` | approval/council/StepGate required |
| `triaged` | `ready` | no approval required; scope/envelope valid |
| `awaiting_approval` | `ready` | valid approval receipt and unchanged bound elements |
| `awaiting_approval` | `blocked` | approval rejected/expired |
| `ready` | `dispatched` | active COO, execution order, state precondition, attempt_id, scope, approval_ref if required |
| `dispatched` | `running` | worker/run acknowledgement with attempt_id |
| `dispatched` | `review_returned` | fast result before running, same attempt_id |
| `running` | `review_returned` | result packet received, same attempt_id |
| `review_returned` | `under_validation` | result schema passes enough to validate |
| `review_returned` | `needs_decision` | malformed/ambiguous result |
| `under_validation` | `fixes_requested` | reviewer/validator requires changes |
| `under_validation` | `ready` | nonterminal changes accepted but more dispatch required |
| `under_validation` | `closed` | all required validators/reviews/evidence pass and closure receipt emitted |
| `fixes_requested` | `ready` | fix plan valid and approved if needed |
| `blocked` | `ready` | unblock receipt and guards pass |
| `needs_decision` | `ready` | decision receipt resolves issue |
| `needs_decision` | `blocked` | decision says hold/deny |
| `timed_out` | `ready` | CEO/active COO retry approval receipt where required |
| `timed_out` | `failed` | retry exhausted or decision denies retry |
| any nonterminal | `superseded` | supersession receipt references replacement |
| any nonterminal | `withdrawn` | valid withdrawal receipt |

### G4. Required lifecycle fields

```yaml
lifecycle_state.v1:
  work_order_id: string
  issue_id: string?
  state: string
  previous_state: string?
  state_version: integer
  state_updated_at: datetime
  state_updated_by: string
  active_coo_id: string
  phase: string
  policy_version: string
  approval_ref: string?
  execution_order_ref: string?
  attempt_id: string?
  workflow_run_id: string?
  reviewer_packet_ref: string?
  validator_result_refs: [string]
  closure_receipt_ref: string?
  blocked_reason: string?
  needs_decision_owner: string?
  state_hash: string
```

### G5. Terminal states

Terminal for operational execution:

- `closed`
- `failed`
- `rejected`
- `withdrawn`
- `superseded`

`Succeeded` should be renamed or demoted to `worker_succeeded` / `result_succeeded` event classification. If retained as a state, it must not be terminal closure.

### G6. Prohibited shortcuts

- `intake -> dispatched`
- `approval -> mutation` without active COO receipt path
- `running -> closed` without review/validator/closure receipt
- `review_returned -> closed` without `under_validation`
- `timed_out -> running` from late result
- `blocked -> dispatched` without unblock receipt
- `needs_decision -> ready` without decision receipt
- standby COO mutation
- labels-only state transition
- Project v2 projection treated as source-of-truth
- Drive/wiki/advisory proposal promoted to operation without canonical capture

---

## H. Contradiction ledger

| ID | Source artefact / section | Conflict | Severity | Why it matters | Proposed fix | Invariant/test |
| --- | --- | --- | --- | --- | --- | --- |
| C-001 | Audit prompt/manifest target vs user instruction/PR #42 | Prompt and manifest name `d94e51...`; user requires post-PR #42 SHA `c2e78d...` | MINOR | Audit baseline ambiguity can invalidate evidence refs | Update audit prompt/manifest target commit or add amendment note referencing PR #42 | CANON-002 baseline pin test |
| C-002 | `LIFEOS_STATE.md`/`BACKLOG.md` vs ADR/changelog/source-of-truth | Trackers still show normalization decisions open while ADR/changelog mark A1-A5 resolved | MAJOR | Canonical trackers become stale and can mislead active COO | Add reconciliation receipt and update trackers to match ratified ADRs | RECON-001 tracker reconciliation test |
| C-003 | Council Protocol v1.3 vs Invocation/Procedural/Context Pack references | Current protocol is v1.3, but binding/procedural docs reference v1.1/v1.2 and Intent Routing v1.0/1.1 WIP | MAJOR | Council authority can be applied under wrong version | Update all council binding/version references or explicitly demote stale runbooks | COUNCIL-002 protocol version consistency test |
| C-004 | Target Architecture COO role vs COO Runtime Spec | Target Architecture makes COO bounded operational decision-maker; Runtime Spec says COO runtime cannot judge/decide/interpret/validate/approve/authorize | MAJOR | Actor boundary is unclear; agents may over- or under-exercise authority | Split `active_coo_control_plane` from `mechanical_runtime_executor`; make runtime subordinate | AUTH-006 role-boundary test |
| C-005 | Work-order FSM vs Runtime Core mission lifecycle vs Build Loop mission journal | Different lifecycle state vocabularies coexist | MAJOR | State transitions can be interpreted inconsistently; closure can be false | Ratify `lifecycle_state.v1` as single operational vocabulary; map old states | STATE-001 FSM consistency test |
| C-006 | COO Operating Contract approval tuple vs schemas/parser | Contract requires approval tuple; schemas/parser do not encode or enforce it | BLOCKING | Invalid/inferred/stale approval remains representable | Add `approval_receipt.v1`; require `approval_ref` in protected/approval-required execution orders | APPROVAL-002 approval receipt schema test |
| C-007 | ADR-001/002 sole-writer and peer direction vs runtime schemas | Active COO/standby/Hermes/OpenClaw authority is prose-only, not machine-checkable | MAJOR | Peer/standby bypass cannot be mechanically rejected | Add `active_coo_id`, `authority_path`, `issuer_role`, and peer advisory checks | AUTH-002 sole-writer enforcement test |
| C-008 | G-CBS status draft vs Council Protocol dependency | G-CBS says draft/CT-2 required, while Council Protocol treats G-CBS closure bundle as gating | MAJOR | Closure requirements may rely on unratified standard | Ratify/list G-CBS or remove binding dependency until ratified | GATE-003 ratified-dependency test |
| C-009 | DAP path/status/Gate 3 universality vs current workflows | DAP claims canonical placement/status and mandatory Gate 3 for artefacts; path/status references appear inconsistent with actual repo/protocol usage | MINOR | Artefact creation may be over-blocked or unclear | Normalize DAP path/status and define exceptions for audit/result artefacts | ART-001 artefact path/status test |
| C-010 | Build Loop Architecture status vs manifest/docs index | Build Loop doc appears draft/status-mixed while manifest says canonical per docs index | MAJOR | Autonomous loop semantics may be over-trusted | Add canonicality header or demote to draft in manifest/index | CANON-003 canonicality header test |
| C-011 | Proposal-only advisory lifecycle vs current need for receipts | Multi-agent communication draft has useful lifecycle/receipt semantics but is non-canonical | MINOR | Useful semantics may be accidentally treated as binding or ignored | Promote only minimal receipt/lifecycle parts through ADR or schema PR | CANON-001 proposal nonauthority test |
| C-012 | Wiki freshness/authority | Wiki schema says derived pages must be fresh/non-authoritative; some wiki pages have source commit maxima older than PR #42 | MINOR | Wiki may inject stale context | Treat wiki as navigation only unless freshness lint passes | WIKI-001 freshness/nonauthority test |
| C-013 | Runtime sandbox/no-network specs vs live OpenClaw ops | Runtime core says sandbox/no network/no unsandboxed fallback; OpenClaw/live gateway docs and state imply local operational gateway behavior | MAJOR | Runtime safety envelope ambiguous | Separate `execution sandbox` from `control gateway`; require env receipt per run | EXEC-001 environment envelope test |
| C-014 | CEO supreme vs `CEO does not mutate state directly` | Target Architecture says CEO does not directly mutate canonical operational state; approval contract permits CEO source comments | MINOR | Could be read as narrowing CEO authority | Clarify: CEO comments are source events; canonical state-block mutation still goes through active COO/operator receipt | AUTH-001 CEO/receipt distinction test |
| C-015 | Project Planning Protocol authority label | Protocol cites `Gemini System Protocol` as authority, which is not in the manifest hierarchy | MINOR | External authority surface may appear to outrank canonical docs | Rebase authority header to LifeOS Constitution/governance hierarchy or mark historical | CANON-004 external authority test |
| C-016 | Closure/evidence gap | Current states allow `succeeded` to be read as terminal success | BLOCKING | False closure and unreviewed work can pass as complete | Add `review_returned`, `under_validation`, and `closed` distinction | STATE-002 result-not-closure test |

---

## I. Minimal invariant set

| Invariant ID | Statement | Enforcement mechanism | Failure mode prevented |
| --- | --- | --- | --- |
| AUTH-001 | CEO authority is supreme, but operational effect requires canonical receipt capture. | Approval receipt schema + state transition guard | Invisible approval; unauditable action |
| AUTH-002 | Exactly one active COO substrate may mutate operational state. | Active COO registry + state writer guard | Split brain; standby mutation |
| AUTH-003 | Standby COOs and advisory agents may observe/relay/prepare but not mutate canonical operational state. | Role permission checks | Bypass through standby/advisory path |
| AUTH-004 | Hermes/OpenClaw peer direction is advisory unless reissued through active COO path or explicitly CEO-stamped and captured. | Authority path field + parser/CI guard | Peer agent command confusion |
| AUTH-005 | Draft/proposal/wiki/Drive/Workspace/local notes never bind operational state without canonical capture. | Canonicality classifier + receipt guard | Non-canonical source bypass |
| AUTH-006 | Mechanical runtime executors cannot create governance authority. | Role boundary schema + tests | Runtime overreach |
| APPROVAL-001 | Approval may never be inferred from silence, prior context, successful execution, or comment sentiment. | Approval required field + ambiguity fail-closed validator | Inferred approval |
| APPROVAL-002 | Approval-required work must reference a complete `approval_receipt.v1`. | Schema/CI validator | Missing approval tuple |
| APPROVAL-003 | Approval is stale if any bound proposal/scope/hash/policy/phase/work-order element changes. | Fingerprint/hash comparison | Approval transfer/drift |
| APPROVAL-004 | Proxy approval requires explicit delegation receipt. | Delegation receipt check | COO/agent impersonating CEO authority |
| GATE-001 | StepGate advances only on explicit `go` for the current step. | StepGate parser + exact current-step state | Future-step permission leak |
| STATE-001 | State transitions must match the canonical FSM and state precondition. | Lifecycle FSM validator | Invalid shortcuts |
| STATE-002 | Worker result/success is not closure. Closure requires closure receipt and validators/reviews. | Lifecycle state model + closure gate | False closure |
| STATE-003 | Late or malformed results cannot mutate success/closure state. | Attempt/run id and timeout guard | Late result corruption |
| STATE-004 | Labels and Project projections are derived; issue body/state block/receipts win. | Reconciliation validator | Projection-as-source error |
| EVID-001 | Every state-changing operation emits a durable receipt with actor, timestamp, refs, hashes, and state_from/to. | Receipt schema + CI | Untraceable mutation |
| EVID-002 | Terminal closure requires evidence bundle: approval refs if needed, PR/commit/test refs, validator results, closure receipt. | Closure validator | Premature close |
| VALID-001 | Validators may hold/block operational progression even after approval; failures escalate rather than bypass. | Validator gate + escalation route | Approved invalid action |
| PROV-001 | Dispatch/execution/review must bind `work_order_id`, `attempt_id`, and `workflow_run_id` where applicable. | Parser + receipt validator | Attempt confusion/idempotency failure |
| COUNCIL-001 | Council/reviewer reject or veto blocks only where current protocol says so; otherwise reviewer output is advisory. | Protocol versioned gate evaluator | Reviewer overreach or ignored veto |
| COUNCIL-002 | Council binding docs must reference the current ratified protocol version. | Doc lint/CI | Stale protocol authority |
| PUSH-001 | Pushback is mandatory on authority, phase, approval, writer, safety, governance, or correctness ambiguity. | Escalation packet trigger validator | Silent unsafe compliance |
| RECON-001 | Canonical tracker conflicts must be resolved by source-of-truth priority and recorded with reconciliation receipt. | Reconciliation job/test | Stale canonical trackers |
| CHANGE-001 | Architecture-affecting PRs must update Source of Truth/changelog/ADRs or declare no impact. | PR checklist/CI | Architecture drift |
| CANON-001 | Non-canonical sources cannot satisfy canonical authority guards. | Source classification field | Proposal/draft bypass |
| CANON-002 | Audit/run baselines must use a single explicit commit SHA. | Audit preflight check | Mixed baseline evidence |

---

## J. Minimal schema amendments

Do not build a large policy engine yet. Add only fields needed to make invalid authority non-actionable.

### J1. New schema: `approval_receipt.v1`

Target: new schema under `artifacts/coo/schemas.md` and parser/CI implementation.

Exact addition:

```yaml
approval_receipt.v1:
  required:
    - receipt_id
    - proposal_id
    - proposal_fingerprint
    - rendered_summary_hash
    - approval_action
    - captured_from_channel
    - captured_at
    - captured_by
    - captured_by_role
    - source_event_ref
    - policy_version
    - phase
    - authority_scope
    - canonical_store_ref
  optional:
    - work_order_id
    - issue_id
    - expires_at
    - delegated_authority_ref
    - override_reason
  rules:
    - captured_by_role in [active_coo, ceo_authorized_operator]
    - approval_action in [approve, reject, waive, override, go, hold]
    - material_change_policy defaults to reapproval_required
```

Reason: Implements COO Contract section 9 and ADR-003 as enforceable data.

Enforcement: parser rejects approval-required state transitions without valid receipt.

### J2. Amend `task_proposal.v1`

Add:

```yaml
proposal_id: string
proposal_fingerprint: string
rendered_summary_hash: string
source_event_ref: string
source_channel: string
risk_class: low | medium | high | protected | governance
requires_approval: boolean
approval_required_reason: string?
policy_version: string
phase: string
protected_paths: [string]
canonicality_class: canonical | derived | proposal | draft | stale | archive | external
```

Reason: Approval must bind to a concrete proposal and rendered summary; canonicality must be explicit.

Enforcement: proposal validator computes/compares fingerprint/hash and flags stale approvals.

### J3. Amend `execution_order.v1`

Add:

```yaml
work_order_id: string
issue_id: string?
attempt_id: string
issued_by: string
issued_by_role: active_coo | ceo_authorized_operator
authority_path: active_coo | ceo_authorized_operator
active_coo_id: string
phase: string
policy_version: string
state_precondition:
  required_state: ready
  state_hash: string?
approval_ref: string?
scope_paths: [string]
protected_paths: [string]
validators_required: [string]
receipt_refs: [string]
idempotency_key: string
```

Rules:

- `approval_ref` required when `requires_approval == true`, protected paths present, retry/redirect requires CEO approval in current phase, or governance policy requires it.
- `issued_by_role` cannot be standby, peer_agent, reviewer, execution_agent, Drive, wiki, or workspace.
- `idempotency_key = issue_id + attempt_id + workflow_run_id` when workflow_run_id exists.

Reason: Makes sole-writer, phase, approval, and state-precondition enforceable.

### J4. Amend `escalation_packet.v1`

Add:

```yaml
escalation_id: string
trigger: authority_unclear | approval_missing | approval_stale | writer_conflict | validator_failed | reviewer_veto | safety | governance | scope | timeout | malformed_result | tracker_conflict
authority_issue_type: human | delegated | mechanical | advisory | evidentiary | invalid
blocking_state: needs_decision | blocked | fixes_requested
required_decision_owner: CEO | active_COO | Council | CSO | runtime_owner
options:
  - option_id: string
    label: string
    effect_on_state: string
    required_receipts: [string]
evidence_refs: [string]
expires_at: datetime?
```

Reason: Escalation should not be vague; it must name the authority problem and decision owner.

### J5. Amend review packet structures

Add required fields:

```yaml
review_packet.v1:
  protocol_version: string
  reviewer_role: string
  verdict: accept | request_fixes | reject | veto | advisory
  binding_effect: advisory | blocking | ceo_decision_required
  evidence_refs: [string]
  findings:
    - finding_id: string
      severity: blocking | major | minor | advisory
      source_ref: string
      required_fix: string?
  complexity_budget_result: pass | fail | not_applicable
  validator_results: [string]
  scope: string
```

Reason: Distinguishes reviewer opinion from binding gate effects.

### J6. Amend receipt structures

Add generic receipt envelope:

```yaml
receipt.v1:
  receipt_id: string
  event_type: string
  actor: string
  actor_role: string
  authority_class: human | delegated | mechanical | advisory | evidentiary | invalid
  canonical_store_ref: string
  input_hash: string?
  output_hash: string?
  refs: [string]
  state_from: string?
  state_to: string?
  guard_results: [string]
  created_at: datetime
```

Reason: Every state-affecting operation needs the same audit spine.

### J7. Add `lifecycle_state.v1`

Use the fields defined in section G4.

Reason: Current state vocabularies diverge. A single lifecycle schema is the cheapest fix.

### J8. Parser/rule changes

- `parse_execution_order` must reject missing `active_coo_id`, `attempt_id`, `state_precondition`, `policy_version`, and required `approval_ref`.
- Parser must classify source canonicality and reject non-canonical sources as authority.
- Parser must compare proposal fingerprint/hash against approval receipt.
- Parser must refuse `standby`, `peer_agent`, `reviewer`, `execution_agent`, `wiki`, `drive`, `workspace`, `project_projection`, or `comment_only` authority paths.
- Parser must reject terminal closure unless `closure_receipt_ref` and validator results exist.

---

## K. Acceptance test suite

| Test name | Scenario | Expected result | Enforcement layer |
| --- | --- | --- | --- |
| valid_human_approval_captured | CEO approves proposal P with matching fingerprint/hash; active COO captures receipt; dispatch order references receipt | `awaiting_approval -> ready -> dispatched` allowed | approval_receipt schema + FSM guard |
| invalid_inferred_approval | Agent tries to dispatch based on prior discussion or silence | Rejected; escalation `approval_missing` | parser/approval guard |
| proxy_approval_without_delegation | COO marks CEO-approved without delegation receipt | Rejected; `approval_missing` or `invalid_proxy` | approval/delegation guard |
| relayed_approval_via_standby | Standby observes CEO approval and tries to mutate state | Mutation rejected; standby may create relay packet; active COO must capture | sole-writer guard |
| stale_approval_after_hash_change | Proposal content changes after approval receipt | Dispatch rejected until new approval receipt | hash/fingerprint comparison |
| ambiguous_approval_comment | CEO says "looks good" without bound proposal/action | Not actionable; ask/capture clarification | approval ambiguity validator |
| reviewer_requests_fixes | Reviewer returns blocking fixes | State becomes `fixes_requested`, not `closed` | review packet gate + FSM |
| reviewer_veto | Council seat emits protocol-valid veto/reject | Block and escalate to CEO/council path; cannot synthesize approval | council gate evaluator |
| unsafe_task_pushback | CEO-approved task conflicts with safety/governance invariant | Agent refuses/escalates; no execution until resolved | pushback/escalation guard |
| suboptimal_task_warning | Task valid but inefficient | Warning recorded; execution may proceed if no blocking rule | warning receipt |
| validator_blocks_approved_task | Approval receipt valid but schema/CI fails | State `needs_decision` or `blocked`; no closure | validator gate |
| closure_without_receipt | Worker says done; no closure receipt/validator evidence | Closure rejected; state `review_returned` or `under_validation` | closure validator |
| openclaw_hermes_authority_conflict | Hermes directs OpenClaw or standby to mutate issue | Direction treated advisory; active COO path required | authority_path guard |
| stepgate_without_go | Step advanced on implication or non-exact phrase | Rejected; remain current step | StepGate parser |
| late_result_after_timeout | Worker returns result after `timed_out` | Logged as late result; no success/closure transition | attempt/timeout guard |
| malformed_result | Result payload cannot validate schema | `needs_decision`; no transition to success | parser/FSM |
| label_only_transition | Label changed to done without state receipt | Reconciler restores/flags conflict; no closure | tracker reconciliation |
| project_projection_conflict | Project status differs from issue state block | Issue state block wins; reconciliation receipt emitted | canonical source priority |
| tracker_stale_after_adr | BACKLOG says decision open while ADR says resolved | CI/reconcile job fails or opens correction packet | source-of-truth consistency test |
| drive_doc_as_approval | Drive doc contains approval-like text | Non-actionable until captured into GitHub receipt | canonicality guard |
| wiki_claim_as_authority | Wiki page claims current truth inconsistent with docs | Docs win; wiki flagged stale/conflict | wiki lint/canonicality guard |
| council_version_mismatch | Invocation binding references old Council Protocol | CI fails protocol-version consistency | doc lint |
| active_coo_split_brain | Two substrates attempt state mutation | Second writer rejected; switchover receipt required | active COO registry |
| closure_after_worker_success_only | Worker result is `succeeded` but no review/validation | State remains `review_returned` or `under_validation`; no close | lifecycle FSM |

---

## L. Implementation sequence

### L1. Surgical amendment order

1. **Reconcile canonical trackers first.**
   - Update `docs/11_admin/LIFEOS_STATE.md` and `docs/11_admin/BACKLOG.md` so they agree with ADR-001 through ADR-004, Architecture Source of Truth, and Architecture Changelog.
   - Emit a reconciliation receipt.
   - Why first: stale canonical trackers undermine every operational decision.

2. **Normalize audit baseline metadata.**
   - Amend `docs/audit/LIFEOS_AUTHORITY_AUDIT_MANIFEST.md` and `docs/audit/LIFEOS_AUTHORITY_AUDIT_PRO_PROMPT.md` or add an audit note saying PR #42 moved the operative baseline to `c2e78d...`.
   - Why: prevents future mixed-SHA audits.

3. **Fix Council version/canonicality references.**
   - Update Council Invocation Binding, AI Council Procedural Spec, Council Context Pack Schema, and Intent Routing references to current ratified versions or explicitly mark them subordinate/draft.
   - Why: council/reviewer blocking authority cannot depend on stale protocol references.

4. **Add `approval_receipt.v1` and enforce it.**
   - Implement schema, parser validation, and minimal CI tests.
   - Why: this is the highest leverage enforcement gap.

5. **Amend `execution_order.v1`, `task_proposal.v1`, and `escalation_packet.v1`.**
   - Add only fields in section J.
   - Why: authority path, active COO id, state precondition, approval ref, and attempt id are currently not enforceable enough.

6. **Ratify `lifecycle_state.v1`.**
   - Add `review_returned`, `under_validation`, `fixes_requested`, and `closed` distinction.
   - Add FSM tests for prohibited shortcuts.
   - Why: prevents result-as-closure and late/malformed result corruption.

7. **Mechanize active/standby and OpenClaw/Hermes directionality.**
   - Add active COO registry or config, authority_path checks, and tests for standby/peer mutation attempts.
   - Why: ADR-001/002 are prose-only until this is enforced.

8. **Resolve G-CBS canonicality.**
   - Either promote G-CBS through required governance process and list it in the authoritative index, or remove binding references that depend on it.
   - Why: closure evidence cannot depend on a draft standard.

9. **Add tracker/source-of-truth reconciliation CI.**
   - Source-of-truth/ADR/changelog vs LIFEOS_STATE/BACKLOG consistency check.
   - Why: stops future stale canonical trackers.

10. **Only then consider promoting advisory lifecycle draft semantics.**
   - Extract minimal receipt/lifecycle ideas from the Multi-Agent Communication Architecture proposal if still needed.
   - Promote by ADR/schema PR, not by informal adoption.

### L2. What to defer

- Full policy engine.
- New multi-agent bus or Drive/Workspace ingress.
- Elaborate CSO/council automation beyond version/canonicality repair.
- Semantic validator sophistication beyond minimal closure and authority gates.
- General identity/provenance framework beyond fields needed for active COO, issuer role, attempt id, and receipt actor.
- Productization and vendor/tool comparison.

### L3. What not to build yet

- Do not build Drive polling or Drive-as-approval flows.
- Do not build new Hermes/OpenClaw peer command semantics.
- Do not let wiki pages drive operational decisions.
- Do not add more lifecycle names until `lifecycle_state.v1` is ratified and tested.
- Do not treat `succeeded` as closure.
- Do not implement convenience shortcuts around StepGate, approval receipts, or validators.
- Do not preserve terminology that hides authority class. Rename ambiguous terms to authority-specific terms: `CEO approval`, `delegated approval`, `COO direction`, `advisory recommendation`, `validator block`, `evidence receipt`, `closure receipt`.

---

## Open decisions

| ID | Decision | Owner | Required to unblock |
| --- | --- | --- | --- |
| OD-AUDIT-001 | Should Category G PR bodies/review packets be reconciled into an evidence packet? | Active COO | Practical example certification |
| OD-AUDIT-002 | Should `succeeded` be removed as a state or retained only as worker result classification? | Active COO / runtime owner | Lifecycle schema amendment |
| OD-AUDIT-003 | Should G-CBS be ratified or demoted from binding closure dependency? | CEO / Council if invoked | Closure gate certainty |
| OD-AUDIT-004 | Which substrate is the active COO registry source? | Active COO / runtime owner | Machine-checkable sole-writer enforcement |
| OD-AUDIT-005 | Who is authorized as `ceo_authorized_operator` besides active COO, if anyone? | CEO | Proxy/capture enforcement |
| OD-AUDIT-006 | How should Council Protocol v1.3 be propagated into older council runbooks/prompts? | Active COO / governance maintainer | Reviewer authority consistency |

---

## Final audit posture

Current LifeOS authority architecture should be treated as **ratified in principle, partially enforced in practice**.

The smallest coherent model is:

1. CEO is supreme.
2. Operational authority requires canonical capture.
3. Active COO is the sole writer.
4. Everyone else is advisory, evidentiary, delegated only by explicit receipt, or mechanically blocking only under protocol.
5. Approval is not transferable and not inferable.
6. Worker success is not closure.
7. Validators block invalid progression, they do not create authority.
8. Every state change needs a receipt.
9. Non-canonical surfaces can inform but never bind.
10. Ambiguity fails closed into escalation.

This is already supported by the best canonical prose. The next required step is not more architecture. It is schema/parser/FSM hardening plus tracker reconciliation.
