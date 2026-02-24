# Handoff Pack: Phase C Council Dogfood + Review Fixes

## Metadata
- Branch: `build/council-process-fixes`
- Base: `main` (`cb6b7fc`)
- Fix commit: `c74e449`
- Scope: Phase C receipts hardening after paid-Zen council dogfood + independent review

## Paid Zen Council Dogfood Execution

## Run mode
- Runtime: `CouncilFSM` (state-machine council path)
- Policy: `config/policy/council_policy.yaml`
- Model path: paid Zen, explicit `claude-sonnet-4-5` seat overrides
- Key source used for run: `/mnt/c/Users/cabra/Projects/LifeOS/.env`

## Outcomes
1. First run blocked at S0 due invalid CCP enum values in `touches` (`runtime/scripts/receipts`), proving fail-closed policy gate behavior.
2. Rerun with policy-valid touches (`runtime_core/interfaces/tests`) completed:
   - status: `complete`
   - verdict: `Revise`
   - mode: `M2_FULL`
   - topology: `HYBRID`
   - seat completion: `11/11`

## Council synthesis themes
- Requested additional hardening in fail-closed and reconciliation flows.
- Majority seat verdict `Revise` (10/11), with one `Accept`.
- A number of seat suggestions were assumption-heavy and not all were directly grounded in current code.

## Independent Review Findings (Implemented)
1. `LAND_RECEIPT_SCHEMA` did not require `tree_equivalence` despite Phase C contract.
2. `run_post_merge_land_gate()` allowed land emission from non-`ACCEPTED` acceptance receipts.
3. `ReceiptStore.rebuild_index()` omitted land receipts, breaking recovery/query correctness.
4. `query_land_receipts_for_workspace(..., plan_core_sha256=...)` ignored the filter argument.
5. Reconciliation treated malformed `tree_equivalence.match` values as compliant instead of fail-closed.

## Changes Implemented
- `runtime/receipts/schemas.py`
  - Added `tree_equivalence` to required fields in `LAND_RECEIPT_SCHEMA`.
- `runtime/receipts/post_merge.py`
  - Added acceptance decision enforcement (`ACCEPTED` required) with `ACCEPTANCE_NOT_ACCEPTED` failure code.
- `runtime/receipts/store.py`
  - Implemented `plan_core_sha256` filtering in `query_land_receipts_for_workspace()`.
  - Added land receipt recovery entries to `rebuild_index()`.
- `runtime/receipts/reconciliation.py`
  - Added mode validation (`audit|alert|enforce`).
  - Switched to fail-closed classification: only `match is True` => compliant; missing/invalid => violation.
- `runtime/tests/receipts/test_phase_c.py`
  - Added schema-required assertion for `tree_equivalence`.
  - Added post-merge gate test for non-accepted receipt rejection.
  - Added reconciliation tests for invalid mode and malformed `tree_equivalence` handling.
- `runtime/tests/receipts/test_store.py`
  - Added regression tests for land receipt index rebuild recovery.
  - Added regression test for `plan_core_sha256` filter behavior.

## Validation Evidence

## Targeted tests
- Command:
  - `pytest runtime/tests/receipts/test_phase_c.py runtime/tests/receipts/test_store.py runtime/tests/receipts/test_schemas.py -q`
- Result:
  - `62 passed`

## Full suite
- Command:
  - `pytest runtime/tests -q`
- Result:
  - `1980 passed, 10 skipped, 6 warnings`

## Commit
- `c74e449 fix(receipts): harden phase c land gate and recovery semantics`

## PR Readiness
- Branch contains a single focused fix commit on top of `main`.
- Worktree is clean.
- Tests are green.
