---
artifact_id: ""
artifact_type: "PLAN_PACKET"
schema_version: "1.2"
created_at: "2026-01-14T03:30:00Z"
author: "Antigravity"
version: "1.7"
status: "DRAFT"
parent_artifact: "artifacts/plans/Plan_Review_Packet_Schema_Workflow_Hardening_v1.6.md"
tags: ["schema-hardening", "review-packet", "vNext", "governance-correction"]
---

# Scope Envelope

- **Goal**: Harden Review Packet schema and workflows (vNext) with deterministic validation and no net-new unproven mandates.
- **Non-Goals**: Hardening Plan Packets (Out of scope); Enforcing versioning lifecycle (P2); Changing Council Protocols.
- **In-Scope Artefacts (resolved by discovery)**:
  - Agent Constitution (pattern: `AgentConstitution_*.md` or `GEMINI.md`)
  - Packet Schemas (pattern: `*packet_schemas*.yaml`)
  - Review Packet Template (pattern: `*review_packet_template*.md`)
  - Validator Scripts (pattern: `validate_review_packet.py` in tooling dir)

# Proposed Changes

## P0.1 Governance Correctness (Fail-Closed)

- **Description**: Downgrade "Anti-Overwrite" to P2. Modify Plan Gate language ONLY if an equivalent gate already exists in the constitution; otherwise record as P2 proposal.
- **Rationale**: Strict adherence to "No net-new governance rules".
- **Touchpoints**:
  - `GEMINI.md` (via discovery)

## P0.2 Plan Gate (Verified Citation)

- **Description**: Add Plan Gate check using strictly discovered path citations (path:Lx-Ly).
- **Rationale**: Enforce existing protocol without asserting unproven conventions.
- **Touchpoints**:
  - `GEMINI.md` (via discovery)

## P0.3 Review Packet Validator Implementation

- **Description**: Implement `validate_review_packet.py` with strict RPV/YPV codes for Review Packets (NOT Plans).
- **Rationale**: Deterministic closure.
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
  - **Status**: asserted

- **Claim**: Plan Artifacts must follow naming pattern `Plan_<Topic>_v<X.Y>.md`
  - **Type**: policy_mandate
  - **Evidence Pointer**: docs/02_protocols/Build_Artifact_Protocol_v1.0.md:L87
  - **Status**: asserted

- **Claim**: Formal Artifacts MUST follow placement rules (Section 11.1)
  - **Type**: policy_mandate
  - **Evidence Pointer**: docs/02_protocols/Build_Artifact_Protocol_v1.0.md:L263-L268
  - **Status**: asserted

# Targets

- **Target**: Canonical Constitution (`GEMINI.md`)
  - **Type**: modify
  - **Mode**: discover
  - **Intent**: Add Plan Gate check (Fail-Closed).

- **Target**: Canonical Schema (`*packet_schemas*.yaml`)
  - **Type**: modify
  - **Mode**: discover
  - **Intent**: Add Review Packet constraints (semantic tokens).

- **Target**: Tooling Dir (`scripts/`)
  - **Type**: new
  - **Mode**: discover
  - **Intent**: Add `validate_review_packet.py`.

# Validator Contract

- **Output Format**: PASS/FAIL
- **Failure Templates (Exact)**:
  - RPV001: Missing section '<SECTION>'.
  - RPV002: Section '<SECTION>' found before '<PREV_SECTION>'.
  - RPV003: Evidence Pointer missing for Acceptance Criterion '<CRITERION>'.
  - RPV004: Evidence Pointer '<PTR>' grammar invalid.
  - RPV005: Missing mandatory checklist row '<ROW>'.
  - RPV006: Checklist item '<ROW>' verification failed (empty).
  - YPV011: Missing field '<FIELD>' in YAML.
  - YPV012: Invalid or missing 'terminal_outcome' (Must be PASS|BLOCKED|REJECTED).
  - YPV013: Missing 'closure_evidence' object.

# Verification Matrix

| Case ID | Input Fixture | Expected | Expected Code | Prefix |
|---------|---------------|----------|---------------|--------|
| PASS_01 | valid_packet.md | PASS   |               |        |
| FAIL_01 | fail_scope.md   | FAIL   | RPV001        | Missing section 'Scope Envelope'|
| FAIL_02 | fail_order.md   | FAIL   | RPV002        | Section 'Issue Catalogue' found before 'Summary'|
| FAIL_05 | fail_chk_row.md | FAIL   | RPV005        | Missing mandatory checklist row 'Provenance'|
| FAIL_06 | fail_chk_val.md | FAIL   | RPV006        | Checklist item 'Provenance' verification failed|
| FAIL_11 | fail_yaml.yaml  | FAIL   | YPV011        | Missing field 'closure_evidence' in YAML|

# Migration Plan

- **Backward Compat**: Warn on legacy verdicts (Stage 1).
- **Rollout Stages**: Immediate adoption.
- **Deprecation Rules**: Stage 2: FAIL if `verdict` field is present.

# Governance Impact

- **Touches Constitution**: yes
- **Gate**: CEO Approval
- **Rationale**: Enforcing existing Plan Gate protocols using strict citations.
