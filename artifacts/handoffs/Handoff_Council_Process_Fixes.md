# Handoff Pack: Council Process Fixes

## Metadata
- Branch: build/council-process-fixes
- Base: main (HEAD at branch creation)
- Scope: council seat output schema compatibility + prompt/schema alignment

## Problem Summary
Live council dogfood runs were frequently blocked by schema-gate mismatches because seat outputs used legacy verdict text "Go with Fixes" while policy/schema required "Revise".

## Changes Implemented
1. Added backward-compatible verdict alias normalization in schema gate:
   - "Go with Fixes" -> "Revise"
   - Applies to:
     - seat "verdict"
     - v2 "verdict_recommendation"
     - v2 synthesis "verdict"
   - Emits warning when alias normalization is used.

2. Updated council role prompts to canonical verdict enum:
   - "Accept | Revise | Reject"
   - Removed legacy "Go with Fixes" wording.

3. Added regression tests:
   - Seat schema gate normalizes legacy verdict alias.
   - Lens review schema gate normalizes legacy verdict alias.
   - Synthesis schema gate normalizes legacy verdict alias.

## Files Changed
- config/agent_roles/council_reviewer.md
- config/agent_roles/council_reviewer_security.md
- runtime/orchestration/council/schema_gate.py
- runtime/tests/orchestration/council/test_schema_gate.py
- runtime/tests/orchestration/council/test_schema_gate_v2.py

## Validation Evidence
### Baseline (Before Changes)
- Command: pytest runtime/tests -q
- Result: 1833 passed, 11 skipped, 6 warnings

### Targeted Tests
- Command: pytest runtime/tests/orchestration/council/test_schema_gate.py runtime/tests/orchestration/council/test_schema_gate_v2.py -q
- Result: 24 passed

### Post-Change Full Suite
- Command: pytest runtime/tests -q
- Result: 1835 passed, 12 skipped, 6 warnings

## Risk Assessment
- Low runtime risk: change is additive and compatibility-focused, while preserving strict enum checks after normalization.
- Expected behavior improvement: fewer false schema rejections in live council runs.

## Merge Notes
- Branch is isolated and contains only council process hardening updates plus tests.
- Ready for PR.
