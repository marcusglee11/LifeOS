# Filesystem Error Boundary Protocol v1.0

**Status:** Draft
**Version:** 1.0
**Last Updated:** 2026-01-29

---

## Purpose

Define fail-closed boundaries for filesystem operations across LifeOS runtime. Ensures deterministic error handling and prevents silent failures.

## Principle: Fail-Closed by Default

All filesystem operations MUST wrap OS-level errors into domain-specific exceptions. Never let `OSError`, `IOError`, or `JSONDecodeError` propagate to callers without context.

**Rationale:**
- **Determinism:** Filesystem errors are environmental; wrapping makes them testable
- **Auditability:** Domain exceptions carry context for debugging
- **Fail-closed:** Explicit error boundaries prevent silent failures

---

## Standard Pattern

```python
try:
    # Filesystem operation
    with open(path, 'r') as f:
        content = f.read()
except OSError as e:
    raise DomainSpecificError(f"Failed to read {path}: {e}")
except json.JSONDecodeError as e:
    raise DomainSpecificError(f"Invalid JSON in {path}: {e}")
```

---

## Exception Mapping Table

| Module | Domain Exception | Wraps | Purpose |
|--------|------------------|-------|---------|
| `runtime/tools/filesystem.py` | `ToolErrorType.IO_ERROR` | `OSError`, `UnicodeDecodeError` | Agent tool invocations |
| `runtime/state_store.py` | `StateStoreError` | `OSError`, `JSONDecodeError` | Runtime state persistence |
| `runtime/orchestration/run_controller.py` | `GitCommandError` | `OSError`, subprocess errors | Git command failures |
| `runtime/orchestration/loop/ledger.py` | `LedgerIntegrityError` | `OSError`, `JSONDecodeError` | Build loop ledger corruption |
| `runtime/governance/policy_loader.py` | `PolicyLoadError` | `OSError`, `JSONDecodeError`, YAML errors | Policy config loading |

---

## Error Type Taxonomy

| Error Type | Meaning | Recovery Strategy |
|------------|---------|-------------------|
| `NOT_FOUND` | File/directory does not exist | Caller decides (retry/fail/skip) |
| `IO_ERROR` | OSError other than NOT_FOUND | Always fail (I/O error unrecoverable) |
| `ENCODING_ERROR` | File is not valid UTF-8 | Always fail (data corruption signal) |
| `PERMISSION_ERROR` | Permission denied (PermissionError) | Always fail (security boundary) |
| `CONTAINMENT_VIOLATION` | Path escapes sandbox | Always fail (security boundary) |
| `SCHEMA_ERROR` | Missing required arguments | Always fail (caller bug) |

---

## Module-Specific Boundaries

### runtime/tools/filesystem.py
- **Pattern:** Returns `ToolInvokeResult` with `ToolError` (never raises)
- **Coverage:** read_file, write_file, list_dir
- **Guarantees:** All OSError wrapped in IO_ERROR, UTF-8 enforced

### runtime/state_store.py
- **Pattern:** Raises `StateStoreError` on filesystem/JSON errors
- **Coverage:** read_state, write_state, create_snapshot
- **Guarantees:** No OSError/JSONDecodeError propagates

### runtime/orchestration/run_controller.py
- **Pattern:** Raises `GitCommandError` on git failures
- **Coverage:** run_git_command, verify_repo_clean
- **Guarantees:** Git errors halt execution (fail-closed)

### runtime/orchestration/loop/ledger.py
- **Pattern:** Raises `LedgerIntegrityError` on corruption
- **Coverage:** hydrate (read), append (write)
- **Guarantees:** Ledger corruption halts build loop

---

## Compliance Checklist

When adding new filesystem operations:

- [ ] Wrap all `open()`, `Path.read_text()`, `Path.write_text()` in try/except
- [ ] Catch `OSError`, `UnicodeDecodeError`, `JSONDecodeError` as appropriate
- [ ] Raise domain-specific exception with context (file path, operation, root cause)
- [ ] Document fail-closed boundary in module docstring
- [ ] Add tests for error paths (mock OSError, verify exception raised)

---

## References

- LifeOS Constitution v2.0 § Fail-Closed Principle
- Tool Invoke Protocol MVP v0.2
- Autonomous Build Loop Architecture v0.3 § Safety Checks
