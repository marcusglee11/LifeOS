---
packet_id: 39a4b8c2-11e5-4089-9a22-38d58e37e912
packet_type: PLAN_ARTIFACT
version: 1.4
mission_name: OpenCode Steward Hardening (Council Unblock)
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Plan: OpenCode Steward Hardening (CT-2 Phase 2)

## Goal
Secure the OpenCode CI Runner with mechanical enforcement of governance boundaries, path safety, and process rules (stage-only, review packets), and execute a **deterministic, clean-tree re-certification** to achieve Council passage.

## User Review Required
> [!IMPORTANT]
> - **JSON-Only Input**: Phase 2 accepts ONLY structured JSON tasks. Free-text is rejected.
> - **Delete Restriction**: ANY delete triggers a Review Packet requirement.
> - **Symlink Defense**: Index-level (mode 120000) AND filesystem-level (parent symlinks) checks.
> - **Packet Schema**: Packets must pass explicit schema validation (metadata, headings, no ellipses).
> - **Archive Removed**: 'Archive' semantics removed in v1.4 to ensure deterministic certification.

## Proposed Changes

### 1. `scripts/opencode_ci_runner.py` (Enforcement Layer)

#### Input Schema (P0.1)
- **JSON-Only**: The runner accepts ONLY JSON payloads matching:
  ```json
  {"files": ["path1", "path2"], "action": "create|modify|delete", "instruction": "..."}
  ```
- **Free-Text Rejection**: Any non-JSON input causes immediate rejection with exit code 1.
- **Archive Action**: Removed.

#### Path Safety (P0.4)
- **Symlink Defense (Dual-Level)**:
  1. **Index-Level**: Query `git ls-files -s` for target path. Reject if mode is `120000` (symlink).
  2. **Filesystem-Level**: For each path component, reject if `os.path.islink()` returns True.
  3. **Realpath Containment**: `os.path.realpath(path)` must start with an allowed root (`docs/`, `artifacts/review_packets/`).
- **Canonicalization**: Reject any path containing `..` or absolute paths.

#### Denylist Enforcement (P0.3)
Mirrored from CCP `denylist_surfaces`:
| Pattern | Action | Enforcement |
|---------|--------|-------------|
| `docs/00_foundations/**` | modify | Reject unless `--override-foundations` flag + interactive token |
| `config/**` | any | Reject unconditionally |
| `scripts/**` | modify | Reject unconditionally |
| `**/*.py` | modify | Reject unconditionally (even under docs/) |
| `GEMINI.md` | modify | Reject unconditionally |

#### Foundations Override Mechanism (P0.3)
- **CLI Flag**: `--override-foundations`
- **Interactive Token**: Runner prompts for confirmation string (e.g., `CONFIRM_OVERRIDE`).
- **Task Isolation**: The `instruction` field in JSON cannot trigger override.
- **Logging**: Emits `[GOVERNANCE-ALERT] override-foundations triggered at <timestamp>`.
- **Gate**: Override automatically triggers Review Packet requirement.

#### Delete Plumbing (P0.2)
- **Allowed Command**: `git rm <path>` (staged delete).
- **Blocked**: Arbitrary shell/git passthrough; only whitelisted subcommands (`add`, `rm`, `ls-files`).
- **Gate**: ANY delete (even single file) triggers Review Packet requirement.

#### Review Packet Gate (P0.2, P1.1)
**Trigger Conditions** (ANY triggers requirement):
1. ANY delete operation (A/M/D/R with D present).
2. More than 1 file touched (staged count > 1).
3. `--override-foundations` used.
4. Any governance-protected surface touched (per denylist).

> **Policy Note**: Phase 2 adopts a conservative trigger: any modify/delete requires a packet to maximize auditability.

**Validation Rules** (Schema):
1. Has YAML frontmatter with `packet_id`, `packet_type`, `version`, `mission_name`, `author`, `status`, `date`.
2. Has sections: `## Summary` or `## Executive Summary`, `## Changes` or `## Evidence`, `## Appendix`.
3. Contains NO literal ellipses (`...`) or `[truncated]`.
4. File is located at `artifacts/review_packets/Review_Packet_*.md`.
5. File is staged as Added (A) only (not Modified/Renamed/Deleted).

**Enforcement**: Use `git diff --cached --name-status` to verify:
- Packet file is staged.
- Packet file status is `A` (Added).
- No existing `Review_Packet_*.md` is Modified (M), Renamed (R), or Deleted (D).

#### Artifact Constraints (P1.2)
- `artifacts/evidence/**`: **READ-ONLY**. Reject any write operation.
- `artifacts/review_packets/**`: **CREATE-ONLY**. Reject modify/rename/delete of existing packets.

#### Stage-Only (Phase 2)
- `git commit` and `git push` are mechanically blocked (whitelist approach).

### 2. `scripts/run_certification_tests.py` (Verification Layer)

#### Clean Tree Isolation (P0.1 - Mandated)
- Creates temporary `git clone` of HEAD.
- Spawns **private** `opencode serve` instance on isolated port (62586).
- Auto-commits harness patches to ensure clean baseline.
- Asserts strict clean state (T-GIT-1).

#### Security Tests
- `test_security_symlink_index`: Stage symlink (mode 120000), verify rejection.
- `test_security_path_traversal`, `test_absolute_path_rejected`.
- `test_git_index_symlink_attack` (T-SEC-10): Forges 120000 mode entry, ensures rejection.

### 3. CCP Update Protocol (P1.2, P1.3)
#### Canonical CCP Location
- **Policy**: Update the canonical CCP file in its governance-controlled location; do not duplicate CCPs under review packet folders (unless they are the canonical source).
- **Target**: `artifacts/review_packets/CCP_OpenCode_Steward_Activation_CT2_Phase2.md` (Confirmed Canonical).

#### Post-Certification Action
1. Compute SHA-256 of `CERTIFICATION_REPORT_v1_4.json`.
2. Update the CCP's "Evidence Reference" section with the new SHA-256.
3. Update "Compliance Status" to match actual test results.
4. Verify NO ellipses in CCP.

### 4. Waivers (P2.1)
- **Concurrency**: Prohibited. No lockfile in Phase 2 (future work).
- **Kill-Switch**: Windows-native `taskkill` accepted. Cross-platform support deferred.

## Verification Plan
1. **Isolation Check**: Verify worktree creation/destruction.
2. **Certification Run**: Execute full suite (v1.4) in isolation.
3. **Hash Verification**: Produce `HASH_MANIFEST_v1.4.json`.

## CHANGELOG
- **v1.4**:
  - **P0.1**: Fixed Clean Tree Isolation (Dedicated Server + Auto-Commit).
  - **P1.1**: Removed `archive` authority (Option B) for determinism.
  - **P1.2**: Added Git Index Symlink (120000) test (T-SEC-10).
- **v1.2 -> v1.3**:
  - P0.1: Removed free-text exception; JSON-only for Phase 2.
  - P0.2: Explicit trigger conditions for Review Packet (any delete, >1 file, override, governance).
  - P0.3: Mirrored CCP denylist in mechanical checks (py files, config, scripts, GEMINI.md, foundations).
  - P0.4: Added filesystem-level symlink check (parent components) + realpath containment.
  - P1.1: Review Packet must be Added-only (A); reject M/R/D on existing packets.
