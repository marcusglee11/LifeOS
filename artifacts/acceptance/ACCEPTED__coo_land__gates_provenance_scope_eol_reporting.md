# ACCEPTED - coo land gates (provenance/scope/eol/reporting)

- main HEAD: 5954f235f2a2f1a73236fadaeb06a6cad9b5e17b
- Change summary:
  - Added coo land fail-closed workflow in runtime/tools/coo_worktree.sh.
  - Added deterministic allowlist and EOL policy helper in runtime/tools/coo_land_policy.py.
  - Enforced evidence-derived scope gate from worktree_diff_name_only.txt with sorted allowlist hashing.
  - Enforced EOL-only blocking by default, override with --allow-eol-only.
  - Routed REPORT_BLOCKED__coo_land__*.md outputs into selected EVID directory.
  - Emitted deterministic land_receipt.txt with baseline/source/destination and clean proofs.
  - Micro-tighten applied in b157150: EVID_SELECTED line in receipt and block-symmetry assertions.
- Evidence example dir:
  - artifacts/evidence/openclaw/jobs/20260209T143426Z/sample_land_success
- Verification summary:
  - pytest -q runtime/tests/test_coo_land_policy.py runtime/tests/test_coo_land_integration.py runtime/tests/test_coo_capsule_render.py passed.
- EMERGENCY_USED=0
