---
artifact_id: ""
artifact_type: "PLAN_PACKET"
schema_version: "1.2"
created_at: "2026-01-14T03:10:00Z"
author: "Antigravity"
version: "1.6"
status: "SUPERSEDED"
parent_artifact: "artifacts/plans/Plan_Review_Packet_Schema_Workflow_Hardening_v1.5.md"
tags: ["schema-hardening", "review-packet", "vNext", "governance-correction"]
---

# Scope Envelope

- **Goal**: Harden Review Packet schema and workflows (vNext) with zero net-new constitutional mandates.
- **Non-Goals**: Enforcing versioning lifecycle (moved to P2); Changing Council Protocols.
- **In-Scope Paths**: `GEMINI.md`, `docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml`, `scripts/validate_review_packet.py`, `docs/02_protocols/templates/review_packet_template.md`.

# Proposed Changes

## P0.1 Governance Correctness (No New Mandates)

- **Description**: Downgrade "Anti-Overwrite" and "Version Lifecycle" enforcement to P2 (Proposal).
- **Rationale**: Strict adherence to "No net-new governance rules" instructions.
- **Touchpoints**:
  - `GEMINI.md` (via discovery)

## P0.2 Plan Gate (Discover-and-Cite)

- **Description**: Add Plan Gate check to GEMINI using strictly discovered path citations.
- **Rationale**: Enforce existing protocol without asserting unproven conventions.
- **Touchpoints**:
  - `GEMINI.md` (via discovery)

## P0.3 Validator Exactness

- **Description**: Implement strict code/message mapping and fix checklist failure codes (RPV005/RPV006).
- **Rationale**: Ensure verifiable determinism.
- **Touchpoints**:
  - `scripts/validate_review_packet.py` (New File)

## P0.4 Review Packet Template

- **Description**: Update template to match strict schema structure via discovery.
- **Rationale**: Alignment.
- **Touchpoints**:
  - `review_packet_template.md` (via discovery)

# Claims

- **Claim**: Plan Artifacts must be placed in `artifacts/plans/`
  - **Type**: policy_mandate
  - **Evidence Pointer**: docs/02_protocols/Build_Artifact_Protocol_v1.0.md:L31
  - **Status**: proven

- **Claim**: Plan Artifacts must follow naming pattern `Plan_<Topic>_v<X.Y>.md`
  - **Type**: policy_mandate
  - **Evidence Pointer**: docs/02_protocols/Build_Artifact_Protocol_v1.0.md:L87
  - **Status**: proven

- **Claim**: Formal Artifacts MUST follow placement rules (Section 11.1)
  - **Type**: policy_mandate
  - **Evidence Pointer**: docs/02_protocols/Build_Artifact_Protocol_v1.0.md:L263-L268
  - **Status**: proven

# Targets

- **Target**: `GEMINI.md` (or `AgentConstitution_*.md`)
  - **Type**: modify
  - **Mode**: discover
  - **Intent**: Add Plan Gate check (Evidenced Only). Remove Anti-Overwrite mandate if present.

- **Target**: `lifeos_packet_schemas_CURRENT.yaml`
  - **Type**: modify
  - **Mode**: discover
  - **Intent**: Add Review Packet constraints.

- **Target**: `scripts/`
  - **Type**: new
  - **Mode**: discover
  - **Intent**: Add `validate_review_packet.py`.

# Validator Contract

- **Output Format**: PASS/FAIL
- **Failure Templates (Exact)**:
  - RPV001: Missing section '<SECTION>'.
  - RPV002: Section '<SECTION>' found before '<PREV_SECTION>'.
  - RPV003: Evidence Pointer invalid or missing for claim '<CLAIM>'.
  - RPV004: Evidence Pointer '<PTR>' grammar invalid.
  - RPV005: Missing mandatory checklist row '<ROW>'.
  - RPV006: Checklist item '<ROW>' verification failed (empty).
  - YPV010: Governance impact missing gate/rationale.
  - YPV011: Missing field '<FIELD>' in YAML.

# Verification Matrix

| Case ID | Input Fixture | Expected | Expected Code | Prefix |
|---------|---------------|----------|---------------|--------|
| PASS_01 | valid_packet.md | PASS   |               |        |
| FAIL_01 | fail_scope.md   | FAIL   | RPV001        | Missing section 'Scope Envelope'|
| FAIL_02 | fail_order.md   | FAIL   | RPV002        | Section 'Issue Catalogue' found before 'Summary'|
| FAIL_05 | fail_chk_row.md | FAIL   | RPV005        | Missing mandatory checklist row 'Provenance'|
| FAIL_06 | fail_chk_val.md | FAIL   | RPV006        | Checklist item 'Provenance' verification failed|
| FAIL_11 | fail_yaml.yaml  | FAIL   | YPV011        | Missing field '<FIELD>' in YAML|

# Migration Plan

- **Backward Compat**: Warn on legacy verdicts (Stage 1).
- **Rollout Stages**: Immediate adoption.
- **Deprecation Rules**: `verdict` field deprecated (WARN).

# Governance Impact

- **Touches Constitution**: yes
- **Gate**: CEO Approval
- **Rationale**: Enforcing existing Plan Gate protocols using strict citations.
