# Review Packet: OpenCode Sandbox Activation v2.1 (Fix Pack)

**Mode**: Builder Envelope Hardening
**Date**: 2026-01-12
**Version**: v2.1
**Status**: VERIFIED

## Summary
Fixed security and audit defects identified in v2.0.
1. **Security**: Builder Mode is now fail-closed for structural operations (Delete/Rename/Copy banned). Path security is case-sensitive aware.
2. **Audit**: All hashes are full-length (64 chars). Build Report matches actual captures.

## Acceptance Criteria
- [x] **P0.1 Permissions**: Builder blocks D/R/C.
- [x] **P0.2 Path Security**: Original path used for filesystem checks.
- [x] **P0.3 Symlink**: Staged symlinks blocked.
- [x] **P0.4 Critical Files**: Builder cannot modify gate policy or runner.
- [x] **P0.6 Audit**: No truncated hashes.

## Evidence Appendix

### Test Captures
| Test Suite | Result | SHA256 |
|------------|--------|--------|
| Builder Policy | PASS | `33d57560f4b30d2dcd11a24792730dddbd9df96b1cd6c43fff042c07923a837b` |
| Regression | PASS | `433ccff43bbaea148b3177e99e1eb06a001a8e51a9f89be6f335220cda2db224` |
| G-CBS Audit | PASS | (See `audit_report.md` in bundle) |

### [scripts/opencode_gate_policy.py](scripts/opencode_gate_policy.py)

### [tests/test_opencode_gate_policy_builder.py](tests/test_opencode_gate_policy_builder.py)
