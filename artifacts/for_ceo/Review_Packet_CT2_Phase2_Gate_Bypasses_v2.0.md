---
packet_id: ct2-phase2-gate-bypasses-v2.0
packet_type: REVIEW_PACKET
version: 2.0
mission_name: CT-2 Phase 2 Gate Bypasses Closure
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Review Packet: CT-2 Phase 2 Gate Bypasses Closure (v2.0)

## Summary

Closed all gate bypasses for CT-2 Phase 2:

- **P0.1 Overrides Removed**: `--override-foundations` flag deleted; denylist is terminal with no bypass
- **P0.2 Post-Diff Envelope Enforcement**: All diff entries validated against envelope
- **P0.3 Runner-Level Tests**: 15 tests proving no bypass
- **No Delete Action**: Task JSON only accepts `create`/`modify`

## Implementation Report

### Key Changes

| Component | Change |
|-----------|--------|
| `opencode_ci_runner.py` | Recreated v2.0: no override flags, post-diff envelope validation |
| `opencode_gate_policy.py` | Added `OUTSIDE_ALLOWLIST_BLOCKED` reason code |
| `test_opencode_gate_policy.py` | Added 15 `TestRunnerEnvelopeEnforcement` tests |

### Envelope Validation Order (Per Diff Entry)

1. **Blocked Operations**: D/R/C → Terminal BLOCK
2. **Denylist-First**: `matches_denylist()` → Terminal BLOCK
3. **Allowlist**: `matches_allowlist()` → OUTSIDE_ALLOWLIST_BLOCKED
4. **Extension under docs/**: `.md` only → NON_MD_EXTENSION_BLOCKED
5. **Review Packets**: Add-only .md → REVIEW_PACKET_NOT_ADD_ONLY / NON_MD_IN_REVIEW_PACKETS

### Test Results

```
84 passed, 2 skipped in 0.42s
```

## DONE Definition Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| No override flags exist | ✅ | No `--override-foundations` in runner |
| Denylist is terminal with no bypass | ✅ | `validate_diff_entry` blocks on denylist first |
| Post-diff validated: denylist-first | ✅ | `test_denylisted_*_blocked` tests |
| Post-diff validated: allowlist enforced | ✅ | `test_outside_allowlist_blocked` |
| Post-diff validated: docs .md-only | ✅ | `test_non_md_under_docs_blocked`, `test_yaml_under_docs_blocked` |
| Post-diff validated: review_packets add-only | ✅ | `test_review_packets_*_blocked` tests |
| Runner blocks on any out-of-envelope change | ✅ | `validate_all_diff_entries()` in main() |
| Deterministic tests prove the above | ✅ | 15 tests in `TestRunnerEnvelopeEnforcement` |

## Appendix — Key Code

### validate_diff_entry

```python
def validate_diff_entry(status: str, path: str, old_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Validate a single diff entry against Phase 2 envelope."""
    norm_path = policy.normalize_path(path)
    
    # 1. Blocked operations (D/R/C)
    if status == "D":
        return (False, ReasonCode.PH2_DELETE_BLOCKED)
    if status.startswith("R"):
        return (False, ReasonCode.PH2_RENAME_BLOCKED)
    if status.startswith("C"):
        return (False, ReasonCode.PH2_COPY_BLOCKED)
    
    # 2. Denylist-first (terminal, no bypass)
    is_denied, deny_reason = policy.matches_denylist(norm_path)
    if is_denied:
        return (False, deny_reason)
    
    # 3. Allowlist check
    if not policy.matches_allowlist(norm_path):
        return (False, ReasonCode.OUTSIDE_ALLOWLIST_BLOCKED)
    
    # 4. Extension check under docs/
    ext_ok, ext_reason = policy.check_extension_under_docs(norm_path)
    if not ext_ok:
        return (False, ext_reason)
    
    # 5. Review packets: add-only .md
    if norm_path.startswith("artifacts/review_packets/"):
        if status != "A":
            return (False, ReasonCode.REVIEW_PACKET_NOT_ADD_ONLY)
        if not norm_path.endswith(".md"):
            return (False, ReasonCode.NON_MD_IN_REVIEW_PACKETS)
    
    return (True, None)
```

### Runner Main Loop (Post-Diff Validation)

```python
# Validate ALL diff entries against envelope
blocked_entries = validate_all_diff_entries(parsed)

if blocked_entries:
    first_block = blocked_entries[0]
    generate_evidence_bundle("BLOCK", first_block[2], mode, task, parsed, blocked_entries)
    log(f"Envelope violation: {first_block[0]} ({first_block[1]}) - {first_block[2]}", "error")
    subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
    sys.exit(1)
```
