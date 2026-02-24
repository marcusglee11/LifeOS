# Handoff Pack: Council Evidence-Grounding Hardening

## Metadata
- Branch: `build/council-process-fixes`
- Base: `main` (`cb6b7fc`)
- Commits:
  - `b213eca` `fix(council): enforce evidence-grounded seat outputs`
  - `71de232` `chore(council): add grounding preflight to reviewer prompts`

## Objective
Reduce council review noise from speculative/model-drift outputs by hardening process + prompts so quality is constrained by model performance, not permissive validation.

## What Was Changed

## 1) Fail-closed schema gate hardening
- File: `runtime/orchestration/council/schema_gate.py`
- Removed silent auto-labeling of uncited claims.
- Added explicit claim grounding validation for `key_findings`, `risks`, and `fixes`:
  - each claim must include citation (`REF:` or `CWE-`) OR assumption tag (`[ASSUMPTION]`)
  - non-grounded claims are schema errors (not warnings)
- Added assumption-quality checks:
  - configurable max assumption ratio
  - `Accept` verdict requires citation dominance
  - assumption-backed claims require non-empty `assumptions` section

## 2) Policy controls for quality floor
- Files:
  - `config/policy/council_policy.yaml`
  - `runtime/orchestration/council/policy.py`
- Added schema gate controls:
  - `require_explicit_claim_grounding: true`
  - `max_assumption_ratio: 0.34`
  - `accept_requires_ref_balance: true`

## 3) Prompt contract tightening
- Files:
  - `config/agent_roles/council_reviewer.md`
  - `config/agent_roles/council_reviewer_security.md`
- Added preflight instructions requiring all claim bullets to contain grounding tokens before output.
- Tightened wording to avoid speculative/non-CCP component claims.
- Clarified that `Accept` requires evidence-backed dominance and insufficient evidence should default to `Revise`.

## 4) Test updates for strict grounding behavior
- Files:
  - `runtime/tests/orchestration/council/test_schema_gate.py`
  - `runtime/tests/orchestration/council/test_fsm.py`
  - `runtime/tests/orchestration/council/test_council_dogfood_mock.py`
- Updated fixtures to emit grounded claims.
- Added regression test coverage for:
  - rejection of ungrounded claims
  - rejection of assumption-heavy `Accept` outputs

## Paid Zen Dogfood Meta-Test (Before/After)

Environment:
- Keys sourced from `/mnt/c/Users/cabra/Projects/LifeOS/.env`
- Model: paid Zen `claude-sonnet-4-5`
- Runtime path: `CouncilFSM`, `M2_FULL`, 11-seat override

### Before prompt preflight tightening
- Result: `BLOCKED`
- Seat completion: `8/11`
- Failed seats: `Alignment`, `CoChair`, `Testing`
- Primary failure class: ungrounded `fixes[]` claims (missing `REF:` or `[ASSUMPTION]`)

### After prompt preflight tightening
- Result: `COMPLETE`
- Verdict: `Accept`
- Seat completion: `11/11`
- Failed seats: `0`
- Schema-gate errors: `0`

Interpretation:
- Process hardening correctly blocked low-grounding outputs.
- Prompt hardening materially improved compliance under same paid model.

## Validation Evidence

### Council-focused tests
- Command:
  - `pytest runtime/tests/orchestration/council -q`
- Result:
  - `140 passed, 2 skipped`

### Full required suite
- Command:
  - `pytest runtime/tests -q`
- Result:
  - `1981 passed, 10 skipped, 6 warnings`

## Merge Readiness
- Branch clean.
- Tests green.
- Council process hardening is isolated and production-ready.
