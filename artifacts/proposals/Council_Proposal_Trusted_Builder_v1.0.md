# Council Proposal: Trusted Builder Mode

---
artifact_id: "council-proposal-trusted-builder-v1"
artifact_type: "COUNCIL_PROPOSAL"
schema_version: "1.0.0"
created_at: "2026-01-25T18:30:00Z"
author: "Claude Code (Sprint Team)"
version: "1.0"
status: "DRAFT"
tags: ["governance", "autonomous-loop", "plan-bypass", "article-xviii"]
council_trigger: "CT-2"
---

## Executive Summary

This proposal extends Article XVIII (Lightweight Stewardship Mode) to enable the Autonomous Build Loop to retry low-risk failures **without Plan Artefact approval**, reducing human intervention for routine fixes while maintaining full audit trails.

**Key Insight**: Article XVIII already allows Plan bypass for Lightweight Stewardship. This extension applies the same principle to **loop retries** for specific, bounded failure classes.

## Problem Statement

The current Autonomous Build Loop requires Plan Artefact approval (Article XIII) before every retry attempt. For low-risk failures like lint errors, test flakes, and typos, this creates:

1. **Unnecessary latency** - Human approval cycles for trivial fixes
2. **Friction** - Interrupts autonomous operation for routine corrections
3. **No additional safety** - These fixes are already bounded by existing safeguards

## Proposed Solution

Add **Section 5: Loop Retry Eligibility** to Article XVIII (Lightweight Stewardship Mode).

### Eligibility Criteria

A loop retry MAY proceed without Plan Artefact approval if **ALL** conditions are met:

| Criterion | Requirement |
|-----------|-------------|
| Failure Class | In TRUSTED_RETRY_CLASSES allowlist |
| Scope | ≤50 lines changed |
| Files | ≤3 files modified |
| Governance | No governance-controlled paths touched |
| Retries | Within retry budget (max 3 per class) |
| Review Packet | STILL REQUIRED (Art. XII not waived) |

### TRUSTED_RETRY_CLASSES Allowlist

| Failure Class | Rationale |
|---------------|-----------|
| `LINT_ERROR` | Deterministic, auto-fixable, bounded |
| `TEST_FLAKE` | Transient, non-deterministic test behavior |
| `TYPO` | Trivial text corrections |
| `FORMATTING_ERROR` | Deterministic style fixes |

### Explicit Exclusions

These failure classes **always require** Plan approval:

- `SYNTAX_ERROR` - May indicate design issues
- `VALIDATION_ERROR` - May require architectural decisions
- `TEST_FAILURE` - Actual logic failures need review
- `REVIEW_REJECTION` - Human reviewer explicitly rejected
- `UNKNOWN` - Cannot assess risk

## Governance Rationale

### CT-2 Trigger Justification

This proposal modifies a governance-controlled document (GEMINI.md), triggering CT-2 per Article XIII §4.

### Constitutional Alignment

| Principle | How Addressed |
|-----------|---------------|
| **Fail-Closed** | Unknown/excluded classes default to Plan approval |
| **Audit Trail** | Review Packet requirement NOT waived (Art. XII) |
| **Bounded Risk** | Hard limits on lines, files, and retries |
| **Human Override** | CEO can still intervene via escalation |

### Risk Analysis

| Risk | Mitigation |
|------|------------|
| Loop runs amok | Bounded by: ≤50 lines, ≤3 files, ≤3 retries, no governance paths |
| Evidence gap | Review Packet STILL required (Art. XII not waived) |
| Scope creep | Explicit allowlist of failure classes (not wildcard) |
| Silent failures | Ledger records all attempts; terminal packet emitted |

## Proposed Amendment

### GEMINI.md Changes

**Location**: Article XVIII (after Section 4)

```markdown
## Section 5. Loop Retry Eligibility

When the Autonomous Build Loop encounters a failure, it MAY proceed
without Plan Artefact approval if ALL of the following are true:

1. Failure class is in the TRUSTED_RETRY_CLASSES list:
   - LINT_ERROR
   - TEST_FLAKE
   - TYPO
   - FORMATTING_ERROR

2. Proposed fix scope is bounded:
   - ≤50 lines changed
   - ≤3 files modified
   - No governance-controlled paths (per Art. XIII §4)

3. Attempt count is within retry budget (max 3 retries per class)

4. Review Packet is STILL REQUIRED (Art. XII not waived)

5. Loop policy explicitly marks failure class as `plan_bypass_eligible: true`

### §5.1 Audit Requirements

When plan bypass is exercised:

1. Ledger MUST record `plan_bypass_applied: true` in attempt record
2. Terminal packet MUST include bypass statistics
3. Review Packet MUST note "Plan Bypass Applied" in Summary

### §5.2 Explicit Exclusions

The following ALWAYS require Plan Artefact approval:
- SYNTAX_ERROR
- VALIDATION_ERROR
- TEST_FAILURE (distinct from TEST_FLAKE)
- REVIEW_REJECTION
- UNKNOWN
- Any failure class not in TRUSTED_RETRY_CLASSES
```

## Implementation Changes

### 1. loop_rules.yaml

Add `plan_bypass_eligible` and `scope_limit` fields to eligible rules:

```yaml
# Existing rules with new fields:

- rule_id: loop.lint-error
  decision: RETRY
  priority: 110
  match:
    failure_class: lint_error
  max_retries: 3
  plan_bypass_eligible: true  # NEW
  scope_limit:                # NEW
    max_lines: 50
    max_files: 3
  on_budget_exhausted:
    decision: TERMINATE
    terminal_outcome: BLOCKED
    terminal_reason: retry_budget_exhausted

- rule_id: loop.test-flake
  decision: RETRY
  priority: 110
  match:
    failure_class: test_flake
  max_retries: 2
  plan_bypass_eligible: true  # NEW
  scope_limit:                # NEW
    max_lines: 50
    max_files: 3
  on_budget_exhausted:
    decision: TERMINATE
    terminal_outcome: BLOCKED
    terminal_reason: retry_budget_exhausted

- rule_id: loop.typo
  decision: RETRY
  priority: 110
  match:
    failure_class: typo
  max_retries: 3
  plan_bypass_eligible: true  # NEW
  scope_limit:                # NEW
    max_lines: 50
    max_files: 3
  on_budget_exhausted:
    decision: TERMINATE
    terminal_outcome: BLOCKED
    terminal_reason: retry_budget_exhausted

- rule_id: loop.formatting-error
  decision: RETRY
  priority: 110
  match:
    failure_class: formatting_error
  max_retries: 3
  plan_bypass_eligible: true  # NEW
  scope_limit:                # NEW
    max_lines: 50
    max_files: 3
  on_budget_exhausted:
    decision: TERMINATE
    terminal_outcome: BLOCKED
    terminal_reason: retry_budget_exhausted
```

### 2. ConfigurableLoopPolicy

Add method to `runtime/orchestration/loop/configurable_policy.py`:

```python
# Governance-controlled paths (from Article XIII §4)
GOVERNANCE_CONTROLLED_PATHS = [
    "docs/00_foundations/",
    "docs/01_governance/",
    "runtime/governance/",
    "GEMINI.md",
]

GOVERNANCE_PATTERNS = [
    "*Constitution*.md",
    "*Protocol*.md",
]

def is_plan_bypass_eligible(
    self,
    failure_class: FailureClass,
    proposed_diff_lines: int,
    proposed_files: list[str]
) -> tuple[bool, str]:
    """
    Check if retry can proceed without Plan approval.

    Args:
        failure_class: The failure class from last attempt
        proposed_diff_lines: Number of lines in proposed fix
        proposed_files: List of file paths that would be modified

    Returns:
        (eligible, reason) tuple
    """
    # Get failure class string for config lookup
    fc_str = failure_class.value.upper() if isinstance(failure_class, FailureClass) else str(failure_class).upper()

    # Find matching rule in failure_routing
    routing = self.failure_routing.get(fc_str, {})

    # Check if rule allows plan bypass
    if not routing.get("plan_bypass_eligible", False):
        return False, f"Failure class {fc_str} not plan_bypass_eligible"

    # Check scope limits
    scope_limit = routing.get("scope_limit", {})
    max_lines = scope_limit.get("max_lines", 50)
    max_files = scope_limit.get("max_files", 3)

    if proposed_diff_lines > max_lines:
        return False, f"Diff exceeds max_lines ({proposed_diff_lines} > {max_lines})"

    if len(proposed_files) > max_files:
        return False, f"Files exceed max_files ({len(proposed_files)} > {max_files})"

    # Check governance paths
    for path in proposed_files:
        if self._is_governance_path(path):
            return False, f"Governance-controlled path: {path}"

    return True, "Plan bypass eligible"

def _is_governance_path(self, path: str) -> bool:
    """Check if path is governance-controlled per Article XIII §4."""
    import fnmatch

    # Check prefixes
    for prefix in GOVERNANCE_CONTROLLED_PATHS:
        if path.startswith(prefix):
            return True

    # Check patterns
    for pattern in GOVERNANCE_PATTERNS:
        if fnmatch.fnmatch(path, pattern):
            return True

    return False
```

### 3. AutonomousBuildCycleMission

Modify retry decision block in `runtime/orchestration/missions/autonomous_build_cycle.py`:

```python
# In the loop, after policy.decide_next_action():

if action == LoopAction.RETRY.value:
    # Check plan bypass eligibility
    last_attempt = ledger.history[-1] if ledger.history else None

    if last_attempt and last_attempt.failure_class:
        # Estimate diff size from last attempt (or use actual proposed fix)
        estimated_lines = len(feedback.split('\n')) if feedback else 0
        estimated_files = last_attempt.changed_files or []

        bypass_eligible, bypass_reason = policy.is_plan_bypass_eligible(
            failure_class=FailureClass[last_attempt.failure_class.upper()],
            proposed_diff_lines=estimated_lines,
            proposed_files=estimated_files
        )

        if bypass_eligible:
            # Log bypass decision
            executed_steps.append(f"plan_bypass_applied:{last_attempt.failure_class}")
            # Proceed directly to build without Plan approval
        else:
            # Standard path: require Plan approval
            # (Implementation depends on how Plan approval is currently handled)
            pass
```

### 4. Taxonomy Extension

Add new failure classes to `runtime/orchestration/loop/taxonomy.py`:

```python
class FailureClass(Enum):
    # Existing...
    SYNTAX_ERROR = "syntax_error"
    VALIDATION_ERROR = "validation_error"
    TEST_FAILURE = "test_failure"
    REVIEW_REJECTION = "review_rejection"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

    # New trusted retry classes
    LINT_ERROR = "lint_error"
    TEST_FLAKE = "test_flake"
    TYPO = "typo"
    FORMATTING_ERROR = "formatting_error"
```

## Verification Plan

### Automated Tests

1. **Unit Test**: `is_plan_bypass_eligible` returns True for LINT_ERROR with 10 lines, 2 files
2. **Unit Test**: `is_plan_bypass_eligible` returns False for TEST_FAILURE
3. **Unit Test**: `is_plan_bypass_eligible` returns False for LINT_ERROR with 100 lines
4. **Unit Test**: `is_plan_bypass_eligible` returns False when touching `docs/01_governance/`
5. **Integration Test**: Loop correctly bypasses Plan for eligible retries
6. **Integration Test**: Loop requires Plan for non-eligible retries

### Manual Verification

1. Trigger a lint error in autonomous loop
2. Verify it auto-retries without Plan approval
3. Verify Review Packet is still produced
4. Verify ledger records `plan_bypass_applied: true`

## Governance Path

1. **Council Review**: This proposal (CT-2 triggered)
2. **Council Ruling**: If approved, produces `Council_Ruling_Trusted_Builder_v1.0.md`
3. **Implementation**: Code changes per ruling
4. **Validation**: Run verification plan
5. **Deployment**: Merge to main

## Dependencies

- Article XIII (Plan Artefact Gate) - extends scope
- Article XVIII (Lightweight Stewardship) - adds Section 5
- `config/policy/loop_rules.yaml` - adds new fields
- `runtime/orchestration/loop/` - adds new method

## Non-Goals

- This proposal does NOT waive Review Packet requirements (Art. XII)
- This proposal does NOT apply to first-run builds (only retries)
- This proposal does NOT enable wildcard bypass (explicit allowlist only)

---

## Appendix A: Full Diff for GEMINI.md

```diff
--- a/GEMINI.md
+++ b/GEMINI.md
@@ -401,6 +401,55 @@ Format:
 [Diff-based context per Section 3]
 ```

+## Section 5. Loop Retry Eligibility
+
+When the Autonomous Build Loop encounters a failure, it MAY proceed
+without Plan Artefact approval if ALL of the following are true:
+
+1. Failure class is in the TRUSTED_RETRY_CLASSES list:
+   - LINT_ERROR
+   - TEST_FLAKE
+   - TYPO
+   - FORMATTING_ERROR
+
+2. Proposed fix scope is bounded:
+   - ≤50 lines changed
+   - ≤3 files modified
+   - No governance-controlled paths (per Art. XIII §4)
+
+3. Attempt count is within retry budget (max 3 retries per class)
+
+4. Review Packet is STILL REQUIRED (Art. XII not waived)
+
+5. Loop policy explicitly marks failure class as `plan_bypass_eligible: true`
+
+### §5.1 Audit Requirements
+
+When plan bypass is exercised:
+
+1. Ledger MUST record `plan_bypass_applied: true` in attempt record
+2. Terminal packet MUST include bypass statistics
+3. Review Packet MUST note "Plan Bypass Applied" in Summary
+
+### §5.2 Explicit Exclusions
+
+The following ALWAYS require Plan Artefact approval:
+- SYNTAX_ERROR
+- VALIDATION_ERROR
+- TEST_FAILURE (distinct from TEST_FLAKE)
+- REVIEW_REJECTION
+- UNKNOWN
+- Any failure class not in TRUSTED_RETRY_CLASSES
+
 ---

 # ARTICLE XIX — DOGFOODING MANDATE
```

## Appendix B: Approval Request

**Council Members**: Please review this proposal for CT-2 compliance.

**Requested Action**: APPROVE / APPROVE_WITH_CONDITIONS / REJECT

**Questions for Council**:
1. Are the TRUSTED_RETRY_CLASSES appropriate?
2. Are the scope limits (50 lines, 3 files) reasonable?
3. Should any additional safeguards be added?

---

**END OF PROPOSAL**
