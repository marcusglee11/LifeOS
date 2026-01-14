---
artifact_id: ""              # Generated via template
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-14T02:50:00Z"
author: "Antigravity"
version: "1.4"
status: "SUPERSEDED"
parent_artifact: "artifacts/plans/Plan_Review_Packet_Schema_Workflow_Hardening_v1.3.md"
tags: ["schema-hardening", "review-packet", "vNext", "anti-overwrite"]
---

# Review Packet Schema + Workflow Audit Hardening (vNext) — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 1.4 |
| **Date** | 2026-01-14 |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Review |
| **Council Trigger** | None |

---

## Executive Summary

This plan hardens the Review Packet schema and workflows (vNext) to reduce review friction. It resolves constitutional contradictions regarding flattening, standardizes evidence grammar, and implements a deterministic preflight validator. Critically, it now includes **Constitutional Safeguards** to prevent versioning protocol violations (in-place edits).

---

## Governance Impact & Authority

* **Governance Gate**: CEO-only approval (clarification + protocol enforcement; no net-new rules).
* **Plan Gate Enforcement (Evidenced)**:
  * **Mandate**: `artifacts/plans/` location and `Plan_<Topic>_v<X.Y>.md` naming.
  * **Authority**: `docs/02_protocols/Build_Artifact_Protocol_v1.0.md`:
    * **Section 2**: Row "Plan" mandates path `artifacts/plans/` (Line 31).
    * **Section 5**: Row "Plan" mandates pattern `Plan_<Topic>_v<X.Y>.md` (Line 87).
    * **Section 11.1**: Formal Artifacts "MUST follow... Placement in designated artifacts/ subdirectories" (Lines 263-268).

---

## Proposed Changes

### Component 1: Constitutional & Schema

#### [MODIFY] <CANONICAL_GEMINI_PATH>

* **Locate via**: Repo search for `GEMINI.md` or `AgentConstitution_*.md`.
* **Updates**:
  * **Article XII §1**:
    * **Evidence Pointer Grammar (Strict)**: `path | path:Lx-Ly | path#sha256:<HEX64> | N/A(<reason>)`. Bare `N/A` is **INVALID**.
    * **Fast-Pass Panel**: Nested block within "Acceptance Criteria".
  * **Article XII §4**: Update Self-Check to align with Tiered Flattening (Patch Set default).
  * **Article XIII (Plan Gate)**:
    * Explicitly reference `Build_Artifact_Protocol_v1.0.md` for Plan constraints.
    * **NEW MANDATE**: Mandate strict adherence to `Build_Artifact_Protocol_v1.0.md` Section 8 (Version Lifecycle).
    * **PROHIBIT** in-place edits (overwrites) to any versioned artifact file.
    * **REQUIRE** a new version file (vX.Y+1) and marking the parent as `SUPERSEDED` for every modification.

#### [MODIFY] <CANONICAL_PACKET_SCHEMA_PATH>

* **Locate via**: Repo search for `lifeos_packet_schemas_CURRENT.yaml` or equivalent.
* **Updates**:
  * **Mandatory**: `closure_evidence` object for `REVIEW_PACKET`.
  * **Semantics**: `terminal_outcome` (PASS|BLOCKED|REJECTED) is the strict token.
  * **Deprecation**: `verdict` field enters **Stage 1 Deprecation** (allowed but WARN if mismatched).

### Component 2: Templates

#### [MODIFY] <CANONICAL_REVIEW_PACKET_TEMPLATE_PATH>

* **Locate via**: Repo search for `review_packet_template.md` in `docs/` or `templates/`.
* **Structure**: Scope -> Summary -> Issue Catalogue -> Acceptance Criteria (inc. Fast-Pass) -> Closure Evidence Checklist -> Non-Goals -> Appendix.
* **Tables**: Add `Evidence Pointer` and `SHA-256` columns.

### Component 3: Tooling

#### [NEW] <VALIDATOR_SCRIPT_PATH>

* **Placement Strategy**:
    1. Use `scripts/` if it exists and contains other validators.
    2. Else, used smallest-scope existing tooling directory found.
* **Output Standard (Canonical)**:
  * **Pass**: `[PASS] Packet valid.`
  * **Fail**: `[FAIL] <CODE>: <MESSAGE>`
* **Logic**:
  * **Markdown**: RPV001-008 (Section order, Table definitions, Pointer grammar).
  * **YAML**: YPV010-014 (Closure evidence, Terminal Outcome semantics).

---

## Verification Plan

### 1. Verification Matrix (Automated)

**Fixture Strategy**:

* **Discovery**: Check for existing fixture/test harness location.
* **Fallback**: If none, create `artifacts/misc/validator_fixtures/` (Max 6 files).
* **Retention**: Fixtures are kept with stable naming for regression checks.

| Test Case | Inputs | Expected Output (Exact format) |
|-----------|--------|--------------------------------|
| **Pass Case** | `valid_packet.md` | `[PASS] Packet valid.` |
| **Fail: Scope** | `fail_scope.md` | `[FAIL] RPV001: Missing section 'Scope Envelope'` |
| **Fail: Order** | `fail_order.md` | `[FAIL] RPV002: Section 'Issue Catalogue' found before 'Summary'` |
| **Fail: Pointer** | `fail_ptr.md` | `[FAIL] RPV004: Invalid Evidence Pointer 'see logs'` |
| **Fail: Checklist** | `fail_checklist.md` | `[FAIL] RPV006: Missing mandatory checklist row 'Provenance'` |
| **Fail: Payload** | `fail_payload.yaml` | `[FAIL] YPV011: Missing field 'closure_evidence'` |

### 2. Manual Verification

1. **Constitutional Check**: Verify `GEMINI.md` text regarding flattening does not contradict strict Appendix A rules.
2. **Versioning Check**: Verify that `Plan_Review_Packet_Schema_Workflow_Hardening_v1.2.md` and `v1.3.md` are marked `SUPERSEDED` and no content was lost in the `v1.4` iteration.

---

## Plan Change Log

* **P0.1 Plan Gate**: Added precise citations to `Build_Artifact_Protocol_v1.0.md` (Sec 2, 5, 11).
* **P0.2 Discovery**: Replaced hardcoded headers with defined discovery rules.
* **P0.3 Grammar**: Locked Evidence Pointer syntax; explicit ban on bare "N/A".
* **P0.4 Outputs**: Canonicalized validator outputs (`[FAIL] ...`).
* **P0.5 Matrix**: Fixed "Summary" section name; aligned codes.
* **P0.6 Fixtures**: Deterministic retention strategy (max 6 files).
* **P0.7 VERSIONING SAFEGUARD**: Added explicit Article XIII update to mandate Section 8 (Lifecycle) and prohibit in-place overwrites.
* **P1.1 Governance**: Added "CEO-only approval" gate.
* **P1.2 Tech Debt**: Flagging old plans as non-blocking technical debt.

---

*This plan was drafted by Antigravity under LifeOS Build Artifact Protocol v1.0.*
