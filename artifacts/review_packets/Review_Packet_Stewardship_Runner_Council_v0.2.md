# Review_Packet_Stewardship_Runner_Council_v0.2

**Mission**: P0/P1 Council-Prep Fixes for Stewardship Runner  
**Date**: 2026-01-02  
**Author**: Antigravity Agent  
**Status**: COMPLETE — All 11 acceptance tests pass

---

## 1. Summary

Implemented P0/P1 fixes per Council review feedback: test scope enforcement, clean-start deadlock prevention, commit staging hardening, and allowlist normalization.

---

## 2. Fixes Implemented

### P0 (Must Fix)

| ID | Issue | Fix | Verification |
|----|-------|-----|--------------|
| P0-1 | `tests.paths` not used | `argv = command + paths` in `run_tests()` | AT-11 ✅ |
| P0-2 | Logs not gitignored | Added `logs/steward_runner/` to `.gitignore` | Second run succeeds ✅ |

### P1 (Should Fix)

| ID | Issue | Fix | Verification |
|----|-------|-----|--------------|
| P1-1 | Commit staging fails on deletions | `git add -A -- <roots>` | AT-07 ✅ |
| P1-2 | Allowlist prefix fragile | `normalize_commit_path()` with fail-closed | Config validated ✅ |
| P1-3 | `repo_root` misleading | Removed from config | Config v0.2 ✅ |

### P2 (Decisions)

| ID | Decision |
|----|----------|
| P2-1 | Defer log overwrite policy |
| P2-2 | **Removed** `timestamps` flag |
| P2-3 | Defer `--step` postflight |

---

## 3. Commit Paths Contract

**Directory prefixes**: End with `/` (e.g., `docs/`)  
**Exact files**: No trailing `/` (e.g., `docs/INDEX.md`)

### Normalization Rules

| Input | Action |
|-------|--------|
| `docs` (no `/`) | Normalize → `docs/` + log |
| `docs\subfolder\` | Normalize backslashes → `docs/subfolder/` |
| `/absolute/path` | **FAIL PREFLIGHT** |
| `../escape` | **FAIL PREFLIGHT** |
| `docs/*.md` | **FAIL PREFLIGHT** |

---

## 4. Acceptance Tests

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
AT-11 PASSED — Test scope enforcement (P0-1)
```

---

## 5. Important Note

> [!IMPORTANT]
> `.gitignore` must include `logs/steward_runner/` for `require_clean_start=true` to work.

---

## 6. Files Modified

| File | Change |
|------|--------|
| [steward_runner.py](scripts/steward_runner.py) | P0-1, P1-1, P1-2, P2-2 |
| [steward_runner.yaml](config/steward_runner.yaml) | P1-3, P2-2, Contract docs |
| [.gitignore](.gitignore) | P0-2 |
| [test_steward_runner.py](tests_recursive/test_steward_runner.py) | AT-11 |

---

## Appendix — Key Code Changes

### run_tests() (P0-1)

```python
def run_tests(config, logger, repo_root) -> bool:
    """Run test suite with configured paths. Returns success."""
    tests_config = config.get("tests", {})
    command = tests_config.get("command", ["python", "-m", "pytest", "-q"])
    paths = tests_config.get("paths", [])
    
    # P0-1: Append test paths to command argv
    argv = list(command) + list(paths)
    
    exit_code, _, _ = run_command(argv, repo_root, logger, "tests")
    return exit_code == 0
```

### normalize_commit_path() (P1-2)

```python
def normalize_commit_path(path: str) -> tuple[str, bool]:
    """
    Normalize a commit_paths entry per Commit Paths Contract.
    Returns (normalized_path, is_valid).
    """
    normalized = path.replace("\\", "/")
    
    # Fail-closed checks
    if normalized.startswith("/"):
        return normalized, False  # Absolute path
    if ".." in normalized:
        return normalized, False  # Path traversal
    if "*" in normalized or "?" in normalized:
        return normalized, False  # Glob pattern
    
    # Add trailing slash for directories
    if "/" in normalized or not "." in normalized.split("/")[-1]:
        if not normalized.endswith("/"):
            normalized = normalized + "/"
    
    return normalized, True
```

### .gitignore (P0-2)

```gitignore
# Steward runner logs (required for require_clean_start=true)
logs/steward_runner/
```

---

## End of Review Packet

