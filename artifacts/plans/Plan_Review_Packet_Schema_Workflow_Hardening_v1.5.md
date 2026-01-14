---
artifact_id: ""              # Generated via template
artifact_type: "PLAN_PACKET"
schema_version: "1.2"
created_at: "2026-01-14T03:00:00Z"
author: "Antigravity"
version: "1.5"
status: "SUPERSEDED"
parent_artifact: "artifacts/plans/Plan_Review_Packet_Schema_Workflow_Hardening_v1.4.md"
tags: ["schema-hardening", "review-packet", "vNext", "plan-packet-adoption"]
---

# Scope Envelope

- **Goal**: Harden Review Packet schema and workflows (vNext) to reduce review friction and enforce deterministic validations.
- **Non-Goals**: Changing Council Protocols; Refactoring unrelated tooling.
- **In-Scope Paths**: `GEMINI.md`, `docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml`, `scripts/validate_review_packet.py`, `docs/02_protocols/templates/review_packet_template.md`.

# Proposed Changes

## P0.1 Constitutional Hardening

- **Description**: Update GEMINI.md to enforce strict Evidence Pointers, Fast-Pass Panel, and the new PLAN_PACKET schema itself.
- **Rationale**: Eliminate ambiguity in review friction points and bind agents to the new schema.
- **Touchpoints**:
  - `GEMINI.md` (via discovery)

## P0.2 Schema Updates

- **Description**: Update valid packet schema to include strict semantic tokens (PASS|BLOCKED|REJECTED) and mandatory evidence fields.
- **Rationale**: Automate outcome parsing and ensure audit trails.
- **Touchpoints**:
  - `lifeos_packet_schemas_CURRENT.yaml` (via discovery)

## P0.3 Validator Implementation

- **Description**: Implement `scripts/validate_review_packet.py` with canonical output format `[FAIL] <CODE>: <MESSAGE>`.
- **Rationale**: Provide deterministic, machine-parseable feedback to agents.
- **Touchpoints**:
  - `scripts/validate_review_packet.py` (New File)

## P0.4 Template Updates

- **Description**: Update Review Packet template to match the new schema structure (Scope -> Summary -> Issue Catalogue...).
- **Rationale**: Ensure human artifacts match validator expectations.
- **Touchpoints**:
  - `docs/02_protocols/templates/review_packet_template.md` (via discovery)

# Claims

- **Claim**: Plan Artifacts must be placed in `artifacts/plans/`
  - **Type**: policy_mandate
  - **Evidence Pointer**: docs/02_protocols/Build_Artifact_Protocol_v1.0.md:L31
  - **Status**: proven

- **Claim**: Plan Artifacts must follow naming pattern `Plan_<Topic>_v<X.Y>.md`
  - **Type**: policy_mandate
  - **Evidence Pointer**: docs/02_protocols/Build_Artifact_Protocol_v1.0.md:L87
  - **Status**: proven

- **Claim**: In-place edits to versioned artifacts are PROHIBITED (Anti-Overwrite).
  - **Type**: policy_mandate
  - **Evidence Pointer**: docs/02_protocols/Build_Artifact_Protocol_v1.0.md:L263-L268
  - **Status**: proven

# Targets

- **Target**: `GEMINI.md` (or `AgentConstitution_*.md`)
  - **Type**: modify
  - **Mode**: discover
  - **Intent**: Enforce PLAN_PACKET schema and Review Packet hardening.

- **Target**: `lifeos_packet_schemas_CURRENT.yaml`
  - **Type**: modify
  - **Mode**: discover
  - **Intent**: Add Review Packet constraints.

- **Target**: `scripts/`
  - **Type**: new
  - **Mode**: discover
  - **Intent**: Add `validate_review_packet.py`.

- **Target**: `review_packet_template.md`
  - **Type**: modify
  - **Mode**: discover
  - **Intent**: Update template structure.

# Validator Contract

- **Output Format**: PASS/FAIL
- **Failure Codes**:
  - RPV001: Missing section
  - RPV002: Invalid Section Order
  - RPV003: Invalid Evidence Pointer
  - RPV004: Invalid Evidence Pointer Grammar
  - RPV006: Missing mandatory checklist row
  - YPV011: Missing field in YAML

# Verification Matrix

| Case ID | Input Fixture | Expected | Expected Code | Prefix |
|---------|---------------|----------|---------------|--------|
| PASS_01 | valid_packet.md | PASS   |               |        |
| FAIL_01 | fail_scope.md   | FAIL   | RPV001        | Missing|
| FAIL_02 | fail_order.md   | FAIL   | RPV002        | Order  |
| FAIL_04 | fail_ptr.md     | FAIL   | RPV004        | Invalid|
| FAIL_06 | fail_check.md   | FAIL   | RPV006        | Missing|
| FAIL_11 | fail_yaml.yaml  | FAIL   | YPV011        | Missing|

# Migration Plan

- **Backward Compat**: Warn on legacy verdicts (Stage 1).
- **Rollout Stages**: Immediate adoption for next mission.
- **Deprecation Rules**: `verdict` field deprecated (WARN).

# Governance Impact

- **Touches Constitution**: yes
- **Gate**: CEO Approval
- **Rationale**: Clarifying existing protocols and enforcing the new Plan Schema to prevent feedback loops.
