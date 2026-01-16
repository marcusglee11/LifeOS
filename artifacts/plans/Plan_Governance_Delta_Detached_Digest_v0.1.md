---
artifact_id: "0a76b41b-8c90-4d92-b516-c540ebcd0762"
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-06T19:55:00+11:00"
author: "Antigravity"
version: "0.1"
status: "SUPERSEDED"
mission_ref: "Governance_Delta_Detached_Digest"
council_trigger: "CT-2"
tags: [governance, g-cbs, detached-digest, attestation]
superseded_by: "artifacts/plans/Plan_Governance_Delta_Detached_Digest_v0.2.md"
---

# Plan: Governance Delta — Detached Digest + Two-Part Attestation

## Executive Summary

This plan formalizes the Detached Digest protocol and introduces a Two-Part Attestation Model for G-CBS closure bundles. Currently, G-CBS semantics are defined inline in `Council_Protocol_v1.2.md` §2.5 without sufficient detail. This creates ambiguity around validator evidence (what it validates) and circularity (embedded evidence referring to the containing ZIP). We propose creating a canonical `G-CBS_Standard_v1.0.md` protocol document and updating the validator/builder to implement explicit, machine-verifiable semantics.

## Problem Statement

**Current Issues:**
1. No standalone G-CBS protocol document exists — only 3 bullets in Council Protocol
2. "Final shipped validation" is ambiguous — does it mean payload or container?
3. Embedding validator transcript inside ZIP creates semantic circularity
4. Validator output doesn't explicitly attest sidecar verification
5. No provenance fields link bundles to specific protocol versions

## Proposed Changes

### Component 1: Protocol Documentation

#### [NEW] `docs/02_protocols/G-CBS_Standard_v1.0.md`
Canonical specification containing:
- **§1 Overview**: Purpose, scope, authority chain
- **§2 Detached Digest Mode**: Marker, sidecar format, validator requirements
- **§3 Two-Part Attestation Model**: Payload Compliance vs Container Integrity
- **§4 Evidence Roles**: Rename `validator_final_shipped` → `validator_payload_pass`
- **§5 Provenance Fields**: `activated_protocols_ref`, `activated_protocols_sha256`
- **§6 Validator Output Contract**: Explicit stdout lines

#### [MODIFY] `docs/02_protocols/Council_Protocol_v1.2.md`
Update §2.5 to reference `G-CBS_Standard_v1.0.md` instead of inline rules.

---

### Component 2: Validator Update

#### [MODIFY] `scripts/closure/validate_closure_bundle.py`
- Print explicit, stable sidecar verification lines:
  - `Detached digest mode: true`
  - `Sidecar digest path: <path>`
  - `Sidecar digest verified: <sha256>`
- Fail closed with deterministic error codes
- Accept new role `validator_payload_pass`

---

### Component 3: Builder Update

#### [MODIFY] `scripts/closure/build_closure_bundle.py`
- Add manifest fields: `activated_protocols_ref`, `activated_protocols_sha256`
- Rename evidence role to `validator_payload_pass`
- Bump profile version to 1.2.3

---

### Component 4: Tests

#### [MODIFY] `scripts/closure/tests/test_gcbs_a1a2_regressions.py`
- Test: Sidecar verification stdout lines present
- Test: `validator_payload_pass` role accepted
- Test: Provenance fields present and correct

## Verification Plan

### Automated Tests
```bash
pytest tests_doc/test_tdd_compliance.py
pytest scripts/closure/tests/
```

### Manual Verification
- Inspect v1.2.3 bundle for new evidence role and provenance fields
- Verify validator stdout includes explicit sidecar verification line

## User Review Required

> [!IMPORTANT]
> **Decision: Evidence Role Rename**
> Proposed: `validator_final_shipped` → `validator_payload_pass`
> This clarifies that the embedded transcript attests *payload compliance*, not container integrity.

> [!IMPORTANT]
> **Decision: Provenance Reference**
> Proposed: Reference `docs/02_protocols/G-CBS_Standard_v1.0.md` as `activated_protocols_ref`
> Alternative: Reference a composite "activated protocols index" if one exists.

## Non-Goals

- Changing ZIP determinism mechanics (timestamps, compression, ordering)
- Broadening to unrelated protocol changes
- Introducing manual verification steps
