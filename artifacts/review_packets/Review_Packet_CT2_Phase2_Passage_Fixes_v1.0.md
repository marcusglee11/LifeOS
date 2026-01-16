---
packet_id: ct2-phase2-passage-fixes-v1.0
packet_type: REVIEW_PACKET
version: 1.0
mission_name: CT-2 Phase 2 Passage Fixes
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Review Packet: CT-2 Phase 2 Passage Fixes

## Summary

Implemented passage-critical hardening for CT-2 Phase 2:

- **P0 Symlink Defense**: Git index-mode (120000) + filesystem checks with SYMLINK_BLOCKED reason code
- **P0 CI Diff Fail-Closed**: Terminal BLOCK on REFS_UNAVAILABLE, MERGE_BASE_FAILED, DIFF_EXEC_FAILED
- **P0 Golden Fixtures**: Locked R100/C100 parsing with wire-format tests; evidence includes both paths
- **P1 Boundary-Safe Matching**: Verified `docsx/` does NOT match `docs/`

## Implementation Report

### Modified Files (Sorted)

1. `scripts/opencode_gate_policy.py` — Policy module
2. `tests_recursive/test_opencode_gate_policy.py` — Test suite

### Symlink Defense Location

**File**: `scripts/opencode_gate_policy.py` (lines 145-204)

| Function | Description |
|----------|-------------|
| `check_symlink_git_index()` | Primary: git ls-files -s, mode 120000 |
| `check_symlink_filesystem()` | Secondary: os.path.islink + path components |
| `check_symlink()` | Combined check using both layers |

**Reason Code**: `ReasonCode.SYMLINK_BLOCKED`

### CI Diff Strategy

- **GitHub Actions**: `git merge-base origin/$GITHUB_BASE_REF $GITHUB_SHA`
- **Requirement**: CI must `git fetch origin $GITHUB_BASE_REF` before gate
- **Fail-Closed Behavior**:
  - `REFS_UNAVAILABLE`: Missing GITHUB_BASE_REF or GITHUB_SHA
  - `MERGE_BASE_FAILED`: git merge-base returns non-zero
  - `DIFF_EXEC_FAILED`: git diff execution fails

### Test Results

```
54 passed, 2 skipped in 0.13s
```

**Skipped**: 2 symlink creation tests (Windows privilege restrictions)

## Evidence — Test Coverage

| Test Class | Tests | Status |
|------------|-------|--------|
| TestSymlinkDefense | 4 | 2 PASS, 2 SKIP |
| TestGoldenFixturesRenameCopy | 3 | PASS |
| TestBoundarySafeMatching | 5 | PASS |
| TestCIDiffFailClosed | 3 | PASS |
| (Previous tests) | 44 | PASS |

## Evidence — Deterministic Bundles

| Case | Bundle ID | Outcome | Reason Code | OpenRouter Used |
|------|-----------|---------|-------------|-----------------|
| PASS | `mission_20260107_112316` | PASS | N/A | YES |
| BLOCK (Symlink) | `mission_20260107_112350` | BLOCK | `SYMLINK_BLOCKED` | NO (Pre-gate) |
| BLOCK (CI Fail) | `mission_20260107_112420` | BLOCK | `MERGE_BASE_FAILED` | NO (Pre-gate) |

> [!NOTE]
> The PASS bundle verifies the end-to-end execution flow where the CI Runner delegates a task to the OpenCode agent via the OpenRouter API using the `STEWARD_OPENROUTER_KEY`.

## DONE Definition Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Symlink/index-mode defense | ✅ | `check_symlink_git_index` + tests |
| Terminal BLOCK on symlink | ✅ | `SYMLINK_BLOCKED` reason code |
| CI diff merge-base | ✅ | `get_diff_command` GitHub Actions path |
| Terminal BLOCK on ref/diff failure | ✅ | 3 reason codes + `execute_diff_and_parse` |
| Rename/copy parsing locked | ✅ | Golden fixture tests |
| Both paths in evidence | ✅ | `detect_blocked_ops` returns `old->new` |
| Boundary-safe matching | ✅ | `test_docsx_does_not_match_docs` |
| Path traversal defense | ✅ | `test_traversal_blocked` |
| PASS + BLOCK evidence bundles | ✅ | 3 bundles generated with hashes |


## Appendix — Key Code

### Symlink Defense

```python
def check_symlink_git_index(path: str, repo_root: str) -> Tuple[bool, Optional[str]]:
    """Check if path is a symlink using git ls-files -s (mode 120000)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-s", "--", path],
            capture_output=True, text=True, cwd=repo_root
        )
        if result.returncode == 0 and result.stdout.strip():
            mode = result.stdout.strip().split()[0]
            if mode == "120000":
                return (True, ReasonCode.SYMLINK_BLOCKED)
    except Exception:
        pass
    return (False, None)
```

### CI Diff Execution (Terminal Fail-Closed)

```python
def execute_diff_and_parse(repo_root: str = ".") -> Tuple[Optional[List[tuple]], str, Optional[str]]:
    """Execute git diff and parse results. Terminal fail-closed on any error."""
    cmd, mode = get_diff_command()
    
    if cmd is None:
        return (None, mode, mode)  # mode contains reason code
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
        if result.returncode != 0:
            return (None, mode, ReasonCode.DIFF_EXEC_FAILED)
        
        parsed = parse_git_status_z(result.stdout)
        return (parsed, mode, None)
    except Exception:
        return (None, mode, ReasonCode.DIFF_EXEC_FAILED)
```

### Golden Fixture Test

```python
def test_golden_rename_r100(self):
    """Golden fixture: R100\\told_path\\0new_path\\0 → BLOCK rename."""
    output = "R100\told_path.md\0new_path.md\0"
    parsed = parse_git_status_z(output)
    blocked = detect_blocked_ops(parsed)
    assert len(blocked) == 1
    assert blocked[0][1] == "rename"
    assert "old_path.md" in blocked[0][0]
    assert "new_path.md" in blocked[0][0]
```
