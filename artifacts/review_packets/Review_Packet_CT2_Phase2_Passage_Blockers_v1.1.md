---
packet_id: ct2-phase2-passage-blockers-v1.1
packet_type: REVIEW_PACKET
version: 1.1
mission_name: CT-2 Phase 2 Passage Blockers
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Review Packet: CT-2 Phase 2 Passage Blockers (v1.1)

## Summary

Closed remaining CT-2 Phase 2 passage blockers:

- **P0.2 Mock-Based CI Fail-Closed Tests**: 5 deterministic tests using `unittest.mock`
- **P0.3 Mock-Based Git-Index Symlink Tests**: 5 deterministic tests (no OS symlink needed)
- **P1.1 Strict Boundary Tests**: 5 tests with explicit `is False`/`is True` assertions
- **P1.2 Plan/Review Coherence**: Index policy committed to **explicit enumeration** (`docs/INDEX.md` only)
- **Runner.log**: Evidence bundles now include `runner.log` with truncation and hashing

## Implementation Report

### New Test Classes

| Class | Tests | Description |
|-------|-------|-------------|
| `TestCIDiffFailClosedMocked` | 5 | Mock subprocess for REFS_UNAVAILABLE, MERGE_BASE_FAILED, DIFF_EXEC_FAILED |
| `TestSymlinkGitIndexMocked` | 5 | Mock git ls-files for mode 120000 detection |
| `TestBoundaryMatchingStrict` | 5 | Strict `is False`/`is True` boundary assertions |

### Modified Files

1. `scripts/opencode_ci_runner.py` — Added log buffer and runner.log to evidence bundles
2. `tests_recursive/test_opencode_gate_policy.py` — Added 15 new behavioral tests

### Test Results

```
70 passed, 2 skipped in 0.31s
```

**Skipped**: 2 filesystem symlink tests (Windows privilege restrictions)

## Index Policy Decision

> [!IMPORTANT]
> **Policy Decision**: Explicit enumeration, NOT runtime discovery.
> 
> Writable index file: `docs/INDEX.md` only.
> 
> This is codified in `WRITABLE_INDEX_FILES` constant.

## Evidence Bundle Structure (Updated)

Each bundle now includes:

| File | Description |
|------|-------------|
| `exit_report.json` | Status, reason_code, mode, timestamp, task |
| `changed_files.json` | Parsed diff entries |
| `classification.json` | is_governance, risk_level |
| `runner.log` | Accumulated log buffer (truncated if needed) |
| `hashes.json` | SHA-256 hashes of all above files |

## DONE Definition Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| CI fail-closed proven behaviorally | ✅ | 5 mock-based tests in `TestCIDiffFailClosedMocked` |
| Git-index symlink proven deterministically | ✅ | 5 mock-based tests in `TestSymlinkGitIndexMocked` |
| PASS + BLOCK evidence bundles hashed | ✅ | 3 bundles with `hashes.json` |
| Plan/review aligns with index policy | ✅ | Explicit enumeration committed |
| Runner.log in evidence bundles | ✅ | Added to `generate_evidence_bundle()` |

## Appendix — New Mock-Based Tests

### CI Fail-Closed (Mock)

```python
def test_refs_unavailable_when_github_base_ref_missing(self, monkeypatch):
    """Missing GITHUB_BASE_REF in CI => REFS_UNAVAILABLE."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    
    cmd, mode = get_diff_command()
    
    assert cmd is None, "Command must be None when refs unavailable"
    assert mode == ReasonCode.REFS_UNAVAILABLE
```

### Git-Index Symlink (Mock)

```python
def test_git_index_symlink_mode_120000_detected(self, tmp_path):
    """Git index mode 120000 => SYMLINK_BLOCKED."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "120000 abc123def456 0\tdocs/link.md"
    
    with patch('scripts.opencode_gate_policy.subprocess.run', return_value=mock_result):
        is_sym, reason = check_symlink_git_index("docs/link.md", str(tmp_path))
        
        assert is_sym is True
        assert reason == ReasonCode.SYMLINK_BLOCKED
```

### Strict Boundary Matching

```python
def test_docsx_strictly_not_allowed(self):
    """docsx/ must STRICTLY NOT match docs/ allowlist."""
    result = matches_allowlist("docsx/test.md")
    assert result is False, "STRICT: docsx/ must return False, not truthy-falsy"
```
