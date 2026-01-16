# ARCH — Builder North-Star Operating Model v0.5 (Draft)

**Status:** Draft (Architecture / Ideation)  
**In force:** No (non-binding; not a governance artefact)  
**Scope:** Target/evolving operating model for the **builder system** (build → verify → govern → integrate → steward)  
**Audience:** CEO interface users; future control-plane designers; endpoint implementers  
**Last updated:** 2026-01-03 (Australia/Sydney)  
**Lineage:** Derived from v0.4 after multi-model iteration; restructured to preserve the north-star and move validation/plan material to annexes.

---

## 0. Purpose and scope

This document defines the desired end-state and intermediate target model for how LifeOS executes builds autonomously with governance gating, auditability, and bounded escalation to the CEO.

**Covers**
- Role boundaries (control plane vs endpoints) and how they interact
- Packet taxonomy (schema-led contracts) and evidence handling
- Ledger topology (Executive Index Ledger + domain ledgers, including Council as a separate domain now)
- Convergence/termination and escalation policy
- Autonomy ladder (capability rungs) as the activation schedule for the machinery above

**Does not cover**
- Concrete runtime implementation, storage engines, or exact schema JSON/YAML
- Full governance protocol text (this doc is not authority)
- Product positioning / broader LifeOS mission statements beyond what is necessary to define the builder operating model

---

## 1. Core invariants (non-negotiables for the north-star)

1) **Single CEO surface:** From the CEO’s view, there is one interface (COO control plane). Internal complexity must be absorbed by the system.  
2) **Typed packets, not chat:** Inter-agent communication is via **schema-led packets** with explicit `authority_refs`, `input_refs`, and signed outputs.  
3) **Evidence by reference:** Packets carry **evidence manifests** (typed references), not embedded logs/diffs.  
4) **Ledgered operations:** The system is auditable by design via append-only ledgers, not ad hoc narrative.  
5) **EIL is the global spine:** Only the Executive Index Ledger (EIL) advances global case state. Domain ledgers publish outcomes; EIL records state transitions.  
6) **Council is separate now:** Governance runs in a dedicated domain ledger (DL_GOV). Governance gates advance only via recorded DL_GOV dispositions.  
7) **Bounded loops:** Build/review/council cycles are bounded with monotonic progress signals and deterministic deadlock triggers.  
8) **CEO by exception:** CEO involvement occurs only on explicit escalation triggers; escalations are bounded to ≤3 options and cite ledger refs.  
9) **Tool choice is an implementation detail:** Roles must not be named after tools (e.g., “OpenCode” is an endpoint implementation, not a role).  
10) **Complexity is debt:** Infrastructure is “earned” rung-by-rung; no premature federation unless it reduces CEO burden and improves auditability.

---

## 2. Roles and boundaries

### 2.1 Control plane vs endpoints

**Control plane** (COO surface)
- Conversational interface for intent capture and status presentation
- Routes work to endpoints
- Enforces constraints, gates, escalation policy
- Owns the EIL and the “global truth” of what is happening

**Endpoints** (specialised services / agents)
- Builder, Verifier, Council, Document Steward, etc.
- Each endpoint accepts a narrow set of packet types and returns typed results + evidence refs

### 2.2 Minimal logical roles (for builds)

1) **COO / Concierge (Control Plane)**  
   Routes, governs, records (EIL), escalates.

2) **Planner–Orchestrator (Control Plane function)**  
   Converts authorised intent into a prioritised workplan and task orders; schedules dispatch.

3) **Architect (Spec Owner / Acceptance Owner)**  
   Owns “done means…”, resolves spec ambiguity, translates rulings into implementable constraints and fix packs.

4) **Builder (Construction Endpoint)**  
   Applies changes under explicit authority; emits build results and artefact refs.

5) **Verifier (Test/Analysis Endpoint)**  
   Runs verification suites and determinism checks; emits verification results and evidence refs.

6) **Council (Governance Endpoint) — DL_GOV**  
   Issues structured rulings and dispositions; ideally operates read-only on review packets + evidence refs.

7) **CSO (Intent Proxy / Deadlock Reframer) — optional early, essential later**  
   Invoked only after deadlock triggers; default action is reframing and re-dispatch (not deciding).

### 2.3 Logical vs physical separation (deployment choice)

Default: roles are **logically distinct** (separate permission sets, separate packet contracts).  
Evolve to physical separation when it materially improves:
- security/blast radius (secrets, money, external comms)
- throughput (parallel build/test)
- context scarcity (domain-specific caches)
- reliability (fault isolation)

---

## 3. Ledger topology (start with per-domain ledgers + executive index)

### 3.1 Ledgers

**Executive Index Ledger (EIL)** — global spine
- `case_id` creation
- authority grants / approvals
- dispatches to domain ledgers (with `dispatch_id`)
- domain outcomes (refs only)
- global state transitions
- escalations and resolutions

**Domain ledgers** — detailed operational truth per domain
- **DL_BUILD:** build/verify/integration execution packets + evidence refs
- **DL_GOV:** council cycles, rulings, dispositions + evidence refs
- **DL_DOC:** doc stewardship requests/results + reports
- (future) DL_FIN, DL_BIZOPS, etc.

### 3.2 Cross-ledger anchoring invariant

Every domain run must be anchored to EIL via:
- shared `case_id`
- `eil_anchor_ref` (the EIL entry that authorised/started the run)
- domain root entry hash/packet ref

Every EIL outcome entry must reference:
- `domain_ledger_id`
- `domain_entry_hash` or `packet_ref`
- outcome classification (pass/fail/fix_required/escalate)

### 3.3 Why Council separation is mandatory now

- Maintains governance independence (no repo write access required)
- Enables clear governance gating: only DL_GOV dispositions advance governance gates in EIL
- Prevents “build loop” and “governance loop” from collapsing into one opaque loop

---

## 4. Packet taxonomy (north-star contracts)

### 4.1 Packet families (minimum viable set)

1) **Intent / Authority**
- `INTENT_PROPOSAL`
- `AUTH_GRANTED` (authority envelope, constraints, escalation rules)

2) **Planning / Tasking**
- `WORKPLAN`
- `TASK_ORDER`

3) **Build execution**
- `BUILD_REQUEST`
- `BUILD_RESULT`

4) **Verification**
- `VERIFY_REQUEST`
- `VERIFY_RESULT`

5) **Review / Governance**
- `REVIEW_REQUEST` / `REVIEW_FINDINGS` (architect/peer)
- `COUNCIL_REVIEW_REQUEST`
- `COUNCIL_RULING`
- `COUNCIL_DISPOSITION`

6) **Change instruction**
- `FIX_PACK` (the only post-finding/ruling change authorisation)

7) **Integration / Release**
- `INTEGRATION_REQUEST` / `INTEGRATION_RESULT`
- `RELEASE_APPROVAL` / `RELEASE_RECORD`

8) **Stewardship**
- `DOC_STEWARD_REQUEST` / `DOC_STEWARD_RESULT`

### 4.2 Required common fields (all packets)

- `packet_id` (prefer content-addressed)
- `packet_type`, `schema_version`
- `issued_at`, `issuer_role`, `issuer_identity`
- `case_id`
- `authority_refs` (what grant/decision authorises this)
- `input_refs` (immutable refs to artefacts, repo state, prior packets)
- `constraints` (permissions/side-effects allowed; determinism envelope)
- `expected_outputs` (declared artefact classes + evidence requirements)
- `evidence_manifest_ref`
- `signature` (canonical serialisation)

### 4.3 Evidence manifests (by reference)

Evidence is stored as typed objects and referenced from packets:
- `TEST_LOG`, `LINT_REPORT`, `DIFF_BUNDLE`, `METRICS`, `TRACE`, `ARTEFACT_BUNDLE`, etc.
- Packets contain summaries + refs, not bulk payloads.

---

## 5. End-to-end build lifecycle (case flow)

### 5.1 High-level flow (conceptual)

```
CEO → COO(Control Plane)
   → EIL: CASE_OPENED / AUTH_GRANTED
   → DL_BUILD: BUILD_REQUEST → BUILD_RESULT
   → DL_BUILD: VERIFY_REQUEST → VERIFY_RESULT
   → DL_GOV: COUNCIL_REVIEW_REQUEST → COUNCIL_RULING/DISPOSITION
   → (if fix) Architect → FIX_PACK → DL_BUILD rebuild/verify
   → EIL: STATE_ADVANCED → INTEGRATION → RELEASE_RECORD
   → DL_DOC: DOC_STEWARD_REQUEST → DOC_STEWARD_RESULT
```

### 5.2 Gate ownership

- **Architect gate:** acceptance criteria clarity (“done means…”) and fix pack authorisation
- **Verifier gate:** tests/determinism/regression evidence
- **Council gate:** policy compliance and disposition (DL_GOV)
- **COO gate:** global state advancement recorded in EIL

---

## 6. Convergence, termination, and deadlocks

### 6.1 Anti-ping-pong rules

- Council/review outputs are **batch rulings** per cycle (no drip-feed).
- Architect responses are **batch fix packs** mapping each item → change → evidence.

### 6.2 Bounded cycles and monotonic progress

Each loop defines:
- max cycles `N`
- a monotonic progress signal (must improve per cycle, or within `M` cycles)
- escalation triggers when bounds are violated

Progress signal examples:
- decreasing failing test count (or closure of specific failing IDs)
- decreasing open ruling item count (or closure of specific `item_id`s)
- decreasing schema conformance errors
- improving determinism checks (replay success / stable hashes)

### 6.3 Deadlock triggers (deterministic)

A deadlock trigger may fire when (examples):
- cycles ≥ `N` with no reduction in open items
- no monotonic progress for `M` cycles
- repeated re-litigation (same item IDs recur without new admissible evidence)
- cross-domain dependency loop (build ↔ council stalemate)

### 6.4 CSO intervention (post-trigger only)

When a deadlock trigger fires, CSO is invoked to **reframe and re-dispatch**, not to decide.

CSO outputs (ordered preference):
1) `CSO_REFRAME_DIRECTIVE` (narrow / split / clarify / repackage evidence) + remaining-cycle bounds
2) `CSO_ROUTING_CHANGE` (redirect to the correct authority: Architect vs Council vs Verifier)
3) `CEO_ESCALATION_REQUIRED` (only if outside authorised envelope)

---

## 7. Escalation policy (CEO by exception)

### 7.1 Levels

- **L0:** Auto-resolve within bounded cycles
- **L1:** Internal escalation → Architect (spec/design ambiguity; routine non-convergence)
- **L1b:** Deadlock escalation → CSO (post-trigger reframing)
- **L2:** Governance escalation → Council (policy/authority conflicts)
- **L3:** CEO escalation → CEO (safety boundaries or governance-required decisions)

### 7.2 CEO escalation packet standard (required)

Any CEO escalation must include:
- escalation class + why triggered
- decision required (single sentence)
- ≤3 options, with effects (not implementation detail)
- recommendation + rationale
- ledger refs (EIL + domain refs only)
- safe default if no response (pause affected case)

---

## 8. Autonomy ladder (capability rungs)

The ladder measures capability, not architectural sophistication. Each rung “earns” additional infrastructure only when it reduces CEO burden and improves auditability.

### Rung 0 — Manual orchestration
Human initiates and executes; AI responds. No durable ledgering beyond ad hoc notes.

### Rung 1 — Triggered autonomy (single task, single loop)
Agent executes a defined task when triggered (CI/cron/command). Outputs are reviewable artefacts.  
**Minimum machinery:** `BUILD_REQUEST/RESULT`, `VERIFY_REQUEST/RESULT`, evidence refs.

### Rung 2 — Supervised chains (multi-step workflow with checkpoints)
Multi-step workflows with explicit checkpoints; agent can run several steps autonomously but must satisfy gates before advancing.  
**Minimum machinery:** EIL case spine + dispatch/outcome recording; structured fix packs.

### Rung 3 — Delegated domains (domain ownership within constraints)
Agent owns a domain end-to-end within constraints; human involvement by exception.  
**Minimum machinery:** domain ledgers + cross-ledger anchoring; council gating for significant changes; bounded escalation.

### Rung 4 — Autonomous initiative (proposal → approval → execution)
Agent identifies tasks worth doing, proposes them, and executes after approval, within delegation envelopes.  
**Minimum machinery:** proposal packets + delegated authority grants + robust deadlock handling.

---

## 9. Security and safety boundaries (north-star posture)

This operating model assumes explicit constraints in `AUTH_GRANTED`:
- no spend / no external comms / no secrets changes unless explicitly delegated
- branch-only writes and controlled merge/release gates (implementation choice, but the authority must exist)
- least privilege credentials and blast-radius partitioning (especially as endpoints become physical services)

(Concrete delegation envelopes and enforcement live in governance/risk artefacts, not here.)

---

## 10. Glossary (minimal)

- **Artefact:** A durable output (code, doc, report, bundle) referenced immutably.
- **Packet:** A typed, schema-led message with signatures, refs, and constraints.
- **Invariant:** A rule that must hold across implementations and rungs.
- **EIL:** Executive Index Ledger (global spine for cases, gates, escalation).
- **Domain ledger:** Append-only ledger for a specific operational domain (build, gov, docs).
- **Disposition:** Council outcome that advances/blocks a governance gate.

---

# Annexes (supporting material; not part of the north-star core)

## Annex A — Validation record (from v0.4 “Validated Foundation”)
This annex preserves proof-of-concept notes and should be maintained in an audit-grade “Validation Record” format:
- environment topology (self-hosted vs hosted runner)
- exact invocations
- immutable evidence refs (logs, commit SHAs, run IDs)
- reproducibility notes

## Annex B — Implementation roadmap (from v0.4 “Implementation Plan”)
Timeboxes are non-durable; preserve as a working plan, but prefer capability exit criteria:
- validate the loop
- raise the stakes (PR workflow, notifications)
- supervised chains
- expand scope

## Annex C — Risk register (from v0.4)
Keep operational and governance risks here, tied to mitigations and triggers.

## Annex D — Migration notes (from v0.4 Appendix B “Migration from Antigravity”)
Tool migrations and endpoint selection belong here. Roles remain stable; implementations swap.

## Annex E — Document history
Version log and major structural changes.
