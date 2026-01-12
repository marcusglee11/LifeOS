# ARCH — Future Build Automation Operating Model v0.1 (Draft)

**Status:** Draft (Architecture / Ideation)  
**In force:** No (non-binding; not a governance artefact)  
**Last updated:** 2026-01-03 (Australia/Sydney)  
**Audience:** CEO interface users; System architects; Future implementers  
**Intent:** Capture the target *operating model* for fully automated builds with governance gating, including role boundaries, packet taxonomy, ledger topology, convergence/termination, and escalation.

---

## 1. Purpose and scope

Define how a fully automated build should run end-to-end with:
- minimal CEO involvement (exception-only),
- schema-led packet exchange between specialised agents/endpoints,
- governance separation (Council as an independent domain),
- auditable, replayable trails via ledgers and evidence manifests,
- bounded loops with deterministic termination and escalation rules.

**Scope includes:** build lifecycle from approved intent → tasking → build/verify → council review cycles → integration/regression/E2E → release record → documentation stewardship.

---

## 2. Non-goals

- This document does not define implementation details, concrete schemas, storage engines, or UI/GUI design.
- This document does not establish governance authority or ratify policy.
- This document does not define every domain (e.g., finance, business ops) beyond ledger topology patterns.

---

## 3. System model and role boundaries

### 3.1 CEO interface principle
From the CEO perspective there is **one system interface** (the control plane). Internally, work is decomposed into specialised endpoint agents/services.

### 3.2 Logical roles (minimal set)
These roles are **logical**; they may be implemented as distinct processes/services later.

1) **COO / Concierge (Control Plane)**
- Primary interface with CEO.
- Routes work to endpoints.
- Enforces policy gates and escalation rules.
- Maintains the Executive Index Ledger (EIL) as the global state spine.

2) **Planner-Orchestrator (Control Plane function)**
- Decomposes approved intent into prioritised tasks.
- Issues task orders to endpoints.
- Tracks dependencies and readiness.
> May be co-located with the COO control plane as one logical agent, with tool-permission separation.

3) **Architect (Spec Owner)**
- Owns “done means…” and resolves spec/design ambiguity.
- Translates rulings into implementable constraints and fix pack requirements.
- Default sink for non-policy ambiguity and non-convergence.

4) **Builder (Construction Endpoint)**
- Executes builds/changes inside authorised constraints.
- Produces build outputs and evidence references.

5) **Verifier (Test/Analysis Endpoint)**
- Executes verification suites (unit/integration/regression/E2E), determinism checks, static analysis.
- Produces verification evidence and pass/fail classifications.

6) **Council (Governance Endpoint) — separate domain**
- Interprets policy/constitution constraints.
- Issues structured rulings and dispositions.
- Operates independently (ideally read-only access to review packets + evidence refs).

7) **CSO (Intent Proxy / Deadlock Reframer) — optional early, essential later**
- High-trust intent alignment arbiter.
- Does not override Council.
- Invoked only after **deadlock triggers**; default action is **reframing and re-dispatch**, not deciding.
- May hold bounded delegated authority (e.g., small spend, small-stakes external comms) under explicit caps and prohibitions (future).

---

## 4. High-level state machine (overview)

Example global states (EIL-owned):
- `CASE_OPENED`
- `AUTH_GRANTED`
- `READY_FOR_BUILD`
- `BUILDING`
- `READY_FOR_REVIEW`
- `FIX_REQUESTED`
- `READY_FOR_COUNCIL`
- `COUNCIL_FIX_REQUESTED`
- `COUNCIL_APPROVED`
- `INTEGRATING`
- `E2E_REGRESSION`
- `RELEASE_APPROVED`
- `ARCHIVED`
- `PAUSED_ESCALATION`

**Invariant:** Only the Executive Index Ledger (EIL) advances global state. Domain ledgers publish outcomes; the control plane records state transitions.

---

## 5. Packet taxonomy

### 5.1 Principle
Packets are **typed commitments**, not chat messages:
- schema-validated,
- signed,
- referencable by immutable IDs,
- replayable via referenced inputs/evidence.

### 5.2 Packet families (minimum viable set)
1) **Intent / Authorization**
- `INTENT_PROPOSAL`
- `AUTH_GRANTED` (decision record / approved intent envelope)

2) **Work decomposition**
- `WORKPLAN`
- `TASK_ORDER`

3) **Build execution**
- `BUILD_REQUEST`
- `BUILD_RESULT`

4) **Verification**
- `VERIFY_REQUEST`
- `VERIFY_RESULT`

5) **Review / Governance**
- `REVIEW_REQUEST` / `REVIEW_FINDINGS` (architect/peer review)
- `COUNCIL_REVIEW_REQUEST` / `COUNCIL_RULING` / `COUNCIL_DISPOSITION`

6) **Change instructions**
- `FIX_PACK` (authorises changes after findings/rulings)

7) **Integration / Release**
- `INTEGRATION_REQUEST` / `INTEGRATION_RESULT`
- `RELEASE_APPROVAL` / `RELEASE_RECORD`

8) **Stewardship**
- `DOC_STEWARD_REQUEST` / `DOC_STEWARD_RESULT`

### 5.3 Required common fields (all packets)
- `packet_id` (prefer content-addressed)
- `packet_type`, `schema_version`
- `issued_at`, `issuer_role`, `issuer_identity` (key id)
- `case_id` (global thread identifier)
- `authority_refs` (what approvals/decisions this operates under)
- `input_refs` (immutable refs: repo states, artefacts, prior packets)
- `constraints` (permissions/side-effects allowed; determinism envelope)
- `expected_outputs` (declared artefact classes + evidence requirements)
- `evidence_manifest_ref` (see below)
- `signature` (over canonical serialisation)

### 5.4 Evidence as first-class (by reference)
Packets should not embed large logs/diffs. Instead:
- `evidence_manifest` is a typed list of evidence objects (test logs, diff bundles, metrics, traces).
- Packets carry concise summaries + references; evidence blobs live in object stores.

---

## 6. Ledger topology (start with B: per-domain + executive index)

### 6.1 Structure
1) **Executive Index Ledger (EIL)**
- Global “spine” for cases, authorisations, dispatches, outcomes, state transitions, escalations.
- The only ledger required to answer: “What is happening now?”

2) **Domain Ledgers**
- `DL_BUILD` — build/verify/integration details + evidence refs
- `DL_GOV` — council review cycles, rulings, dispositions + evidence refs
- `DL_DOC` — documentation stewardship actions and reports
- (future) `DL_FIN`, `DL_BIZOPS`, etc.

3) **Object/Evidence Stores**
- Hold heavy evidence objects referenced by manifests.

### 6.2 Cross-ledger anchoring invariant
Every domain run must be anchored to EIL:
- Domain packets carry `case_id` + `eil_anchor_ref` (the EIL entry authorising/dispatching the run).
- EIL records outcomes with `domain_ledger_id` + `domain_entry_hash/packet_ref`.

**Invariant:** Domain ledgers cannot advance global state directly; they publish outcomes; EIL records transitions.

### 6.3 Governance separation (DL_GOV from day one)
- Council runs in `DL_GOV`.
- EIL governance gates advance only via recorded DL_GOV dispositions.
- Council ideally has read-only access to review packets and evidence refs, not direct repo access.

---

## 7. Convergence, termination, and bounded cycles

### 7.1 Anti-ping-pong measures
- **Batch rulings:** reviewers/council issue consolidated rulings per cycle.
- **Batch fix packs:** architect/design returns one fix pack mapping each item → change → evidence.

### 7.2 Bounded cycles
Each loop (build-review, council, verification) has:
- `max_cycles (N)`
- a required **monotonic progress signal** per cycle
- escalation triggers when bounds are violated

### 7.3 Monotonic progress signals (examples)
- reduced failing test count (or closure of specific failing IDs)
- reduced open council item count (or closure of specified item IDs)
- reduced schema conformance errors
- determinism checks improving (replay success/hashes stable)

### 7.4 Failure classification (required)
Non-convergence must be classified (to avoid “try again” loops):
- spec ambiguity
- conflicting constraints (policy vs design)
- tooling/runtime limitation
- flaky verification / harness instability
- scope creep / mis-slicing

---

## 8. Escalation policy

### 8.1 Levels and default routing
- **L0:** Auto-resolve within bounded cycles.
- **L1:** Internal escalation → Architect (spec/design ambiguity; routine non-convergence).
- **L1b:** Deadlock escalation → CSO (intent reframing; post-trigger only).
- **L2:** Governance escalation → Council (policy/authority conflicts).
- **L3:** CEO escalation → CEO (only when required by governance class or safety boundary).

### 8.2 Trigger taxonomy
- Non-convergence (cycle limit; no monotonic progress)
- Spec/intent ambiguity
- Policy/authority conflict
- Safety boundaries (money, external comms, security-sensitive operations)
- Tooling/runtime limitations

### 8.3 CEO escalation packet (standard payload)
Every CEO escalation must include:
- escalation class
- decision required (single sentence)
- up to 3 options with effects
- recommendation + rationale
- ledger refs only (EIL + domain refs)
- safe default if no response (pause affected case)

---

## 9. CSO deadlock protocol (post-trigger only)

### 9.1 Deadlock triggers (deterministic)
Examples:
- council cycles ≥ N with no reduction in open item count
- no monotonic progress for M cycles
- repeated re-litigation (same item IDs recur without new evidence types)
- cross-domain dependency loop (build ↔ council stalemate without a new admissible evidence path)

### 9.2 CSO outputs (ordered preference)
1) `CSO_REFRAME_DIRECTIVE` (default)
- narrow scope, clarify intent into acceptance criteria, repackage minimal decisive evidence, split into sub-cases
- includes `max_remaining_cycles` for retry

2) `CSO_ROUTING_CHANGE`
- redirect to correct authority (Architect vs Council vs Verifier/harness)

3) `CEO_ESCALATION_REQUIRED`
- only if reframing cannot stay within the authorised envelope

### 9.3 Guardrail
CSO may re-scope/reprioritise within envelope but must not relax acceptance thresholds or expand permissions without pre-authorised rules or CEO escalation.

---

## 10. Open questions / parameters (intentionally deferred)
- Defaults for cycle limits: `N` (cycles), `M` (no-progress cycles), `K` (post-reframe retry cycles)
- Delegation envelopes for CSO (caps, expiry, prohibited zones)
- Exact schema registry/versioning policy for packets
- Evidence store strategy (shared vs per-domain)
- Operational monitoring / observability requirements (alert thresholds)

---

## 11. Summary invariants (the “spine”)
1) **EIL is the global state spine.** Domains publish outcomes; EIL advances state.
2) **Council is separate (DL_GOV).** Governance gates advance only via DL_GOV dispositions recorded in EIL.
3) **Packets are typed commitments.** Signed, schema-led, replayable, evidence by reference.
4) **Fixes are traceable.** Fix packs must cite ruling item IDs and evidence refs.
5) **Loops are bounded.** Convergence enforced via monotonic progress signals and cycle limits.
6) **CSO intervenes only after deadlock triggers.** Default action is reframing and re-dispatch, not deciding.
7) **CEO involvement is exception-only.** Escalations must be minimal, options-bounded, and ledger-referenced.

---
