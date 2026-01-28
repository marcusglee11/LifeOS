---
artifact_id: "9d8689c1-7977-4560-84a8-6f5df9a2656d"
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-10T19:33:00+11:00"
author: "Antigravity"
version: "0.1"
status: "DRAFT"
mission_ref: "Tool_Invoke_MVP"
---

# Implement `tool_invoke` Execution Substrate (MVP) — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 0.1 |
| **Date** | 2026-01-10 |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Review |
| **Council Trigger** | None |

---

## Executive Summary

Implement a deterministic local execution substrate for `tool_invoke` operations in the LifeOS runtime. This involves creating a tool registry that dispatches requests to specialized Python handlers (filesystem, pytest) with strict policy validation and containment defense.

---

## Problem Statement

The current `tool_invoke` operation in `OperationExecutor` is a stub. To enable autonomous build loops, the runtime needs a secure, deterministic way to perform local actions like reading/writing files and running tests without exposing the entire system to accidental or malicious escape.

---

## Proposed Changes

### Tool Infrastructure

#### [NEW] [schemas.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tools/schemas.py)

Define strict request/response schemas (`ToolInvokeRequest`, `ToolInvokeResult`).

#### [NEW] [registry.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tools/registry.py)

Central dispatch logic for tools. Integrates the policy gate.

#### [NEW] [tool_policy.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/governance/tool_policy.py)

Hardcoded allowlist gate for tools/actions. Resolves sandbox root.

### Handlers

#### [NEW] [filesystem.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tools/filesystem.py)

Handlers for `read_file`, `write_file`, and `list_dir` with symlink defense.

#### [NEW] [pytest_runner.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tools/pytest_runner.py)

Pytest runner with timeout enforcement and 64KB output capping.

---

## Verification Plan

### Automated Tests

| Test | Command | Expected |
|------|---------|----------|
| Policy Gate | `pytest runtime/tests/test_tool_policy.py` | PASS (GovernanceUnavailable/PolicyDenied) |
| Filesystem | `pytest runtime/tests/test_tool_filesystem.py` | PASS (Containment/Symlink defense) |
| Integration | `pytest runtime/tests/test_tool_invoke_integration.py` | PASS (Write -> Read -> Pytest flow) |

---

## User Review Required

> [!IMPORTANT]
> **Sandbox Root Strategy**: The implementation will use the environment variable `LIFEOS_SANDBOX_ROOT` as the primary source for the sandbox root. If not set, it will fall-closed with `GovernanceUnavailable`.

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Containment | Path escape attempts via `..` or symlinks return `PolicyDenied`. |
| Determinism | `list_dir` results are sorted; hashing is stable. |
| Resilience | Unknown tools or actions fail-closed without side effects. |

---

## Non-Goals

- NO git mutation verbs (git add/commit/reset etc. are out-of-scope).
- NO external network access for tools.

---

*This plan was drafted by Antigravity under LifeOS Build Artifact Protocol v1.0.*
