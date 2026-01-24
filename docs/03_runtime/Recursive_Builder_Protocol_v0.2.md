# Recursive Builder Protocol

**Version:** v0.2
**Status:** Protocol
**Date:** 2026-01-23

## 1. Overview

This protocol defines the binding invariants for the Recursive Builder Integration in Autonomous Mode.

## 2. Binding Invariants

These invariants are canonical for the execution-grade capability of the recursive runner.

### C1) One-Item Blast Radius (Default)

In autonomous mode, the runner defaults to processing exactly **ONE** backlog item per invocation. Multi-item processing requires an explicit, hard-capped batching flag.

### C2) Dry-Run Has Zero Side Effects

The `--dry-run` flag **MUST NOT**:

- Dispatch missions.
- Write artifacts.
- Mutate the backlog.

### C3) Fail-Closed Outcome Handling

Any unknown, ambiguous, or malformed mission result shape:

- Triggers a **BLOCKED** outcome.
- Leaves the backlog **UNCHANGED**.
- **MUST** emit a `BLOCKED` artifact containing the raw result/error.

### C4) Backlog Mutation Guarded by Evidence Contract

The backlog item may be marked `DONE` **ONLY** when the evidence contract is satisfied:

- `success == True`
- `terminal_outcome == "PASS"` (Explicit string match)
- Provenance fields (commit hash, etc.) are present.

If the contract is not satisfied, the runner **MUST NOT** mutate the backlog and must BLOCK or emit an artifact.

### C5) Artifact Provenance (Closure-Grade Minimum)

Emitted `WAIVER_REQUESTED`, `ESCALATION_REQUESTED`, and `BLOCKED` artifacts **MUST** include:

- **Identity:** `run_id`, `timestamp`, `item_key`, `item_title`.
- **Context:** `baseline_commit`, `backlog_path` (repo-relative).
- **Result:** `normalized_result` (with explicit outcome fields).
- **Paths:** All paths mapping to files must be **repo-relative** (no absolute `file:///` URIs).

## 3. Reference Implementation

- **Runner:** `recursive_kernel/runner.py`
- **Evidence Bundle:** `artifacts/closures/Recursive_Builder_Integration_Bundle_v0.4.zip`
