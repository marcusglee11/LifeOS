# Tier-2 Orchestration Hardening Backlog v0.1

**Authority**: Runtime Architecture  
**Scope**: Tier-2 Orchestrator, Builder, Daily Loop Runner  
**Status**: Backlog (Non-Blocking Hardening Items Only)

## 1. Purpose

This backlog consolidates all non-blocking hardening and documentation suggestions arising from Tier-2 reviews of:

- `runtime/orchestration/engine.py` (Orchestrator)
- `runtime/orchestration/builder.py` (Workflow Builder)
- `runtime/orchestration/daily_loop.py` (Daily Loop Runner)

No items in this backlog are required for current correctness or Tier-2 activation. They are candidates for a future hardening wave or Fix Pack.

## 2. Orchestrator Hardening Items (engine.py)

### ORCH-H1 — Explicit Runtime Operation Semantics

**Type**: Spec / Possible Code Tightening  
**Description**: Currently, any operation other than "fail" is effectively treated as a no-op.

**Actions**:
- **Update spec / docs** to state explicitly that:
    - Supported operations in this Tier-2 phase are:
        - "noop" — no state change.
        - "fail" — terminates execution with error.
    - All other operations are treated as no-op in this phase.
- **Optional code tightening (future)**: Restrict allowed operation values to a closed set (e.g. {"noop", "fail"}) and raise a deterministic error for unknown operations, once the contract is ready.

### ORCH-H2 — Freeze Executed Steps for Audit Stability

**Type**: Code Hardening  
**Description**: `executed_steps` holds references to the original `StepSpec` instances. If external code mutates the workflow after orchestration, serialisations of an existing `OrchestrationResult` could change.

**Actions (one of)**:
- When populating `executed_steps`, store:
    - `copy.deepcopy(step)`, or
    - `step.to_dict()` snapshots instead of live objects.
- Ensure `result.to_dict()` remains byte-identical even if the original workflow is mutated post-run.

### ORCH-H3 — Context Metadata Integration (Future Extension)

**Type**: Design / Spec  
**Description**: `ExecutionContext.metadata` is currently unused. It could carry deterministic run metadata (e.g. run_id, caller, policy_version).

**Actions (future phase)**:
- Design a minimal, fixed schema for metadata fields that may be surfaced into:
    - lineage (e.g. caller, policy_version).
    - receipt (e.g. run_id).
- Ensure:
    - Metadata injection is deterministic.
    - Adding metadata does not break existing tests or determinism invariants.

### ORCH-H4 — Explicit Payload Shape Requirements

**Type**: Spec  
**Description**: `StepSpec.to_dict()` assumes payload is a dict with string keys suitable for sorted iteration.

**Actions**:
- **Update spec (and relevant docs)** to state that:
    - `payload` MUST be:
        - JSON-serialisable.
        - A dict with string keys.
    - Optionally add defensive checks and raise a clear error if the invariant is violated.

## 3. Builder Hardening Items (builder.py)

### BLD-H1 — Canonical Metadata Schema

**Type**: Spec / Light Code Cleanup  
**Description**: Metadata for missions is not fully canonical:
- `daily_loop` uses `{"mission_type": "daily_loop", "params": {...}}`.
- `run_tests` uses `{"mission_type": "run_tests", "type": "run_tests", "params": {...}}`.

**Actions**:
- **Decide on a canonical key**: e.g. "mission_type" for all mission types.
- **Make metadata consistent**: Either drop the redundant "type" in run_tests, or document intentional dual fields (mission_type vs type) if the distinction is needed later.

### BLD-H2 — Parameter Normalisation and Validation

**Type**: Code Hardening / Spec  
**Description**: `requested_steps` and `requested_human_steps` behave as upper bounds and can be negative. Negative values are handled safely but implicitly.

**Actions**:
- **Normalise** `requested_steps` and `requested_human_steps` as:
    ```python
    requested_steps = max(0, min(requested_steps, MAX_TOTAL_STEPS))
    requested_human_steps = max(0, min(requested_human_steps, MAX_HUMAN_STEPS))
    ```
- **Update spec/docs** to state:
    - These fields are upper bounds.
    - They are clamped to [0, MAX_*].

### BLD-H3 — AntiFailurePlanningError Semantics

**Type**: Spec  
**Description**: The Review Packet references both truncation and AntiFailurePlanningError. In practice, supported templates are designed so that truncation avoids violations; planning errors are “should not happen” cases.

**Actions**:
- **Document explicitly** that:
    - For supported missions, excessive requests are truncated deterministically to satisfy Anti-Failure limits.
    - `AntiFailurePlanningError` is reserved for:
        - Misconfigured templates that still violate constraints after planning.
        - Workflows externally constructed and passed into `_validate_anti_failure` (if reused).

### BLD-H4 — Envelope Violation Typing at Planning Time

**Type**: Spec (Optional Code Refinement)  
**Description**: `_validate_anti_failure` uses `AntiFailurePlanningError` for both step-count violations and invalid `step.kind`. Orchestrator uses `EnvelopeViolation` at execution.

**Actions**:
- **Decide and document** whether planning-time invalid kinds:
    - Stay as `AntiFailurePlanningError` (planning concern), or
    - Use a more specific exception (e.g. a subtype) to align conceptually with `EnvelopeViolation`.
- Reflect this decision in the Review Packet.

### BLD-H5 — Daily Loop Template Documentation (Archive Step)

**Type**: Spec  
**Description**: Implementation includes an optional "daily-archive" runtime step when within Anti-Failure limits. High-level text emphasises 4 steps (1 human, 3 runtime).

**Actions**:
- **Update Review Packet** to state:
    - Default `daily_loop` (with default params):
        - 4 steps total:
            - 1 human: "daily-confirm-priorities".
            - 3 runtime: e.g. summarise, generate priorities, log summary.
    - When `requested_steps` is increased (up to 5):
        - A 5th runtime step "daily-archive" may be included, still within Anti-Failure limits.

### BLD-H6 — Remove or Use remaining_slots

**Type**: Code Hygiene  
**Description**: `_build_daily_loop` computes `remaining_slots = requested_steps - len(steps)` but never uses it.

**Actions**:
- Either:
    - Remove `remaining_slots`, or
    - Use it explicitly to control template expansion (e.g., loop only while `remaining_slots > 0`), keeping behaviour equivalent.

### BLD-H7 — Mission Registry Extension Rules

**Type**: Spec  
**Description**: Future mission types will be added to `_MISSION_BUILDERS`, and must preserve Tier-2 invariants.

**Actions**:
- **Add explicit “extension rules”** to the Builder spec:
    - Any new mission template MUST:
        - Produce ≤ MAX_TOTAL_STEPS and ≤ MAX_HUMAN_STEPS.
        - Use only step kinds in {"runtime", "human"}.
        - Preserve mission params in metadata via `dict(sorted(params.items()))`.
        - Pass `_validate_anti_failure` without relying on external correction.

## 4. Daily Loop Runner Hardening Items (daily_loop.py)

### DLR-H1 — Clarify Final State Semantics

**Type**: Spec  
**Description**: Review text currently suggests “final state is independent of input,” which is ambiguous and potentially misleading.

**Actions**:
- **Update Review Packet** to state:
    - `result.final_state`:
        - Does not alias `ExecutionContext.initial_state`.
        - Is a deterministic function of `initial_state` + `params`.
    - In this Tier-2 phase, operations are effectively no-op, so the value of `final_state` may equal `initial_state`, but immutability and aliasing guarantees still hold.

### DLR-H2 — Document Builder-Level Anti-Failure Errors

**Type**: Spec  
**Description**: Docstring and Review Packet list `AntiFailureViolation` and `EnvelopeViolation` but not the builder’s `AntiFailurePlanningError`.

**Actions**:
- **Add to Review Packet** and (optionally) docstring:
    - `run_daily_loop` may propagate `AntiFailurePlanningError` if builder templates are misconfigured.
    - Under normal configuration, supported daily-loop missions should not trigger this.

### DLR-H3 — Defensive Copy of params

**Type**: Code Hardening  
**Description**: `run_daily_loop` passes `params` directly into `MissionSpec`. Caller mutation of the dict after calling the function could theoretically affect builder behaviour if used asynchronously (even though current usage is synchronous).

**Actions**:
- **Update code** to:
    ```python
    mission = MissionSpec(
        type="daily_loop",
        params=dict(params or {}),
    )
    ```
- This ensures mission params are decoupled from caller-owned state.

### DLR-H4 — Document Relationship to Builder Template

**Type**: Spec  
**Description**: Runner doc currently describes conceptual daily loop steps, while the exact sequence is defined in the Builder.

**Actions**:
- **Clarify in Review Packet** that:
    - `run_daily_loop` is a thin composition layer:
        - Mission construction → Builder → Orchestrator.
    - The exact step sequence (including optional archive step) is defined by the Builder’s `daily_loop` template and may evolve, as long as Tier-2 invariants are preserved.

### DLR-H5 — Explicit Exception Propagation Behaviour

**Type**: Spec  
**Description**: Runner does not catch or wrap exceptions from Builder or Orchestrator.

**Actions**:
- **Add an explicit note** to the Review Packet:
    - `run_daily_loop` propagates exceptions from Builder and Orchestrator unchanged.
    - Callers should be prepared to handle:
        - `AntiFailurePlanningError` (planning).
        - `AntiFailureViolation` (execution-time Anti-Failure breach).
        - `EnvelopeViolation` (execution-time envelope breach).
        - Any other documented runtime errors at lower layers.

## 5. Mission Registry Hardening Items (registry.py)

### HB-T2-REG-01 — Enforce WorkflowDefinition id/name Consistency

**Type**: Correctness / Determinism  
**Summary**: Tighten `WorkflowDefinition.__post_init__` so that if both `id` and `name` are provided and differ, raise a `ValueError`.  
**Rationale**: Prevents silent divergence between workflow identifier fields; reduces future nondeterminism risk in mission routing.

### HB-T2-REG-02 — Document Registry Immutability Contract

**Type**: Maintainability / API Surface Clarity  
**Summary**: Add comment above `MISSION_REGISTRY` stating that external callers must treat the mapping as read-only and new missions must be added in code, not at runtime.  
**Rationale**: Prevents accidental mutation and preserves static determinism guarantees.

### HB-T2-REG-03 — Add Echo Mission Determinism Test

**Type**: Testing Coverage  
**Summary**: Add a dedicated determinism test for "echo" mirroring the daily-loop determinism pattern.  
**Rationale**: Ensures both built-in Tier-2 missions exhibit identical-input ⇒ identical-output behaviour explicitly.

### HB-T2-REG-04 — Remove Unused Import in test_tier2_registry.py

**Type**: Cleanliness / Future-Proofing  
**Summary**: Delete unused line `from runtime.orchestration import registry as reg`.  
**Rationale**: Keeps the TDD suite minimal and eliminates misleading signals regarding module coupling.

## 6. Mission Harness Hardening Items (harness.py)

### HB-T2-HAR-01 — Define Semantics for Duplicate Mission Names

**Type**: API Semantics / Determinism  
**Summary**: Decide and document how the harness should behave when a `ScenarioDefinition` contains multiple `MissionCall`s with the same name.  
**Current behaviour**: Later missions with the same name overwrite earlier entries in `ScenarioResult.mission_results` (last-write wins), which is deterministic but implicit.  
**Action**:
- Either (a) document that mission names within a scenario MUST be unique, and add a defensive check, or
- (b) extend `ScenarioResult.mission_results` to map mission name → list of `OrchestrationResult` to support repeated missions explicitly.  
**Rationale**: Makes scenario semantics explicit and avoids surprising overwrites while preserving determinism.

### HB-T2-HAR-02 — Signal Read-Only Result Structures via Type Hints

**Type**: Maintainability / API Clarity  
**Summary**: Update type hints for `ScenarioResult` fields to reflect read-only intent.  
**Action**:
- Change `mission_results` annotation to `Mapping[str, OrchestrationResult]`.
- Change `metadata` annotation to `Mapping[str, Any]`.  
**Rationale**: Clarifies that callers must treat scenario results and metadata as read-only views, reducing the risk of accidental mutation in higher layers.

### HB-T2-HAR-03 — Add ScenarioResult.to_dict() for Productisation

**Type**: Productisation Readiness / UX  
**Summary**: Add a `to_dict()` method on `ScenarioResult` to provide a fully serialisable representation for CLI, UI, and the Deterministic Test Harness v0.5.  
**Action (target shape)**:
- Implement `ScenarioResult.to_dict()` returning:
    - `scenario_name`: str
    - `mission_results`: `Dict[str, Dict[str, Any]]` (via `OrchestrationResult.to_dict()`)
    - `metadata`: `Dict[str, Any]` (deep-copied).  
**Rationale**: Provides a stable, canonical serialisation path for scenarios, simplifies higher-level tooling, and aligns with existing `OrchestrationResult.to_dict()` patterns.

## 7. Suite Runner Hardening Items (suite.py)

### HB-T2-SUITE-01 — Remove Unused Import from suite.py

**Type**: Cleanliness / Maintainability  
**Summary**: Remove the unused `copy` import from `runtime/orchestration/suite.py`.  
**Action**:
- Delete `import copy` at the top of `suite.py`.  
**Rationale**: Keeps the module minimal and avoids misleading signals about potential state-copying behaviour.

### HB-T2-SUITE-02 — Signal Read-Only Suite Result Structures via Type Hints

**Type**: API Clarity / Future-Proofing  
**Summary**: Update type hints on `ScenarioSuiteResult` to reflect read-only intent for its mappings.  
**Action**:
- Change `scenario_results` annotation from `Dict[str, ScenarioResult]` to `Mapping[str, ScenarioResult]`.
- Change `metadata` annotation from `Dict[str, Any]` to `Mapping[str, Any]`.  
**Rationale**: Indicates to higher layers that suite results and metadata should be treated as read-only views, reducing accidental mutation risks.

### HB-T2-SUITE-03 — Add Explicit Test for Duplicate Scenario Names

**Type**: API Semantics / Determinism  
**Summary**: Add a test covering the documented last-write-wins behaviour when multiple scenarios share the same `scenario_name`.  
**Action**:
- In `runtime/tests/test_tier2_suite.py`, add a test that:
    - Builds a `ScenarioSuiteDefinition` with two `ScenarioDefinitions` having the same `scenario_name`.
    - Runs `run_suite`.
    - Asserts that `ScenarioSuiteResult.scenario_results` contains a single entry under that name corresponding to the last scenario.  
**Rationale**: Locks in the documented semantics for duplicate scenario names and prevents future regressions.

## 8. Expectations Engine Hardening Items (expectations.py)

### HB-T2-EXP-01 — Remove Redundant exists Branch in _evaluate_op

**Type**: Cleanliness / Single-Source Semantics  
**Summary**: `_evaluate_op` contains an `op == "exists"` branch that is never used, because `evaluate_expectations` handles "exists" directly.  
**Action**:
- Remove the `op == "exists"` branch from `_evaluate_op` in `runtime/orchestration/expectations.py`, keeping "exists" semantics defined exclusively in `evaluate_expectations`.  
**Rationale**: Eliminates dead code, clarifies operator responsibilities, and prevents divergence of "exists" semantics in future edits.

### HB-T2-EXP-02 — Make SuiteExpectationsDefinition.expectations Deeply Immutable

**Type**: API Semantics / Immutability  
**Summary**: `SuiteExpectationsDefinition` is `frozen=True` but its `expectations` field is a mutable `List[MissionExpectation]`.  
**Action**:
- Change `expectations` to `Tuple[MissionExpectation, ...]` and, if needed, normalise list inputs to tuples in `__init__`, mirroring `ScenarioDefinition`/`ScenarioSuiteDefinition`.  
**Rationale**: Aligns with other Tier-2 definition types, prevents accidental mutation after construction, and strengthens determinism guarantees for large expectation sets.

### HB-T2-EXP-03 — Signal Read-Only Result Structures via Mapping[...]

**Type**: API Clarity / Future-Proofing  
**Summary**: `SuiteExpectationsResult.expectation_results` and `.metadata` are currently typed as `Dict[...]`, though callers should treat them as read-only.  
**Action**:
- Update type hints in `SuiteExpectationsResult` to:
    - `expectation_results`: `Mapping[str, ExpectationResult]`
    - `metadata`: `Mapping[str, Any]`
(Implementation can continue to use plain dicts.)  
**Rationale**: Communicates read-only intent to Tier-3 / harness callers and reduces the risk of accidental mutation in higher layers.

### HB-T2-EXP-04 — Enforce or Document Expectation ID Uniqueness

**Type**: API Semantics / Determinism  
**Summary**: `expectation_results` is keyed by `MissionExpectation.id`; duplicate IDs currently produce last-write-wins behaviour without any signal.  
**Action**:
- Either:
    - (a) Document that `MissionExpectation.id` values MUST be unique per suite, and add a defensive check that raises or clearly flags duplicates, or
    - (b) Intentionally support duplicates via an alternative structure (e.g., mapping ID → list of `ExpectationResult`), and update tests accordingly.  
**Rationale**: Avoids silent overwrites and makes ID semantics explicit, which matters once suites grow and are generated programmatically.

### HB-T2-EXP-05 — Clean Up Unused Type Imports

**Type**: Cleanliness / Maintainability  
**Summary**: `Mapping` and `Union` (or other types, if present) are imported but unused in `runtime/orchestration/expectations.py`.  
**Action**:
- Remove unused imports, or use them as part of HB-T2-EXP-03’s type hint tightening.  
**Rationale**: Keeps the module minimal and avoids misleading signals about intended usage patterns.

## 9. Test Run Aggregator Hardening Items (test_run.py)

### HB-T2-TRUN-01 — Signal Read-Only Test Run Metadata via Mapping[...]

**Type**: API Clarity / Future-Proofing  
**Summary**: `TestRunResult.metadata` is currently typed as `Dict[str, Any]`, but callers should treat it as read-only.  
**Action**:
- Update `TestRunResult` in `runtime/orchestration/test_run.py` to use:
    - `metadata`: `Mapping[str, Any]`
while still constructing it with a plain dict internally.  
**Rationale**: Aligns with other Tier-2 result types and signals to higher layers that metadata must not be mutated, reducing accidental side effects.

### HB-T2-TRUN-02 — Enrich Test Run Metadata with Core Identifiers

**Type**: Productisation Readiness / UX  
**Summary**: `TestRunResult.metadata` currently exposes only `test_run_hash`, which is sufficient but sparse for higher-level tooling.  
**Action (non-breaking extension)**:
- Add additional keys to metadata, such as:
    - `"suite_name"` — sourced from the underlying `ScenarioSuiteResult` / suite definition.
    - `"expectations_passed"` / `"expectations_total"` — simple counts derived from `SuiteExpectationsResult`.
- Keep `test_run_hash` unchanged and stable for given inputs.  
**Rationale**: Makes it easier for CLI / UI layers and logs to identify and summarise runs without digging into nested results.

### HB-T2-TRUN-03 — Add TestRunResult.to_dict() for Deterministic Harness v0.5

**Type**: Productisation / Serialisation  
**Summary**: There is no canonical serialisation helper on `TestRunResult`; callers must reconstruct serialisable views manually.  
**Action (target shape)**:
- Implement `TestRunResult.to_dict()` returning a fully JSON-serialisable structure, for example:
    - `suite_result`: serialised via `ScenarioSuiteResult` (using its own `to_dict()` once added).
    - `expectations_result`: serialised via `SuiteExpectationsResult` (using its own `to_dict()` once added).
    - `passed`: bool.
    - `metadata`: deep-copied metadata dict.
- Ensure this structure is consistent with (or a superset of) what is used in the `test_run_hash` payload.  
**Rationale**: Provides a single canonical shape for logging, persistence, diffing, and future Deterministic Test Harness features, avoiding ad-hoc serialisation logic in higher layers.

## 10. Execution Guidance

These items can be batched into a future “Tier-2 Orchestration Hardening” mission or Fix Pack.

**Recommended execution order (minimal disruption)**:
1. **Spec/docs-only items**: ORCH-H4, BLD-H3, BLD-H5, BLD-H7, DLR-H1, DLR-H2, DLR-H4, DLR-H5, HB-T2-HAR-01.
2. **Code hygiene**: BLD-H6, HB-T2-REG-04, HB-T2-HAR-02, HB-T2-SUITE-01, HB-T2-SUITE-02, HB-T2-EXP-01, HB-T2-EXP-03, HB-T2-EXP-05, HB-T2-TRUN-01.
3. **Low-risk code hardening**: DLR-H3, BLD-H2, ORCH-H2, HB-T2-REG-01, HB-T2-REG-02, HB-T2-REG-03, HB-T2-HAR-03, HB-T2-SUITE-03, HB-T2-EXP-02, HB-T2-EXP-04, HB-T2-TRUN-02, HB-T2-TRUN-03.
4. **Design extensions**: ORCH-H3, BLD-H1, BLD-H4, ORCH-H1 (if tightening op set).
