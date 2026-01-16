---
packet_id: 39a4b8c2-11e5-4089-9a22-38d58e37e912
packet_type: PLAN_ARTIFACT
version: 1.2
mission_name: OpenCode Steward Hardening (Council Unblock)
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-06
---

# Plan: OpenCode Steward Hardening (CT-2 Phase 2)

## Goal
Secure the OpenCode CI Runner with mechanical enforcement of governance boundaries, path safety, and process rules (stage-only, review packets), and execute a **deterministic, clean-tree re-certification** to achieve Council passage.

## User Review Required
> [!IMPORTANT]
> - **Input Constraint**: Tasks must be **JSON-structured**. Free-text is rejected unless it references pre-declared files.
> - **Delete Restriction**: Deletion allowed in `docs/**` ONLY if accompanied by a **Validated Review Packet**.
> - **Symlink Defense**: Git index checks will reject any 120000 mode entry (symlink) in the allowed paths.
> - **Packet Schema**: Packets must adhere to a strict schema (Metadata, headings, NO ellipses).

## Proposed Changes

### 1. `scripts/opencode_ci_runner.py` (Enforcement Layer)
#### [MODIFY] Existing Script
- **Input Schema (P0.1)**: 
  - **Strict JSON Phase 2**: The runner will ONLY accept JSON payloads matching `{"files": [...], "action": "...", "instruction": "..."}`.
  - **Free-Text Rejection**: Any non-JSON input is rejected.
- **Path Safety (P0.4)**:
  - `check_path_safety(path)`:
    - **Symlink Defense (Index Level)**: Check git index for mode `120000` on target path or parents. Reject if found. Enforce `os.path.realpath` is within roots.
    - **Canonicalization**: Resolve `..` and ensure path is within allowed roots (`docs/`, `artifacts/review_packets/`).
- **Foundations Override (P0.3)**:
  - **Mechanism**: Requires CLI flag `--override-foundations` AND interactive confirmation (runner waits for token).
  - **Logging**: Emits deterministic `[GOVERNANCE-ALERT] override-foundations triggered` log line.
  - **Task Isolation**: Cannot be triggered by the instruction JSON payload.
- **Delete Plumbing (P0.2)**:
  - **Allowed**: `git rm <path>` (Staged delete).
  - **Blocked**: Arbitrary shell/git passthrough.
  - **Gate**: Any `rm` operation triggers "Review Packet Required" check.
- **Review Packet Gate (P1.1)**:
  - **Schema Validator**:
    - Trigger: Any modify/delete, or override.
    - Check: `artifacts/review_packets/Review_Packet_*.md` in staged files.
    - **Validation Rules**:
      1. Has YAML Metadata header.
      2. Has sections `## Executive Summary`, `## Evidence`, `## Appendix`.
      3. Contains **NO** literal ellipses `...` or `[truncated]`.
- **Artifact Constraints (P1.2)**:
  - `artifacts/evidence/**`: **READ-ONLY**.
  - `artifacts/review_packets/**`: **CREATE-ONLY**. No modify/move of existing packets.
- **Stage-Only (Phase 2)**:
  - `git commit` and `git push` are mechanically blocked.

### 2. `scripts/run_certification_tests.py` (Verification Layer)
#### [MODIFY] Existing Harness
- **Clean Tree Isolation (P0.1)**:
  - Harness creates a dedicated temporary git worktree.
  - Runs certification in isolation.
  - Verifies clean state at start/end.
- **New Security Tests**:
  - `test_security_symlink_index`: Stage a symlink (mode 120000), verify agent refuses to touch it.
  - `test_governance_foundation_interactive`: detailed override test.
  - `test_packet_schema_fail`: Missing section or ellipses -> FAIL.
  - `test_delete_without_packet`: `git rm` without packet -> FAIL.

### 3. CCP Update Protocol (P1.3)
#### Post-Certification Action
1.  Compute SHA-256 of the new `CERTIFICATION_REPORT_v1_3.json`.
2.  Update `artifacts/review_packets/CCP_OpenCode_Steward_Activation_CT2_Phase2.md`:
    - Embed the new SHA-256 in "Evidence Reference".
    - Update "Compliance Status" text.
    - Ensure NO ellipses.

### 4. Waivers (P2.1)
- **Concurrency**: Prohibited. No lockfile implementation in this phase (process isolation assumed).
- **Kill-Switch**: Windows-native `taskkill` is accepted for this environment.

## Verification Plan
1.  **Isolation Check**: Verify worktree creation.
2.  **Certification Run**: Execute full suite (v1.3).
3.  **Hash Verification**: `HASH_MANIFEST.json`.

## CHANGELOG (v1.0 -> v1.2)
- v1.1: Added JSON, Symlinks, Delete-Gate.
- v1.2: Added Index-level symlink check, specific Override mechanism, Packet Schema validator.
