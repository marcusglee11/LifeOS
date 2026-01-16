---
artifact_id: ""              # Generated via template
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-14T01:30:00Z"
author: "Antigravity"
version: "1.0"
status: "SUPERSEDED"
tags: ["schema-hardening", "review-packet", "vNext"]
---

# Review Packet Schema + Workflow Audit Hardening (vNext) — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Date** | 2026-01-14 |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Review |
| **Council Trigger** | None |

---

## Executive Summary

This plan hardens the Review Packet schema and workflows (vNext) to reduce review friction. It resolves constitutional contradictions regarding flattening, standardizes evidence pointer grammar, introduces an "Acceptance Criteria" Fast-Pass Panel, and implements a deterministic preflight validator `validate_review_packet.py` to enforce these standards.

---

## Problem Statement

Review packets currently suffer from ambiguous requirements (e.g., flattening contradictions) and variable evidence quality. This causes review drag. A validated schema is required.

---

## Governance Impact & Authority

* **Constitutional Clarifications**: This plan clarifies `GEMINI.md` Art. XII to resolve a flattening contradiction and standardize pointer grammar. It introduces no net-new governance rules.
* **Plan Gate Enforcement**: Citations below affirm existing policy; no new conventions are invented.
  * **Mandate**: `artifacts/plans/` location and `Plan_<Topic>_vX.Y.md` naming.
  * **Authority**: `docs/02_protocols/Build_Artifact_Protocol_v1.0.md` Section 2 ("Canonical Path: `artifacts/plans/`") and Section 11.1 ("Formal Artifacts... MUST follow... Placement in designated artifacts/ subdirectories").

---

## Proposed Changes

### Component 1: Constitutional & Schema

#### [MODIFY] [GEMINI.md](GEMINI.md)

* **Article XII §1**: Add Scope Envelope requirements, Fast-Pass Panel (nested in Acceptance Criteria), and strict Evidence Pointer grammar.
* **Article XII §4**: Update Self-Check to align with Tiered Flattening (Patch Set default).
* **Article XIII**: Explicitly reference `Build_Artifact_Protocol_v1.0.md` for Plan location/naming constraints.

#### [MODIFY] [docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml](docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml)

* **REVIEW_PACKET Payload**:
  * **Mandatory**: `closure_evidence` object.
  * **Canonical Semantics**: `terminal_outcome` (PASS|BLOCKED|REJECTED) is the strict status token. `verdict` is deprecated.
  * **Shape**: Define `closure_evidence` (Provenance, Artifacts, Repro, Governance, Outcome).

### Component 2: Templates

#### [MODIFY] [docs/02_protocols/templates/review_packet_template.md](docs/02_protocols/templates/review_packet_template.md)

* **Structure**: Scope -> Summary -> Issue Catalogue -> Acceptance Criteria (Fast-Pass Panel included) -> Closure Evidence Checklist -> Non-Goals -> Appendix.
* **Tables**: Add `Evidence Pointer` and `SHA-256` columns to Acceptance Criteria.

#### [MODIFY] [docs/02_protocols/lifeos_packet_templates_v1.yaml](docs/02_protocols/lifeos_packet_templates_v1.yaml)

* Update Template 5 (REVIEW_PACKET) to match vNext schema.

### Component 3: Tooling

#### [NEW] [scripts/validate_review_packet.py](scripts/validate_review_packet.py)

* **Location**: `scripts/` (collocated with existing `validate_packet.py` and `closure/` tooling).
* **Logic**:
  * **Markdown**: RPV001-008 (Section order, Table definitions, Pointer grammar).
  * **YAML**: YPV010-014 (Closure evidence, Terminal Outcome semantics).

---

## Verification Plan

### Automated Tests (Validator Matrix)

Target fixtures will be generated in `artifacts/misc/validator_fixtures/` (deterministic fallback location).

| Test | Command | Expected |
|------|---------|----------|
| **Pass Case** | `python scripts/validate_review_packet.py artifacts/misc/validator_fixtures/valid_packet.md` | `[PASS] Packet valid.` (Exit 0) |
| **Fail: Scope** | `python scripts/validate_review_packet.py artifacts/misc/validator_fixtures/fail_scope.md` | `[FAIL] RPV001: Missing section 'Scope Envelope'` |
| **Fail: Pointer** | `python scripts/validate_review_packet.py artifacts/misc/validator_fixtures/fail_ptr.md` | `[FAIL] RPV004: Invalid Evidence Pointer 'see logs'` |
| **Fail: yaml** | `python scripts/validate_review_packet.py artifacts/misc/validator_fixtures/fail_payload.yaml` | `[FAIL] YPV011: Missing field 'closure_evidence'` |

### Manual Verification

1. **Constitutional Consistency**: Verify `GEMINI.md` flattening checks align with Appendix A.
2. **Validator Execution**: Run `validate_review_packet.py` on the self-generated `Review_Packet_Review_Packet_Schema_Hardening_v1.0.md` (which will be moved to `artifacts/review_packets/` per protocol).

---

## Non-Goals

* Do not modify `BUILD_PACKET` or other schemas.
* Do not introduce new directories; use existing `scripts/` and `artifacts/`.

---

*This plan was drafted by Antigravity under LifeOS Build Artifact Protocol v1.0.*
