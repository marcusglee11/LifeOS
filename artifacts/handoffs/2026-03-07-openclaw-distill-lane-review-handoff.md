# OpenClaw Distill Lane Review Handoff

Review packet: `artifacts/review_packets/Review_Packet_OpenClaw_Distill_Lane_Prototype_v1.0.md`
Created: `2026-03-07T02:25:58Z`
Updated: `2026-03-08` — hardening layer committed on top of milestone-1 prototype
Base head: `8e7cdcf98c5b30a0322ced824ba3dc67327e5422`
Milestone-1 prototype: `9ffc311c`
Hardened tip: see commit SHA on `build/openclaw-distill-lane` after this commit

## What changed in the hardening layer

The committed worktree edits add an explicit hardening layer on top of the milestone-1 prototype
(`9ffc311c`). The merge target is the **hardened tip**, not 9ffc311c.

### `runtime/tools/openclaw_distill_lane.py`
- Explicit health/preflight state handling: `health_state_invalid` as a distinct bypass reason
  (previously these paths fell through implicitly)
- Compatibility fingerprint gating: active replacement is blocked when the current instance's
  fingerprint does not match the candidate; prevents silent capability regression on live instances
- Named timeout/cadence constants replacing magic numbers throughout
- Stricter canonical preflight validation: rejects distillation when preflight reports an
  unexpected/unknown state rather than silently passing it through

### `runtime/tests/test_openclaw_distill_lane.py`
- Tests for `health_state_invalid` bypass path
- Tests for fingerprint mismatch gate on active replacement
- Tests for named timeout/cadence constant values
- Tests for strict preflight state rejection

### `runtime/tests/test_coo_worktree_breakglass.py`
- Additional tests for breakglass bypass paths introduced by the hardening layer

## Review focus
- Verify the distillation lane stays bounded to the OpenClaw COO wrapper path.
- Verify deny-overrides-allow classification and protected-root handling in `runtime/tools/openclaw_distill_lane.py`.
- Verify `active` replacement is limited to `coo openclaw -- models status` and that `status --all --usage` remains shadow-only.
- Verify audit artifacts are written only under `$OPENCLAW_STATE_DIR/runtime/gates/distill/`.
- Verify the redaction helper change in `runtime/tools/coo_worktree.sh` does not regress existing wrapper behavior.
- Verify `health_state_invalid` is treated as a bypass (not a pass) across all call paths.
- Verify fingerprint mismatch correctly blocks active replacement.

## Verified evidence
- `pytest runtime/tests/test_openclaw_distill_lane.py runtime/tests/test_coo_worktree_breakglass.py -v` -> `25 passed in 5.35s`
- `pytest runtime/tests -q --deselect test_review_mission_real_v2_runtime_path_smoke` -> `2427 passed, 7 skipped, 1 deselected, 6 warnings in 587.27s`
  - Deselected: live council smoke test (pre-existing hang when all 3 CLI tools in PATH; unrelated to this branch)
- `close_build.py --dry-run --json` -> `ok: true`, targeted tests 2/2 passed

## Changed files
- `runtime/tools/coo_worktree.sh` (milestone-1, unchanged in hardening)
- `runtime/tools/openclaw_distill_lane.py` (hardened)
- `runtime/tests/test_openclaw_distill_lane.py` (hardened)
- `runtime/tests/test_coo_worktree_breakglass.py` (hardened)
