---
packet_id: ct2-phase2-passage-v2.1
packet_type: REVIEW_PACKET
version: 2.1
mission_name: CT-2 Phase 2 Passage v2.1 Fixes
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Review Packet: CT-2 Phase 2 Passage v2.1 Fixes

## Summary

Implemented passage-critical fixes for v2.1:

- **P0.1 Truncation Footer**: Already well-formed (no ellipses)
- **P0.3 Symlink Fail-Closed**: `check_symlink_git_index()` now BLOCKs on exception/nonzero
- **P1.2 Determinism**: `changed_files.json` sorted by normalized path

## Implementation Report

### Key Changes

| Component | Change |
|-----------|--------|
| `opencode_gate_policy.py` | Added `SYMLINK_CHECK_FAILED` reason code; symlink check now fail-closed |
| `opencode_ci_runner.py` | Sorted `changed_files.json` for deterministic output |
| `test_opencode_gate_policy.py` | Updated symlink tests; added nonzero return test |

### Symlink Fail-Closed Behavior

```python
def check_symlink_git_index(path, repo_root):
    try:
        result = subprocess.run(["git", "ls-files", "-s", "--", path], ...)
        # Fail-closed: nonzero return code means we cannot verify
        if result.returncode != 0:
            return (True, ReasonCode.SYMLINK_CHECK_FAILED)
        # Check mode 120000 for symlink
        ...
    except Exception:
        # Fail-closed: exception means we cannot verify
        return (True, ReasonCode.SYMLINK_CHECK_FAILED)
```

### Test Results

```
85 passed, 2 skipped in 0.50s
```

## DONE Definition Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Truncation footer well-formed | ✅ | Already explicit with `cap_lines=`, `cap_bytes=` |
| No ellipses in footer | ✅ | Format uses proper formatting |
| Symlink fail-closed on exception | ✅ | `test_git_index_exception_blocks_fail_closed` |
| Symlink fail-closed on nonzero | ✅ | `test_git_index_nonzero_return_blocks_fail_closed` |
| changed_files.json sorted | ✅ | Sorted by `normalize_path()` |

## Appendix — New Test Cases

### Symlink Fail-Closed Tests

```python
def test_git_index_exception_blocks_fail_closed(self, tmp_path):
    """Exception during git ls-files => BLOCK with SYMLINK_CHECK_FAILED."""
    with patch('scripts.opencode_gate_policy.subprocess.run', side_effect=Exception("Git not available")):
        is_sym, reason = check_symlink_git_index("docs/file.md", str(tmp_path))
        assert is_sym is True, "Exception must trigger BLOCK (fail-closed)"
        assert reason == ReasonCode.SYMLINK_CHECK_FAILED

def test_git_index_nonzero_return_blocks_fail_closed(self, tmp_path):
    """Nonzero return code from git ls-files => BLOCK with SYMLINK_CHECK_FAILED."""
    mock_result = MagicMock()
    mock_result.returncode = 128
    with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result):
        is_sym, reason = check_symlink_git_index("docs/file.md", str(tmp_path))
        assert is_sym is True
        assert reason == ReasonCode.SYMLINK_CHECK_FAILED
```
