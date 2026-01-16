---
artifact_id: ""              # Generated via template
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-14T02:00:00Z"
author: "Antigravity"
version: "1.1"
status: "SUPERSEDED"
parent_artifact: "artifacts/plans/Plan_Review_Packet_Schema_Workflow_Hardening_v1.0.md"
tags: ["schema-hardening", "review-packet", "vNext"]
---

# Review Packet Schema + Workflow Audit Hardening (vNext) — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 1.1 |
| **Date** | 2026-01-14 |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Review |
| **Council Trigger** | None |

---

## Executive Summary

This plan hardens the Review Packet schema and workflows (vNext) to reduce review friction. It resolves constitutional contradictions regarding flattening, standardizes evidence grammar, and implements a deterministic preflight validator.

---

## Governance Impact & Authority

* **Constitutional Clarifications**: This plan clarifies `GEMINI.md` Art. XII to resolve a flattening contradiction and standardize pointer grammar. It introduces no net-new governance rules.
* **Plan Gate Enforcement (Validated)**: Mandates strictly adhere to `docs/02_protocols/Build_Artifact_Protocol_v1.0.md`:
  * **Naming**: `Plan_<Topic>_v<X.Y>.md` (Section 5, Table row "Plan").
  * **Placement**: `artifacts/plans/` (Section 2, Table row "Plan").
  * **Formal Artifacts**: "MUST follow... Placement in designated artifacts/ subdirectories" (Section 11.1).

---

## Proposed Changes

### Component 1: Constitutional & Schema

#### [MODIFY] [GEMINI.md](GEMINI.md)

* **Article XII §1**: Add Scope Envelope requirements, Fast-Pass Panel (nested in Acceptance Criteria), and strict Evidence Pointer grammar (`path:Lx-Ly` or `N/A(reason)`).
* **Article XII §4**: Update Self-Check to align with Tiered Flattening (Patch Set default).
* **Article XIII**: Explicitly reference `Build_Artifact_Protocol_v1.0.md` for Plan location/naming constraints.

#### [MODIFY] [docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml](docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml)

* **Locate via**: Repo search for `lifeos_packet_schemas_CURRENT.yaml` or equivalent canonical schema file.
* **Updates**:
  * **Mandatory**: `closure_evidence` object for `REVIEW_PACKET`.
  * **Semantics**: `terminal_outcome` (PASS|BLOCKED|REJECTED) is the strict token.
  * **Deprecation**: `verdict` field enters **Stage 1 Deprecation** (allowed but WARN if mismatched).

### Component 2: Templates

#### [MODIFY] [docs/02_protocols/templates/review_packet_template.md](docs/02_protocols/templates/review_packet_template.md)

* **Locate via**: Repo search for "Review Packet" template in `docs/` or `templates/`.
* **Structure**: Scope -> Summary -> Issue Catalogue -> Acceptance Criteria (inc. Fast-Pass) -> Closure Evidence Checklist -> Non-Goals -> Appendix.
* **Tables**: Add `Evidence Pointer` and `SHA-256` columns.

### Component 3: Tooling

#### [NEW] [scripts/validate_review_packet.py](scripts/validate_review_packet.py)

* **Placement Strategy**:
    1. Use `scripts/` if it exists and contains other validators (e.g., `validate_packet.py`).
    2. Else, used smallest-scope existing tooling directory found.
* **Output Standard**:
  * Pass: `[PASS] Packet valid.`
  * Fail: `[FAIL] <CODE>: <MESSAGE>`
* **Logic**:
  * **Markdown**: RPV001-008 (Section order, Table definitions, Pointer grammar).
  * **YAML**: YPV010-014 (Closure evidence, Terminal Outcome semantics).

---

## Verification Plan

### 1. Verification Matrix (Automated)

**Fixture Strategy**: Do not create new directories unless necessary.

1. Check for existing fixture/test harness location.
2. If none, create strictly limited fallback: `artifacts/misc/validator_fixtures/` (Max 6 files).
3. Clean up fixtures after run if possible, or mark as ephemeral.

| Test Case | Inputs | Expected Output (Exact) |
|-----------|--------|-------------------------|
| **Pass Case** | `valid_packet.md` | `[PASS] Packet valid.` |
| **Fail: Scope** | `fail_scope.md` | `[FAIL] RPV001: Missing section 'Scope Envelope'` |
| **Fail: Section Order** | `fail_order.md` | `[FAIL] RPV002: Section 'Issue Catalogue' found before 'Executive Summary'` |
| **Fail: Pointer** | `fail_ptr.md` | `[FAIL] RPV004: Invalid Evidence Pointer 'see logs'` |
| **Fail: Checklist** | `fail_checklist.md` | `[FAIL] RPV006: Missing mandatory checklist row 'Provenance'` |
| **Fail: Payload** | `fail_payload.yaml` | `[FAIL] YPV011: Missing field 'closure_evidence'` |

### 2. Manual Verification

1. **Constitutional Check**: Verify `GEMINI.md` text regarding flattening does not contradict strict Appendix A rules.
2. **Repo Consistency**: Search for any other `implementation_plan.md` instances and flag them as technical debt (do not fix in this mission).

---

## Plan Change Log

* **P0.1 Plan Gate**: Validated mandates against `Build_Artifact_Protocol_v1.0.md` (Cited Sections 2, 5, 11).
* **P0.2 Discovery**: Replaced hardcoded paths with discovery instructions (e.g., "Locate via repo search").
* **P0.3 Directories**: Defined strict "Use existing or limited fallback" strategy for fixtures.
* **P0.4 Outputs**: Standardized validator output to `[FAIL] <CODE>: <MESSAGE>`.
* **P1.1 Verdict**: Defined **Stage 1 Deprecation** (Warn) for `verdict` field.
* **P1.2 Matrix**: Expanded to 1 Pass + 5 distinct Fail cases.

---

*This plan was drafted by Antigravity under LifeOS Build Artifact Protocol v1.0.*
