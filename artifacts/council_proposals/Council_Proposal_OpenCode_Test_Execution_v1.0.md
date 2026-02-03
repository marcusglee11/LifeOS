# Council Proposal: OpenCode Test Execution (Phase 3a Envelope Expansion)

---
artifact_id: "council-proposal-opencode-test-execution-v1.0"
artifact_type: "COUNCIL_PROPOSAL"
schema_version: "1.0.0"
created_at: "2026-02-02T00:00:00Z"
author: "Claude Code (Phase 4C Implementation)"
version: "1.0"
status: "DRAFT"
tags: ["governance", "autonomous-loop", "tool-policy", "pytest", "phase-3a", "envelope-expansion"]
council_trigger: "CT-2"
supersedes: null
---

## 0) Decision Request (Council)

**Ruling:** PENDING

This proposal requests Council approval to expand the OpenCode tool envelope to include autonomous pytest execution with strict scope and safety constraints.

---

## 1) Executive Summary

This proposal extends the OpenCode tool policy to enable autonomous test execution via `pytest`, limited to the `runtime/tests/` directory. This capability is essential for Phase 4 (Autonomous Construction) to enable the build loop to verify its own changes without human intervention.

**Core Safety Principles:**
- **Strict path scope enforcement**: Only `runtime/tests/**` allowed
- **Timeout protection**: 5-minute per-run timeout with SIGTERM/SIGKILL
- **Output capture**: stdout/stderr capped at 50KB to prevent memory issues
- **Failure classification**: Structured taxonomy (TEST_FAILURE, TEST_FLAKE, TEST_TIMEOUT)
- **Budget enforcement**: 10-minute cumulative test time per mission
- **Fail-closed**: Any scope violation or timeout immediately blocks execution

**Key Constraint:** This proposal does NOT expand pytest execution beyond the runtime test suite. Protected governance paths remain strictly off-limits.

---

## 2) Problem Statement

The Autonomous Build Loop (Phase 4) cannot currently verify its code changes autonomously. Without test execution capability:

- Every code change requires manual test verification
- Build-test-fix cycles cannot be automated
- The loop cannot learn from test failures to improve subsequent attempts
- Regression detection requires human intervention

Current OpenCode envelope limitations:
- **Allowed:** Doc steward operations (`.md` files in `docs/`)
- **Not Allowed:** Test execution, build verification, code validation

This creates a critical gap: the loop can modify code but cannot verify correctness.

---

## 3) Definitions (Normative)

- **Test Execution Envelope:** The set of paths where pytest is authorized to run tests.
- **Test Target:** The path argument passed to pytest (file or directory).
- **Test Timeout:** Maximum wall-clock time allowed for a single pytest invocation (300 seconds).
- **Mission Test Budget:** Cumulative test time allowed per mission run (600 seconds / 10 minutes).
- **Test Failure Classification:** Structured taxonomy for test outcome analysis (TEST_FAILURE, TEST_FLAKE, TEST_TIMEOUT).
- **Allowed Test Scope:** `runtime/tests/**` only (recursive).

---

## 4) Non-Goals

1. This proposal does **not** enable pytest on arbitrary paths (only `runtime/tests/**`).
2. This proposal does **not** enable test modification or test generation (only execution).
3. This proposal does **not** waive Review Packet requirements for test results.
4. This proposal does **not** enable testing of governance-protected paths.
5. This proposal does **not** enable network access during tests (sandbox remains enforced).
6. This proposal does **not** remove timeout protections or budget limits.

---

## 5) Proposed Amendment (Tool Policy)

**Amend `runtime/governance/tool_policy.py`** to add pytest scope enforcement:

### Section 5.1 — Pytest Tool Allowlist

pytest is already present in `ALLOWED_ACTIONS`:

```python
ALLOWED_ACTIONS = {
    "filesystem": ["read_file", "write_file", "list_dir"],
    "pytest": ["run"],  # Already present
}
```

This proposal adds **path scope enforcement** for pytest.run actions.

### Section 5.2 — Pytest Scope Enforcement

When `tool="pytest"` and `action="run"`, the system MUST validate:

**(A) Target Path Validation:**
- Target must start with `runtime/tests/` or be exactly `runtime/tests`
- Normalized paths (forward slashes) used for comparison
- Path traversal attempts (e.g., `runtime/tests/../../etc/passwd`) MUST be rejected

**(B) Timeout Enforcement:**
- Per-run timeout: 300 seconds (5 minutes)
- Process terminated with SIGTERM, then SIGKILL after 5 seconds
- Timeout results in status="TIMEOUT" and exit_code != 0

**(C) Output Capture:**
- stdout captured up to 50KB
- stderr captured up to 50KB
- Truncation at 50KB boundary if exceeded
- Full output stored in evidence with truncation marker

**(D) Mission Budget:**
- Cumulative test time across all pytest invocations: 10 minutes max
- Budget check BEFORE execution
- Budget exhaustion triggers ESCALATE policy action

### Section 5.3 — Fail-Closed Requirements

If the system cannot:
- Determine the canonical test target path,
- Resolve the workspace root for path validation,
- Enforce timeout limits, or
- Track mission budget,

then pytest execution MUST be denied with reason "GOVERNANCE_UNAVAILABLE".

---

## 6) Policy & Implementation Specification (Execution-Grade)

### 6.1 Pytest Scope Validation Function

```python
def check_pytest_scope(target_path: str) -> Tuple[bool, str]:
    """
    Validate pytest target is within allowed test directories.

    Allowed: runtime/tests/**
    Blocked: Everything else

    Returns:
        (allowed, reason) tuple
    """
    allowed_prefixes = ["runtime/tests/", "runtime/tests"]
    normalized = target_path.replace("\\", "/")

    for prefix in allowed_prefixes:
        if normalized.startswith(prefix) or normalized == prefix:
            return True, f"Path within allowed test scope: {prefix}"

    return False, f"PATH_OUTSIDE_ALLOWED_SCOPE: {target_path}"
```

### 6.2 Timeout Enforcement

```python
PYTEST_TIMEOUT_SECONDS = 300  # 5 minutes

def execute_pytest_with_timeout(
    target: str,
    timeout: int = PYTEST_TIMEOUT_SECONDS
) -> PytestResult:
    """
    Execute pytest with timeout enforcement.

    Returns PytestResult with:
    - status: "PASS" | "FAIL" | "TIMEOUT"
    - exit_code: pytest exit code (or -9 for SIGKILL)
    - stdout: captured output (truncated at 50KB)
    - stderr: captured errors (truncated at 50KB)
    - duration: wall-clock seconds
    """
    # Implementation uses subprocess.run(timeout=timeout)
    # with SIGTERM/SIGKILL handling
```

### 6.3 Integration into check_tool_action_allowed()

```python
# In check_tool_action_allowed():
if tool == "pytest" and action == "run":
    target = request.args.get("target", "")
    allowed, reason = check_pytest_scope(target)
    if not allowed:
        return False, PolicyDecision(
            allowed=False,
            decision_reason=f"DENIED: {reason}",
            matched_rules=["pytest_scope_violation"],
        )
```

### 6.4 Test Failure Classification

Extend `runtime/orchestration/loop/taxonomy.py`:

```python
class FailureClass(Enum):
    TEST_FAILURE = "test_failure"      # Existing
    TEST_FLAKE = "test_flake"          # Existing
    TEST_TIMEOUT = "test_timeout"      # NEW - test exceeded timeout
    # ... existing classes ...
```

Classification rules in `runtime/orchestration/loop/failure_classifier.py`:

```python
def classify_test_failure(
    result: PytestResult,
    previous_results: List[PytestResult] = None
) -> FailureClass:
    """
    Classify a pytest failure into FailureClass.

    Rules:
    - If status == "TIMEOUT": return TEST_TIMEOUT
    - If failed but passed on previous run: return TEST_FLAKE
    - Otherwise: return TEST_FAILURE
    """
```

### 6.5 Evidence Requirements

Every pytest execution MUST record:

```yaml
pytest_evidence:
  target: "runtime/tests/test_example.py"
  exit_code: 0
  status: "PASS"
  duration_seconds: 12.4
  test_counts:
    passed: 42
    failed: 0
    skipped: 3
  stdout: "<captured output, max 50KB>"
  stderr: "<captured errors, max 50KB>"
  truncated: false
  timeout_triggered: false
```

### 6.6 Protected Path Exclusions (Redundant Safety)

Even though the scope check limits to `runtime/tests/**`, the system MUST also verify that no governance-protected paths are in the test target:

- `docs/00_foundations/**` - Constitution (protected)
- `docs/01_governance/**` - Governance rulings (protected)
- `config/governance/protected_artefacts.json` (protected)

If a test target somehow matches a protected path pattern, execution MUST be denied with reason "PROTECTED_PATH_VIOLATION".

---

## 7) Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Runaway test process consuming resources | HIGH | Timeout enforcement with SIGTERM/SIGKILL after 300s |
| Test escaping sandbox to access filesystem | HIGH | Strict path scope validation before execution |
| Large test output consuming memory | MEDIUM | Output truncation at 50KB boundary |
| Flaky tests causing infinite retries | MEDIUM | Flake detection + retry budget enforcement |
| Protected path access via test execution | HIGH | Redundant protected path check before execution |
| Test modifying source files during execution | MEDIUM | Sandbox enforcement (read-only source in test context) |
| Timeout bypass via subprocess spawning | MEDIUM | Process group termination (PGID kill) |

---

## 8) Rollback Plan

If pytest execution proves unstable or unsafe:

1. **Immediate Rollback:** Remove "pytest" from ALLOWED_ACTIONS in tool_policy.py
2. **Evidence Preservation:** All pytest_evidence blocks remain in ledger for analysis
3. **Fallback Mode:** Loop operates in "human verification" mode (status quo ante)
4. **Root Cause Analysis:** Review captured evidence to identify failure modes

Rollback trigger conditions:
- More than 10% of pytest executions trigger timeouts
- Any evidence of sandbox escape or protected path access
- Mission budget exhaustion occurs in >25% of runs
- Council directive to suspend

---

## 9) Success Metrics

**Phase 3a Goals (Immediate):**
- ✅ pytest executes successfully on `runtime/tests/`
- ✅ Zero pytest executions outside allowed scope
- ✅ Zero timeout bypasses or hangs
- ✅ Test failure classification working (TEST_FAILURE, TEST_FLAKE, TEST_TIMEOUT)
- ✅ Evidence capture complete for all executions

**Phase 4 Goals (Autonomous Build Loop):**
- Build loop successfully runs tests after code changes (>95% success rate)
- Test failure feedback enables successful retry (>50% fix rate on first retry)
- Zero governance violations detected in test execution

---

## 10) Dependencies

**Blocks:**
- Phase 4D (Full Code Autonomy) - requires test verification working
- Autonomous build-test-fix loop completion

**Blocked By:**
- Council ruling approval (this proposal)
- Implementation of T4C-02 through T4C-06 tasks

---

## 11) Evidence Requirements (Post-Implementation)

Upon completion of implementation, the following evidence MUST be submitted:

1. **Test Suite Pass:**
   - `pytest runtime/tests/test_tool_policy_pytest.py -v` output (all passing)
   - `pytest runtime/tests/test_failure_classifier.py -v` output (all passing)
   - `pytest runtime/tests/test_build_test_integration.py -v` output (all passing)

2. **Regression Check:**
   - `pytest runtime/tests -q` output showing zero new failures

3. **Manual Verification:**
   - Demonstration of scope enforcement blocking out-of-scope paths
   - Demonstration of timeout enforcement terminating long-running tests
   - Demonstration of output capture working correctly

4. **Code Review:**
   - Git commit hash containing implementation
   - Diff showing changes to tool_policy.py, taxonomy.py, and test files

---

## 12) Constitutional Alignment

This proposal aligns with:

- **Article XIII (Protected Surfaces):** Protected paths remain strictly off-limits
- **Article XVIII (Lightweight Stewardship):** Test execution is bounded and audited
- **Constitution Section 4 (Fail-Closed Governance):** All scope violations fail closed

This proposal does NOT conflict with:
- Trusted Builder Mode (orthogonal - this is about tool envelope, not plan bypass)
- Doc Steward policies (orthogonal - different tool scope)
- Council review requirements (Review Packets still mandatory)

---

## 13) References

- [Phase 4C Implementation Plan](/mnt/c/Users/cabra/Projects/LifeOS/artifacts/plans/Phase_4C_OpenCode_Envelope_Expansion.md)
- [Tool Policy Module](runtime/governance/tool_policy.py)
- [Taxonomy Module](runtime/orchestration/loop/taxonomy.py)
- [Constitution](docs/00_foundations/LifeOS_Constitution_v2.0.md)
- [Council Ruling: Trusted Builder Mode v1.1](docs/01_governance/Council_Ruling_Trusted_Builder_Mode_v1.1.md)

---

## 14) Approval Authority

This proposal requires **unanimous Council approval** (all four agents: Claude, Gemini, Kimi, DeepSeek) OR **APPROVE_WITH_CONDITIONS** where all P0 conditions are satisfied before activation.

Minimum acceptance threshold: 3/4 APPROVE votes with at most 1 APPROVE_WITH_CONDITIONS (where conditions are P1 or satisfied pre-activation).

---

**Proposal Status:** DRAFT - Awaiting Council Review
**Implementation Status:** Tasks T4C-02 through T4C-06 in progress
**Next Step:** Council review after implementation complete + evidence submitted
