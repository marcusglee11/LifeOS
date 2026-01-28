---
artifact_id: "9d8689c1-7977-4560-84a8-6f5df9a2656d"
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-10T19:33:00+11:00"
updated_at: "2026-01-10T19:53:00+11:00"
author: "Antigravity"
version: "0.2"
status: "DRAFT"
mission_ref: "Tool_Invoke_MVP"
---

# Implement `tool_invoke` Execution Substrate (MVP) — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 0.2 |
| **Date** | 2026-01-10 |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Approval |
| **Council Trigger** | None |

---

## Executive Summary

Implement a deterministic local execution substrate for `tool_invoke` operations in the LifeOS runtime. This involves creating a tool registry that dispatches requests to specialized Python handlers (filesystem, pytest) with strict policy validation and containment defense.

---

## Problem Statement

The current `tool_invoke` operation in `OperationExecutor` is a stub. To enable autonomous build loops, the runtime needs a secure, deterministic way to perform local actions like reading/writing files and running tests without exposing the entire system to accidental or malicious escape.

---

## Schema Lock-In (Blocker Fix #1)

All `ToolInvokeResult` objects **MUST** include:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `timestamp_utc` | `str` | Yes | ISO 8601 format |
| `ok` | `bool` | Yes | Success indicator |
| `tool` | `str` | Yes | Tool name |
| `action` | `str` | Yes | Action name |
| `policy.allowed` | `bool` | Yes | Gate decision |
| `output.truncated` | `bool` | Yes | True if output exceeded cap |

File effects **MUST** use:

| Field | Type | Notes |
|-------|------|-------|
| `size_bytes` | `int` | NOT `bytes` |
| `sha256` | `str` | Full hash, no truncation |

**Output cap policy**: 64KB combined stdout+stderr. If exceeded, `output.truncated=true`.

---

## Root Canonicalization (Blocker Fix #2)

**Invariant**: Sandbox root must be canonical at config time.

```python
def resolve_sandbox_root() -> Path:
    raw = os.environ.get("LIFEOS_SANDBOX_ROOT")
    if not raw:
        raise GovernanceUnavailable("LIFEOS_SANDBOX_ROOT not set")
    
    root = Path(raw).resolve()  # realpath canonicalization
    
    if not root.exists():
        raise GovernanceUnavailable(f"Sandbox root does not exist: {root}")
    if not root.is_dir():
        raise GovernanceUnavailable(f"Sandbox root is not a directory: {root}")
    
    return root  # Already canonical via resolve()
```

All path containment checks compare `realpath(target)` against `realpath(root) + os.sep`.

---

## Binary/Non-UTF8 Policy (Important Fix #1)

**Decision**: Fail-closed with `EncodingError` on UTF-8 decode failure.

- `read_file` attempts UTF-8 decode
- If decode fails → `ok=false`, `error.type="EncodingError"`
- No base64 fallback in MVP

---

## Pytest Parsing Constraint (Important Fix #2)

**Decision**: Minimal structured output only. No partial parsing.

Return only:

- `exit_code: int`
- `stdout: str`
- `stderr: str`
- `duration_ms: int`
- `cmd: list[str]`
- `truncated: bool`

Do NOT attempt to parse test counts, names, or results from stdout.

---

## Proposed Changes

### Phase A: Infrastructure (in order)

1. **Schemas**: `runtime/tools/schemas.py`
2. **Policy Gate**: `runtime/governance/tool_policy.py`
3. **Registry**: `runtime/tools/registry.py`

### Phase B: Handlers

1. **Filesystem**: `runtime/tools/filesystem.py`
2. **Pytest**: `runtime/tools/pytest_runner.py`

### Phase C: Integration

1. **Engine**: Update `runtime/orchestration/operations.py`

---

## Test Coverage (Important Fix #3)

| Test File | Cases |
|-----------|-------|
| `runtime/tests/test_tool_policy.py` | Allowed tool/action; denied unknown; `GovernanceUnavailable` when root missing/not-dir/symlink |
| `runtime/tests/test_tool_filesystem.py` | `read_file` success; `NotFound`; `EncodingError` (binary); `write_file` success; empty content (0 bytes); `list_dir` sorted; `..` escape → `PolicyDenied` + no side effects; symlink escape blocked |
| `runtime/tests/test_pytest_runner.py` | Success; failure; timeout (5s + hanging fixture); output truncation |
| `runtime/tests/test_tool_invoke_integration.py` | Golden workflow: write → read (hash match) → pytest |

---

## Evidence Report Deliverable

**Path**: `artifacts/TEST_REPORT_TOOL_INVOKE_MVP.md`

**Required Contents**:

- Files added/modified (deterministic order)
- Test commands + raw output
- Schema verification proof
- Containment test results
- Truncation cap configuration

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Containment | `..` and symlink escapes return `PolicyDenied` with no side effects |
| Determinism | `list_dir` sorted; hashing stable |
| Fail-Closed | Unknown tool/action denied; missing root → `GovernanceUnavailable` |
| Schema | All results include `timestamp_utc`, `output.truncated`, `size_bytes` |

---

## Non-Goals

- NO git mutation verbs
- NO external network access
- NO base64 encoding for binary files

---

*This plan was drafted by Antigravity under LifeOS Build Artifact Protocol v1.0.*
