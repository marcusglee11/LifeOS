LifeOS Alignment Layer v1.0

Consolidation Packet for LifeOS v1.1, GPTCOO Project Builder v0.9, and Antigravity Implementation Packet v0.9.7
Canonical as of: 2025-11-27

0. Purpose and Authority

This document defines the alignment layer connecting:

LifeOS v1.1 Core Specification (constitutional, supreme authority)

GPTCOO v1.1 Project Builder Specification v0.9 (Patched) (module-level behavioural spec)

Antigravity Implementation Packet v0.9.7 (engineering execution guide)

This packet establishes the hierarchical relationship, subordination rules, scope boundaries, and required textual amendments to each downstream document to ensure full consistency with LifeOS v1.1.

All inconsistencies and governance leakages described herein are resolved by the amendments in Sections 3–5.

LifeOS v1.1 remains the constitution. All other documents derive their authority from it, not parallel to it.

1. Hierarchy Model (Canonical)

The following hierarchy is mandatory and non-negotiable:

1. LifeOS v1.1 – Constitution (Supreme Authority)

Defines:

Governance model (CEO, Council, Chair, Reviewers).

Determinism.

Energy governance.

Spec supremacy.

Safe Mode, Reconciliation Mode.

Ambiguity resolution (no silent assumption filling).

Routing & escalation rules.

Freeze Protocol.

Canonical role boundaries.

2. GPTCOO Project Builder Spec v0.9 – Module Spec (Subordinate)

Defines:

Behaviour of the Project Builder mission type.

Task FSM, repair loop, planner, QA, snapshot, context injection.

Sandbox contract for PB missions.

Tokenizer determinism.

Budgeting/repair-budget semantics.

The PB spec does not define:

Governance.

Council rules.

Role authority.

Constitutional invariants.

Global determinism requirements (it implements LifeOS invariants).

3. Antigravity Implementation Packet v0.9.7 – Engineering Guide (Subordinate to Both)

Defines:

Code structure.

Module layout.

Test suite requirements.

Engineering patterns (“BEGIN IMMEDIATE”, path checks).

Developer workflow (branching, PR rules).

The Implementation Packet does not define:

Governance rules.

Specification authority.

Reviewer authority.

The meaning of MUST/SHOULD beyond engineering execution.

2. Global Alignment Invariants

These invariants must hold across all documents:

2.1 Spec Supremacy

LifeOS v1.1 overrides all clauses in PB Spec and Implementation Packet in case of conflict.

2.2 No Governance Leakage

Execution-layer documents must not define roles, privileges, approval rules, or governance workflows.

2.3 Determinism as Constitutional

PB Spec and Implementation Packet determinism rules are module-level implementations of the LifeOS determinism invariant. They are not standalone determinism authorities.

2.4 Ambiguity → Escalation

LifeOS forbids silent assumption resolution.
PB and Implementation Packet must explicitly escalate ambiguous/underspecified cases through the LifeOS governance path.

2.5 Freeze Protocol Applies Universally

Any external HTTP/tooling step referenced in PB or Antigravity inherits Freeze Protocol from LifeOS.

2.6 Role Boundaries

CEO: Final authority.

Council: Governance reviews and verdicts.

COO Runtime: Deterministic execution only.

PB Spec + Implementation Packet: Do not introduce new roles.

3. Required Amendments — Project Builder Spec v0.9 (Patched)

This section provides exact textual amendments to bring the Project Builder spec into full alignment.

3.1 Add Mandatory Preamble at Top of PB Spec

Insert at line 1:

LifeOS Subordination Clause
This Project Builder Specification is subordinate to LifeOS v1.1.
All governance, determinism, ambiguity-handling, and authority rules in LifeOS v1.1 supersede this specification.
This document defines only module-level behaviour for Project Builder missions executed by the COO Runtime.
No clause herein grants governance authority, modifies LifeOS governance, or overrides constitutional invariants.

3.2 Clarify Role Boundaries

Replace any sentence implying the COO “decides”, “approves”, “rejects”, or “determines” outcomes with language indicating:

The COO enforces constraints mechanically.

All governance decisions originate from CEO/Council.

Example replacement:

Replace:
“COO rejects the plan if...”

With:
“The COO Runtime mechanically enforces plan constraints defined by LifeOS and this Module Spec. Violations cause deterministic routing to CEO via QUESTION messages.”

3.3 Add Ambiguity Escalation Clause

Insert in validation and error-handling sections:

In any case of ambiguity, incomplete data, insufficient constraints, or conflicting inputs, the COO MUST escalate to CEO via QUESTION, consistent with LifeOS §1.3 (“No Silent Assumption Resolution”).

3.4 Freeze Protocol Integration

Insert in sandbox and context-injection sections:

All external calls, including non-deterministic tool invocations, are governed by LifeOS Freeze Protocol.
PB missions inherit all Freeze Protocol semantics; the PB spec does not redefine external determinism.

3.5 Determinism Reframing

Insert in determinism preamble:

All determinism rules within this document are module-level implementations of the LifeOS determinism invariant (LifeOS §2.1).
They are not standalone authorities.

No further changes required to PB spec content.

4. Required Amendments — Antigravity Implementation Packet v0.9.7

This section contains all required edits to ensure the engineering packet aligns to LifeOS and does not act as an independent spec.

4.1 Add Mandatory Preamble

Insert at line 1:

Subordination Clause
This Implementation Packet is subordinate to:

LifeOS v1.1 (constitutional authority)

GPTCOO Project Builder Spec v0.9 (module specification)
This packet has no governance authority.
“MUST”, “SHOULD”, “REQUIRE” describe engineering implementation obligations only, not governance or specification supremacy.

4.2 Remove Governance-Like Language

Replace all instances of:

“senior reviewer approval required”

“council-proxy reviewer required”

“approval gate”

With:

“These steps are engineering workflow norms and do not carry governance authority.”

4.3 Clarify Role Boundaries

Insert:

The Implementation Packet defines only engineering patterns and does not define or modify any LifeOS governance roles.

4.4 Clarify Determinism Status

Insert:

Determinism requirements herein are implementations of LifeOS determinism.
Where LifeOS prescribes determinism, this packet defines only the engineering method.

4.5 Clarify Ambiguity Rules

Insert:

Any engineering scenario with ambiguous or conflicting information MUST escalate through the LifeOS governance path (QUESTION → CEO), not be resolved implicitly.

4.6 Deprecate Spec-like Wording

Replace any wording implying authoritative specification (“non-negotiable”, “authoritative”, “canonical”) with:

“normative engineering pattern for Spec v0.9 compliance”.

5. Unified Alignment Reference (To Include in Repo)

The following should be placed in /docs/ALIGNMENT_README.md:

Canonical Hierarchy

LifeOS v1.1 (Constitution)

GPTCOO Project Builder Spec v0.9 (Subordinate Module Specification)

Antigravity Implementation Packet v0.9.7 (Engineering Implementation)

Source Code (Execution of the Above)

Interpretation Rules

Where PB Spec conflicts with LifeOS → LifeOS wins.

Where Implementation Packet conflicts with PB → PB wins.

Where code conflicts with spec → spec wins (LifeOS §1.5).

Ambiguous cases escalate to CEO.

Determinism is constitutional; PB/Antigravity implement it.

Sandbox, manifest, snapshot, tokenizer behaviours are PB-level behaviours under LifeOS invariants.

No document except LifeOS defines governance.

6. Implementation Required for Antigravity (High-Level)

This packet enforces the following Antigravity tasks:

Add LifeOS subordination clauses to PB spec and Implementation Packet.

Remove all governance-like language from Implementation Packet.

Port all PB functionality into the single unified coo/ runtime tree.

Delete the shadow project_builder/ directory once fully merged.

Update documentation to reflect unified runtime and hierarchy.

Produce Council Review Packet for consolidation approval.

Redeploy Antigravity with aligned specs.

7. Completion Criteria

The consolidation is considered complete when:

All three documents contain the required subordination clauses.

All governance leakage removed.

All determinism rules are phrased as LifeOS implementations.

Repo has a single canonical runtime tree.

A Council Chair Verdict is issued and CEO approves alignment.

Antigravity is executing only the canonical runtime path.

Snapshot, manifest, sandbox, tokenizer, and budget logic match PB spec v0.9 exactly.

All tests pass against the unified runtime.

END — LifeOS Alignment Layer v1.0 (Consolidation Packet)
