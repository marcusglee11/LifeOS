# Review_Packet_Stewardship_Runner_Council_v0.3

**Mission**: Council-Prep Fixes (P0/P1) + Allowlist Normalization Hardening  
**Date**: 2026-01-02  
**Author**: Antigravity Agent  
**Status**: COMPLETE — All 20 acceptance tests pass

---

## 1. Summary

Implemented all P0/P1 fixes plus hardened allowlist normalization per Council review feedback.

---

## 2. Fixes Implemented

### P0 (Must Fix)

| ID | Issue | Fix | Verification |
|----|-------|-----|--------------|
| P0-1 | `tests.paths` not used | `argv = command + paths` | AT-11 ✅ |
| P0-2 | Logs not gitignored | Added to `.gitignore` | Clean-start ✅ |

### P1 (Should Fix)

| ID | Issue | Fix | Verification |
|----|-------|-----|--------------|
| P1-1 | Commit staging fails on deletions | `git add -A -- <roots>` | AT-07 ✅ |
| P1-2 | Allowlist prefix fragile | `normalize_commit_path()` hardened | AT-12, AT-13 ✅ |
| P1-3 | `repo_root` misleading | Removed from config | Config v0.2 ✅ |
| **NEW** | Exact-file normalization bug | Only bare names get `/` | AT-12 ✅ |
| **NEW** | Windows absolute paths | Detect `C:\`, `\\server` | AT-13 ✅ |
| **NEW** | Segment-based `..` check | Split and check each segment | AT-13 ✅ |

---

## 3. Commit Paths Contract

**Directory prefixes**: End with `/` (e.g., `docs/`)  
**Exact files**: No trailing `/` (e.g., `docs/INDEX.md`)  
**Bare names**: Normalized to directory if no `.` (e.g., `docs` → `docs/`)

### Fail-Closed Cases

| Pattern | Error Reason |
|---------|--------------|
| `//server/share/` | `absolute_path_unc` |
| `/absolute/path/` | `absolute_path_unix` |
| `C:/temp/` | `absolute_path_windows` |
| `../docs/` | `path_traversal` |
| `docs/../other/` | `path_traversal` |
| `docs/*.md` | `glob_pattern` |
| `./docs/` | `current_dir_segment` |

### Staging Roots Derivation

From `commit_paths: ["docs/", "docs/INDEX.md"]`:
- `docs/` → root `docs/`
- `docs/INDEX.md` → root `docs/INDEX.md`
- `git add -A -- docs/ docs/INDEX.md`

---

## 4. Acceptance Tests (20 total)

```
AT-01 PASSED — Missing run-id fails
AT-02 PASSED — Dirty repo fails
AT-03 PASSED — Tests failure blocks downstream
AT-04 PASSED — Validator failure blocks corpus
AT-05 PASSED — Corpus outputs enforced
AT-06 PASSED — No change = no commit
AT-07 PASSED — Allowed changes commit
AT-08 PASSED — Disallowed changes fail
AT-09 PASSED — Dry run never commits
AT-10 PASSED — Log determinism
AT-11 PASSED — Test scope enforcement
AT-12 PASSED — Allowlist normalization (bare → dir/)
AT-13 PASSED — Fail-closed unsafe paths (8 parametrized cases)
```

---

## 5. Important Notes

> [!IMPORTANT]
> `.gitignore` must include `logs/steward_runner/` for `require_clean_start=true`.

> [!NOTE]
> UNC paths (`//server`) must be checked before Unix absolute (`/`) since `//` starts with `/`.

---

## 6. Files Modified

| File | Lines | Change |
|------|-------|--------|
| `scripts/steward_runner.py` | 670 | Core fixes, normalization hardening |
| `config/steward_runner.yaml` | 52 | Removed repo_root/timestamps, added contract docs |
| `.gitignore` | 7 | Added steward logs |
| `tests_recursive/test_steward_runner.py` | 675 | AT-11, AT-12, AT-13 |

---

## Appendix — Key Code

### normalize_commit_path() (Final)

```python
def normalize_commit_path(path: str) -> tuple[str, str | None]:
    """
    Normalize a commit_paths entry per Commit Paths Contract.
    Returns (normalized_path, error_reason | None).
    """
    normalized = path.replace("\\", "/")
    
    # UNC path - check BEFORE Unix (// starts with /)
    if normalized.startswith("//"):
        return normalized, "absolute_path_unc"
    
    # Unix absolute path
    if normalized.startswith("/"):
        return normalized, "absolute_path_unix"
    
    # Windows drive absolute (C:/ or C:)
    if len(normalized) >= 2 and normalized[1] == ":":
        return normalized, "absolute_path_windows"
    
    # Glob patterns
    if "*" in normalized or "?" in normalized:
        return normalized, "glob_pattern"
    
    # Segment-based path traversal and current-dir check
    segments = normalized.rstrip("/").split("/")
    for segment in segments:
        if segment == "..":
            return normalized, "path_traversal"
        if segment == ".":
            return normalized, "current_dir_segment"
    
    # Only normalize bare names (no / at all) that look like directories
    if "/" not in path and not path.endswith("/"):
        if "." not in path:
            normalized = normalized + "/"
    
    return normalized, None
```

---

## End of Review Packet
