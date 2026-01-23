# Implementation Plan: Policy Engine E2E Test Battery

## Goal

Add 6 surgical E2E tests for Policy Engine authoritative gating to validate end-to-end wiring, fail-closed behavior, filesystem scope enforcement, and escalation/waiver artifact workflows. Tests must be deterministic, fast (no sleeps), and introduce zero new failures.

## User Review Required

> [!IMPORTANT]
> **Wiring Approach**: These tests will NOT modify the production loop controller (`AutonomousBuildCycleMission`). Instead, they will test the policy engine components in isolation with minimal integration points, using direct instantiation of `LoopPolicy(effective_config=...)` and `PolicyLoader(authoritative=...)` to validate the authoritative gating mechanism.

> [!CAUTION]
> **Tool Dispatch Path**: E2E-4 requires routing tool invocations through the SAME path the loop uses. Current discovery shows `check_tool_action_allowed(request)` as the enforcement point, but the actual dispatch integration point in the loop is not yet confirmed. If missing, a minimal seam may be required.

## Proposed Changes

### [NEW] [`test_policy_engine_authoritative_e2e.py`](file:///c:/Users/cabra/Projects/LifeOS/runtime/tests/orchestration/missions/test_policy_engine_authoritative_e2e.py)

Creates a new E2E test module under `runtime/tests/orchestration/missions/` with the following structure:

#### Fixtures

1. **`policy_config_dir(tmp_path)`**: Creates a temporary policy config directory with valid/invalid YAML files for testing
2. **`mock_loop_minimal(tmp_path)`**: Minimal loop harness that exercises policy decisions without full mission execution

#### Test Cases

**E2E-1: Authoritative ON uses Policy Engine (wiring tripwire)**

- Arrange: Enable authoritative mode via `PolicyLoader(authoritative=True)` with valid config
- Spy: Wrap `ConfigDrivenLoopPolicy.decide_next_action()` to record calls
- Act: Instantiate `LoopPolicy(effective_config=...)` and invoke `decide_next_action(ledger)`
- Assert: `ConfigDrivenLoopPolicy` was called; legacy `_hardcoded_decide` was NOT called

**E2E-2: Authoritative OFF falls back to Phase A**

- Arrange: Instantiate `LoopPolicy()` with no config (Phase A mode)
- Spy: Wrap `_hardcoded_decide` method
- Act: Invoke `decide_next_action(ledger)`
- Assert: `_hardcoded_decide` was called; no config policy instantiated

**E2E-3: Invalid/unverifiable config fails closed**

- Arrange: Set `LIFEOS_WORKSPACE_ROOT=tmp_path`; create invalid `policy_rules.yaml` (malformed YAML or missing required keys)
- Act: Attempt `PolicyLoader(authoritative=True).load()`
- Assert: Raises `PolicyLoadError`; no fallback to best-effort

**E2E-4: Filesystem scope non-bypassable (end-to-end through tool policy)**

- Arrange: Set `LIFEOS_WORKSPACE_ROOT=tmp_path` and `LIFEOS_SANDBOX_ROOT=tmp_path/sandbox`
- Create three test cases via `ToolInvokeRequest.from_dict()`:
  - a) Missing path: `{"tool":"filesystem","action":"write_file","args":{"content":"x"}}`
  - b) Out-of-scope path: `{"tool":"filesystem","action":"write_file","args":{"path":"../outside.txt","content":"x"}}`
  - c) In-scope path: `{"tool":"filesystem","action":"write_file","args":{"path":"sandbox/ok.txt","content":"x"}}`
- Act: Route each through `check_tool_action_allowed(request)`
- Assert:
  - a) & b) return `(False, decision)` with appropriate denial reason
  - c) returns `(True, decision)` with ALLOWED

**E2E-5: Escalation artifact determinism + unresolvable escalation fails closed**

- Arrange: Create `ConfigurableLoopPolicy` with escalation trigger (protected path touched)
- Prepare ledger with `changed_files=["docs/01_governance/test.md"]`
- Act: Invoke `policy.decide_next_action(ledger)`
- Assert:
  - Returns `("terminate", reason, "ESCALATION_REQUESTED")`
  - Escalation artifact exists at `artifacts/escalations/Policy_Engine/ESCALATION_*.json`
  - Artifact contains required fields: `reason`, `requested_authority`, `ttl_seconds`, `context`, `created_at`
- Unresolvable variant:
  - Make artifact directory read-only (`chmod 0o444`)
  - Re-run policy decision
  - Assert: Raises exception or returns fail-closed signal (no silent pass)

**E2E-6: Waiver artifact behavior + TTL**

- Arrange: Create `ConfigurableLoopPolicy` with retry limit exhausted and waiver-eligible failure class
- Prepare ledger with 3 consecutive `REVIEW_REJECTION` failures
- Act (valid waiver):
  - Invoke `policy.decide_next_action(ledger)` → Returns `WAIVER_REQUESTED`
  - (Simulated waiver approval would be external; this test validates the request signal)
- Act (expired waiver - if waiver evaluation exists in repo):
  - Monkeypatch `datetime.utcnow()` to return future time beyond TTL
  - Assert: Waiver is rejected deterministically

#### Determinism Constraints

- **Time**: Monkeypatch `datetime.utcnow()` in `runtime.orchestration.loop.policy` module for TTL tests
- **Filesystem**: All operations isolated to `tmp_path`
- **Artifact naming**: Use existing `EscalationArtifact.write()` which includes timestamp + content hash (deterministic given monkeypatched time)

### Testability Seams (If Required)

**None expected** based on current architecture. If tool dispatch path is not accessible:

- Add `_dispatch_tool_request(request)` method to `AutonomousBuildCycleMission` for testability
- Justification: Minimal seam, acceptable for E2E isolation

## Verification Plan

### Automated Tests

**Primary**: Run the new E2E test battery

```bash
pytest -q runtime/tests/orchestration/missions/test_policy_engine_authoritative_e2e.py
```

**Expected outcome**: 6 tests pass (E2E-1 through E2E-6)

**Full suite gate** (if feasible):

```bash
pytest -q runtime/tests
```

**Expected outcome**: Zero new failures beyond pre-existing failures

### Evidence Requirements

1. Verbatim logs from targeted test run
2. Verbatim logs from full suite (if executed)
3. Confirmation that all 6 E2E tests pass deterministically

### Manual Verification

Not applicable — all tests are automated.
