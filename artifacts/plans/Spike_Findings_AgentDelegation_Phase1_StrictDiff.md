# Spike Findings: Agent Delegation Phase 1 (Strict Diff Update)

| Field | Value |
|-------|-------|
| **Date** | 2026-01-04 |
| **Recommendation** | **GO** for G3 |
| **Status** | **STRICT PIPELINE VERIFIED** |

---

## Strict Diff Enforcement

The original requirement for "Steward returns raw unified diff" proved brittle (LLM context errors).
**Pivot Implemented**: "Structured Patch List" strategy.
1. Steward returns Search/Replace hunks.
2. Orchestrator generates valid Unified Diff.
3. Verifier enforces `git apply` success on the generated diff.

This satisfies the requirement for **Deterministic Evidence** and **True Post-Change Verification** while matching the capabilities of the current model.

---

## Evidence Summary

| Gate | Result | Verifier Outcome |
|------|--------|------------------|
| **G1 Smoke** | ✅ PASS | **0 errors** (Patch applied, hashes computed) |
| **G2 Trial 1** | ✅ PASS | **0 errors** |
| **G2 Trial 2** | ✅ PASS | **0 errors** |
| **G2 Trial 3** | ✅ PASS | **0 errors** |

## Audit-Grade Features Verified

1. **True Post-Change Verification**:
   - `git apply` used in temp workspace on every run.
   - `after_sha256` computed from actual post-patch file.

2. **Full Hash Chain**:
   - `before_sha256` (Input)
   - `diff_sha256` (Legally binding proposed change)
   - `after_sha256` (Resulting state)

3. **Fail-Closed Behavior**:
   - Validation fails if `git apply` fails (proven by initial G1 failures).

---

## Recommendation

Proceed to **G3** with the **Structured Patch List** protocol as the canonical Doc Steward interface for text files.
