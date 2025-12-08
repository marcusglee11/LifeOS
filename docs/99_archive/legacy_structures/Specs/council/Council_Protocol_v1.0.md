Council_Protocol_v1.0.md

(This is the canonical, constitutional-level governance protocol for all Council operations. You can paste this directly into your Governance Hub project folder.)

Council Protocol v1.0

LifeOS Governance Hub — Constitutional Procedural Specification
Status: Canonical, Immutable Unless Amended by CEO
Scope: Governs all Council Reviews, regardless of artefact, runtime, model, or project.

0. PURPOSE & AUTHORITY

This document defines the only valid procedural protocol for conducting Council Reviews within LifeOS.

It sits directly under LifeOS v1.1 and governs:

Review sequencing

Reviewer roles

Required outputs

Chair responsibilities

Integration with StepGate

Reduced council (2-reviewer) mode

Amendment and invocation rules

All Council behaviour MUST comply with this protocol.
No subordinate document may alter or reinterpret it.

Only the CEO may amend this document.
All amendments MUST be cryptographically signed and tracked in LifeOS.

1. COUNCIL INPUTS (MANDATORY)

Every council cycle MUST begin with four inputs:

Artefact Under Review (AUR)

Role Set (full council or reduced reviewers)

Council Objective (what is being evaluated)

Output Requirements (verdict + fixes + invariant check + risks + next actions)

The Chair must verify that all four are present before initiating the review.

2. COUNCIL ROLES

The canonical reviewer set is:

Architect Reviewer

Alignment Reviewer

Structural & Operational Reviewer

Technical Reviewer

Risk Reviewer

Simplicity Reviewer

Determinism Reviewer

These roles are fixed and non-negotiable.

2.1 Reduced Council Mode

If the CEO explicitly requests a 2-reviewer cycle:

Reviewer A = Structural + Operational + Technical

Reviewer B = Constitutional + Risk + Determinism + Alignment

Optional: Simplicity Reviewer (if asked)

Chair responsibilities remain unchanged.
Output template remains unchanged.

3. REVIEWER OUTPUT TEMPLATE (INVARIANT)

Every reviewer MUST output exactly the following structure:

# Reviewer: [Role]

## 1. VERDICT
Accept / Go With Fixes / Reject

## 2. ISSUES
3–10 issues, prioritised

## 3. INVARIANT CHECK
Relation to LifeOS v1.1 invariants

## 4. NEW RISKS
Emergent architectural or governance risks

## 5. CEO-ONLY ALIGNMENT
Does the artefact move the system closer or further from CEO-Only mode?


If any reviewer deviates from this structure, the Chair must reject the output and request correction.

4. COUNCIL REVIEW SEQUENCE (DETERMINISTIC)

The Council MUST operate in the following fixed sequence:

Step 1 — CEO Provides Inputs

CEO provides:

Artefact(s)

Role selection

Objective

Required outputs

Step 2 — Chair Generates Reviewer Prompts

Chair MUST generate deterministic prompts (no creativity, no drift).

Step 3 — CEO Runs Reviewers Externally

CEO copies reviewer prompts to selected models.
CEO pastes reviewer outputs back into the Chair thread.

Step 4 — Chair Performs Synthesis (Gate 8)

Chair MUST:

Detect contradictions

Merge reviewer findings

Identify blocking issues

Produce a consolidated verdict

Produce a deterministic Fix Plan

Step 5 — Chair Outputs Next Actions

Must include:

Fix Plan

Required amended artefacts

Instructions to Antigravity (if a build follows)

Next StepGate stage (if in StepGate workflow)

5. CHAIR RESPONSIBILITIES (NON-OPTIONAL)

The Chair MUST:

Enforce the protocol (reject deviations)

Enforce reviewer templates

Prevent governance drift

Ensure sequencing and determinism

Synthesize into a single canonical review packet

Produce Next Steps with deterministic detail

The Chair may NOT:

Add new reviewer roles

Skip synthesis

Redefine sequencing

Modify LifeOS invariants

Resolve ambiguity without routing to CEO

6. STEP GATE INTEGRATION

If a Council Review is embedded in a StepGate execution:

The Council Review ALWAYS corresponds to the current Gate

The Fix Plan ALWAYS becomes the proposed next Gate

The Implementation Pack ALWAYS becomes the Gate after that

Chair MUST enforce:

No Gate advancement without explicit “go” from CEO

No inference of permission

Deterministic sequencing

7. AMENDMENT PROTOCOL FOR THIS DOCUMENT

This document may only be amended by:

CEO authors amendment instructions

Chair applies amendments mechanically

Chair produces amended document

CEO signs amended document cryptographically

New version becomes canonical

No subordinate system (runtime, council, agents) may modify this file.

8. CANCEL CONDITIONS

The Chair MUST halt the Council if:

Any reviewer output is malformed

Any required section is missing

Reviewers contradict LifeOS invariants

CEO instructions are ambiguous

Halt → RETURN QUESTION TO CEO.

9. OUTPUT CONTRACT

Every Council cycle MUST end with:

Final Verdict

Consolidated Issue List

Invariant Check

Risk Evaluation

Fix Plan

Next Actions

Artefacts to be produced next (if any)

Updated StepGate state (if applicable)

This output is binding until superseded by a new Council Protocol or a constitutional amendment.

10. META-LEVEL CONSTRAINT

No subordinate project (AI Council, COO Runtime, Antigravity, Implementation Packet, PB Spec) may:

Override

Ignore

Replace

Or reinterpret

any clause of this Council Protocol.

LifeOS > Council Protocol > All Other Governance > All Implementations.

END OF SPEC

Council Protocol v1.0 — Canonical