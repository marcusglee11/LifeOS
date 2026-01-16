# OpenCode Steward Certification Log (v1.4)

**Date**: 2026-01-07
**Suite Version**: v1.4
**Runner Version**: Hardening v1.4 (CT-2 Phase 2)

## Test Summary
- **Total Tests**: 13
- **Passed**: 13
- **Failed**: 0
- **Waivers**: NONE

## Key Validations
1. **Isolation (P0.1)**: [PASS] `T-GIT-1` confirms clean tree using dedicated isolation server and auto-committed patches.
2. **Symlink Defense (P0.4/P1.2)**: [PASS] `T-SEC-10` confirms rejection of Git Index symlinks (mode 120000).
3. **Archive Semantics (P1.1)**: Removed from scope (Option B) to ensure deterministic certification.
4. **Denylist**: [PASS] All protected surfaces (Foundations, Config, Scripts, .py, Evidence) rejected.

## Evidence
- **Report**: [CERTIFICATION_REPORT_v1_4.json](./CERTIFICATION_REPORT_v1_4.json)
- **Manifest**: [HASH_MANIFEST_v1.4.json](./HASH_MANIFEST_v1.4.json)
