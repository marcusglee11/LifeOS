# Runtime ↔ Antigrav Mission Protocol v1.0

**Status**: Active  
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Implements**: Tier2.5_Unified_Fix_Plan_v1.0 (F7)  
**Effective**: 2026-01-02

---

## 1. Purpose

This protocol defines the interface between Antigravity (the document steward / build agent) and the COO Runtime. It specifies:

- Which runtime entrypoints Antigravity may invoke
- How missions are represented and validated
- How Anti-Failure and envelope constraints apply to Antigrav-originated missions
- How the mission whitelist is maintained

---

## 2. Definitions

| Term | Meaning |
|------|---------|
| **Antigravity** | The AI agent acting as Document Steward and build executor |
| **Runtime** | The COO Runtime (Tier-2 deterministic orchestration layer) |
| **Mission** | A bounded unit of work with defined inputs, outputs, and constraints |
| **Entrypoint** | A Python function that Antigravity may invoke to execute missions |
| **Whitelist** | The set of mission types Antigravity is authorized to execute |

---

## 3. Whitelisted Entrypoints

Antigravity may ONLY invoke the following runtime entrypoints:

### 3.1 Tier-2.5 Authorized Entrypoints

| Entrypoint | Module | Purpose | Risk Level |
|------------|--------|---------|------------|
| `run_daily_loop()` | `runtime.orchestration.daily_loop` | Execute daily loop mission | Low |
| `run_scenario()` | `runtime.orchestration.harness` | Execute single scenario | Low |
| `run_suite()` | `runtime.orchestration.suite` | Execute scenario suite | Low |
| `run_test_run_from_config()` | `runtime.orchestration.config_adapter` | Execute config-driven test run | Low |
| `aggregate_test_run()` | `runtime.orchestration.test_run` | Aggregate results | Low |

### 3.2 Forbidden Entrypoints

Antigravity may NOT directly invoke:

| Entrypoint | Reason |
|------------|--------|
| `OrchestrationEngine._execute_step()` | Internal; bypasses validation |
| `MissionBuilder._build_*()` | Internal; bypasses registry |
| Any `runtime.gates.*` | Governance layer; CEO-only |
| Any `runtime.freeze.*` | State management; requires explicit authorization |
| Any `runtime.rollback.*` | Destructive; requires CEO approval |

### 3.3 Entrypoint Extension

New entrypoints may be added to Section 3.1 ONLY via:
1. Fix Pack proposing the addition
2. Council review (Architect + Risk minimum)
3. CEO approval
4. Update to this document

---

## 4. Mission Whitelist

### 4.1 Tier-2.5 Authorized Mission Types

| Mission Type | Registry Key | Parameters | Constraints |
|--------------|--------------|------------|-------------|
| Daily Loop | `daily_loop` | `mode`, `requested_steps`, `requested_human_steps` | Max 5 steps, max 1 human step |
| Echo | `echo` | `message`, `params` | Test only; no side effects |
| Run Tests | `run_tests` | `suite_name`, `config` | Read-only; no mutations |

### 4.2 Mission Type Extension

New mission types may be added ONLY via:
1. Implementation in `runtime/orchestration/` with full test coverage
2. Registration in `runtime/orchestration/registry.py`
3. Fix Pack documenting the mission type
4. Council review
5. Update to this whitelist

---

## 5. Pre-Execution Validation

Before Antigravity executes ANY mission, the following validations MUST pass:

### 5.1 Mission Validation Checklist

| ID | Validation | Failure Action |
|----|------------|----------------|
| V1 | Mission type is in whitelist (Section 4.1) | REJECT mission |
| V2 | Entrypoint is authorized (Section 3.1) | REJECT mission |
| V3 | Parameters conform to mission schema | REJECT mission |
| V4 | Anti-Failure limits will not be exceeded | REJECT mission |
| V5 | No forbidden step kinds in plan | REJECT mission |
| V6 | Runtime tests pass (A1 from F3) | HALT and deactivate |

### 5.2 Validation Sequence

```
1. Receive mission request
2. Check V1: mission_type in WHITELIST
3. Check V2: entrypoint in AUTHORIZED_ENTRYPOINTS
4. Check V3: validate(params, mission_schema)
5. Build mission via MissionBuilder
6. Check V4, V5: _validate_anti_failure(workflow)
7. Check V6: pytest runtime/tests (if not recently verified)
8. Execute mission
9. Log result
```

---

## 6. Anti-Failure Enforcement

Per COO Runtime Spec, Anti-Failure invariants apply to ALL missions including Antigrav-originated:

### 6.1 Hard Limits

| Constraint | Limit | Enforcement |
|------------|-------|-------------|
| MAX_TOTAL_STEPS | 10 | Builder rejects plans exceeding limit |
| MAX_HUMAN_STEPS | 3 | Builder rejects plans exceeding limit |
| Allowed step kinds | `{"runtime", "human"}` | EnvelopeViolation on other kinds |

### 6.2 Enforcement Points

- **Planning time**: `MissionBuilder._validate_anti_failure()` rejects invalid plans
- **Execution time**: `OrchestrationEngine` raises `EnvelopeViolation` on forbidden operations
- **Post-execution**: Results logged; violations trigger F4 deactivation

---

## 7. Envelope Constraints

Antigrav-originated missions operate under the Tier-2 deterministic envelope:

### 7.1 Forbidden Operations

| Operation | Reason |
|-----------|--------|
| Network I/O | Non-deterministic |
| File I/O outside workspace | Escape from sandbox |
| Random number generation | Non-deterministic |
| System time access (wall clock) | Non-deterministic |
| External process execution | Uncontrolled side effects |

### 7.2 Permitted Operations

| Operation | Condition |
|-----------|-----------|
| Read from `docs/` | Always |
| Write to `docs/` | After mission success, via commit |
| Read from `runtime/` | Always |
| Run `pytest` | Via subprocess with captured output |
| Run `generate_corpus.py` | Via subprocess with captured output |
| Git operations | Commit, push only; no force-push without CEO |

### 7.3 OpenCode-First Doc Stewardship (MUST)
Per [OpenCode_First_Stewardship_Policy_v1.0.md](../01_governance/OpenCode_First_Stewardship_Policy_v1.0.md), for any documentation change within the CT-2 Phase 2 envelope, Antigravity **MUST**:
1. Route the change through OpenCode stewardship.
2. Execute the CT-2 gate runner `scripts/opencode_ci_runner.py`.
3. Capture and retain full audit evidence (v2.4+ hygiene enforced).

Bypass of this routing for in-envelope docs is strictly forbidden and constitutes a process failure.

---

## 8. Result Handling

### 8.1 Success Path

When mission completes successfully:

1. **Log** result with full trace
2. **Verify** outputs conform to expected schema
3. **Commit** any file changes with descriptive message
4. **Push** to remote (if configured)
5. **Report** summary to CEO (async, non-blocking)

### 8.2 Failure Path

When mission fails:

1. **Log** failure with full trace and error details
2. **Preserve** state (no cleanup that destroys evidence)
3. **Classify** failure per F4 severity levels
4. **Deactivate** if trigger conditions met
5. **Escalate** to CEO if ambiguous

---

## 9. Audit Trail

All Antigrav→Runtime invocations MUST be logged:

### 9.1 Required Log Fields

| Field | Content |
|-------|---------|
| `timestamp` | ISO 8601 UTC |
| `mission_type` | Registry key |
| `entrypoint` | Function invoked |
| `params` | Mission parameters (sanitized) |
| `result` | Success/failure |
| `duration_ms` | Execution time |
| `commit_hash` | Git commit if changes made |
| `error` | Error details if failed |

### 9.2 Log Location

Logs written to:
- Console (immediate feedback)
- `logs/antigrav_missions.jsonl` (persistent, append-only)
- Git commit messages (for state-changing missions)

---

## 10. Protocol Versioning

This protocol is versioned. Changes require:

1. Fix Pack with proposed changes
2. Council review (minimum: Architect, Risk)
3. CEO approval
4. Version increment (v1.0 → v1.1 for minor, v2.0 for breaking)

Breaking changes (new constraints, removed permissions) require:
- Full Council review
- Migration plan for in-flight missions
- CEO sign-off

---

**END OF DOCUMENT**

