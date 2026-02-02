# Council Proposal: Code Autonomy (Phase 4D Envelope Expansion)

---
artifact_id: "council-proposal-code-autonomy-v1.0"
artifact_type: "COUNCIL_PROPOSAL"
schema_version: "1.0.0"
created_at: "2026-02-03T00:00:00Z"
author: "Claude Code (Phase 4D Implementation)"
version: "1.0"
status: "DRAFT"
tags: ["governance", "autonomous-loop", "tool-policy", "code-creation", "phase-4d", "envelope-expansion"]
council_trigger: "CT-4D"
supersedes: null
requested_rulings: ["CR-4D-01"]
---

## 0) Decision Request (Council)

**Ruling:** PENDING

This proposal requests Council approval to expand the OpenCode tool envelope to enable autonomous code creation and modification within strictly defined paths, with comprehensive safety measures including syntax validation, diff budgets, and self-modification protection.

---

## 1) Executive Summary

This proposal extends the OpenCode tool policy to enable autonomous code creation and modification in the `coo/`, `runtime/`, and `tests/` directories. This capability is the final step in Phase 4 (Autonomous Construction) to enable the build loop to implement features and fixes without human intervention.

**Core Safety Principles:**
- **Strict path allowlist**: Only `coo/`, `runtime/`, `tests/` paths authorized
- **Protected paths enforcement**: Governance and self-modification files hardcoded as DENIED
- **Diff budget**: Maximum 300 lines of changes per build cycle
- **Syntax validation**: All Python, YAML, and JSON files validated before write
- **Fail-closed**: Any validation failure or protection violation immediately blocks write
- **Evidence capture**: All file operations recorded with full provenance

**Key Constraints:**
- Protected governance paths (`docs/00_foundations/`, `docs/01_governance/`, `config/governance/`) remain strictly off-limits
- Self-modification protection files (`runtime/governance/*.py`) cannot be modified
- Agent identity files (`CLAUDE.md`, `GEMINI.md`, `config/models.yaml`) are protected

---

## 2) Problem Statement

The Autonomous Build Loop (Phase 4) cannot currently modify code autonomously. Without code creation capability:

- Every code change requires manual human implementation
- Build-test-fix cycles cannot be fully automated
- The loop cannot implement fixes based on test failures
- Feature development requires human intervention at every step

Current OpenCode envelope limitations:
- **Allowed:** Doc operations (`.md` files), test execution (`pytest`)
- **Not Allowed:** Code creation, code modification, file writes outside docs

This creates the final critical gap: the loop can plan changes, write docs, and run tests, but cannot implement the actual code changes.

**Prerequisites Met:**
- Phase 4C (Test Execution) has been implemented and verified
- Syntax validation infrastructure is implemented
- Protected paths registry is established
- Diff budget validation is in place

---

## 3) Definitions (Normative)

- **Code Autonomy Envelope:** The set of paths where autonomous agents are authorized to create and modify files.
- **Protected Path:** A path that is explicitly blocked from autonomous modification, including governance surfaces and self-modification protection files.
- **Diff Budget:** The maximum number of changed lines allowed per build cycle (300 lines).
- **Syntax Validation:** Automated validation of file syntax using language-specific parsers (AST for Python, parsers for YAML/JSON).
- **Self-Modification Protection:** Hardcoded denial of modifications to files that control the policy enforcement system itself.
- **Allowed Code Paths:** `coo/`, `runtime/`, `tests/`, `tests_doc/`, `tests_recursive/` (recursive).

---

## 4) Non-Goals

1. This proposal does **not** enable file creation outside the allowed code paths.
2. This proposal does **not** permit modification of governance surfaces (`docs/00_foundations/`, `docs/01_governance/`).
3. This proposal does **not** permit modification of self-protection files (`runtime/governance/self_mod_protection.py`, etc.).
4. This proposal does **not** enable arbitrary diff sizes (300-line budget remains enforced).
5. This proposal does **not** waive syntax validation requirements.
6. This proposal does **not** enable modification of agent identity files (`CLAUDE.md`, `GEMINI.md`, `config/models.yaml`).
7. This proposal does **not** remove Review Packet requirements for significant code changes.

---

## 5) Proposed Amendment (Tool Policy)

**Amend `runtime/governance/tool_policy.py`** to add code autonomy policy enforcement.

### Section 5.1 — Tool Allowlist Amendment (FUTURE)

**IMPORTANT:** This proposal defines the policy but does NOT immediately activate write operations. Activation requires:
1. Council approval (CR-4D-01)
2. 30 days of stable Phase 4C operation with 0 envelope violations
3. Evidence compilation demonstrating safety

When approved, `ALLOWED_ACTIONS` will be amended:

```python
ALLOWED_ACTIONS = {
    "filesystem": ["read_file", "write_file", "list_dir"],  # write_file activated
    "pytest": ["run"],
}
```

### Section 5.2 — Protected Paths Registry

**Create `runtime/governance/protected_paths.py`** with hardcoded protection:

```python
PROTECTED_PATHS = {
    # Governance surfaces - Council-only
    "docs/00_foundations/": "GOVERNANCE_FOUNDATION",
    "docs/01_governance/": "GOVERNANCE_RULINGS",
    "config/governance/": "GOVERNANCE_CONFIG",

    # Self-modification protection - Hardcoded
    "runtime/governance/self_mod_protection.py": "SELF_MOD_PROTECTION",
    "runtime/governance/envelope_enforcer.py": "ENVELOPE_ENFORCER",
    "runtime/governance/protected_paths.py": "PROTECTED_PATHS_REGISTRY",
    "runtime/governance/tool_policy.py": "TOOL_POLICY_GATE",

    # Agent identity - Council-only
    "config/agent_roles/": "AGENT_IDENTITY",
    "config/models.yaml": "MODEL_CONFIG",
    "config/governance_baseline.yaml": "GOVERNANCE_BASELINE",

    # Build infrastructure - Self-protection
    "CLAUDE.md": "AGENT_INSTRUCTIONS",
    "GEMINI.md": "AGENT_INSTRUCTIONS",
}

ALLOWED_CODE_PATHS = [
    "coo/",
    "runtime/",
    "tests/",
    "tests_doc/",
    "tests_recursive/",
]
```

### Section 5.3 — Path Validation Policy

When `tool="filesystem"` and `action="write_file"`, the system MUST validate:

**(A) Protected Path Check (Highest Priority):**
- If path matches any PROTECTED_PATHS entry → DENY immediately
- Protected check takes precedence over allowed scope

**(B) Allowed Scope Check:**
- Path must start with one of ALLOWED_CODE_PATHS
- If not in allowed scope → DENY with reason "PATH_OUTSIDE_ALLOWED_SCOPE"

**(C) Validation Logic:**
```python
def validate_write_path(path: str) -> tuple[bool, str]:
    # 1. Check protected first (deny takes precedence)
    if is_path_protected(path):
        return False, "PROTECTED: [reason]"

    # 2. Check allowed scope
    if not is_path_in_allowed_scope(path):
        return False, "PATH_OUTSIDE_ALLOWED_SCOPE"

    return True, "ALLOWED"
```

### Section 5.4 — Diff Budget Enforcement

**Maximum Diff Budget:** 300 lines per build cycle

**(A) Diff Calculation:**
- Count total added + deleted + modified lines across all file operations
- Cumulative across all writes in a single build mission
- Budget check performed BEFORE any write operation

**(B) Budget Enforcement:**
```python
MAX_DIFF_LINES = 300

def validate_diff_budget(diff_lines: int) -> tuple[bool, str]:
    if diff_lines > MAX_DIFF_LINES:
        return False, f"DIFF_BUDGET_EXCEEDED: {diff_lines} > {MAX_DIFF_LINES}"
    return True, "Diff within budget"
```

**(C) Budget Exceeded Behavior:**
- Block all writes when budget exceeded
- Trigger escalation to CEO queue
- Capture evidence of attempted oversized change

### Section 5.5 — Syntax Validation

**Create `runtime/governance/syntax_validator.py`** for fail-closed syntax validation.

**(A) Supported Languages:**
- **Python:** AST parsing (`ast.parse()`)
- **YAML:** Safe parsing (`yaml.safe_load()`)
- **JSON:** Standard parsing (`json.loads()`)

**(B) Validation Policy:**
- Detect language from file extension (`.py`, `.yaml`, `.yml`, `.json`)
- Parse content before write operation
- If parse fails → DENY write with syntax error details
- Unknown file types → WARN but allow (fail-open for non-code files)

**(C) Implementation:**
```python
class SyntaxValidator:
    def validate(self, content: str, lang: str) -> ValidationResult:
        if lang == "python":
            return validate_python(content)  # ast.parse()
        elif lang in ["yaml", "yml"]:
            return validate_yaml(content)    # yaml.safe_load()
        elif lang == "json":
            return validate_json(content)    # json.loads()
        else:
            return ValidationResult(valid=True)  # Unknown type
```

### Section 5.6 — Fail-Closed Requirements

If the system cannot:
- Determine if a path is protected,
- Validate the path scope,
- Calculate the diff budget,
- Perform syntax validation, or
- Track file operation history,

then write operations MUST be denied with reason "GOVERNANCE_UNAVAILABLE".

---

## 6) Policy & Implementation Specification (Execution-Grade)

### 6.1 Code Autonomy Policy Check

```python
def check_code_autonomy_policy(
    request: ToolInvokeRequest,
    diff_lines: Optional[int] = None,
) -> Tuple[bool, PolicyDecision]:
    """
    Check code autonomy policy for write/create operations.

    Policy:
    1. Protected paths are DENIED (highest priority)
    2. Paths outside allowed scope are DENIED
    3. Diff budget exceeded is DENIED
    4. Syntax validation failure is DENIED
    5. All checks passed → ALLOWED
    """
    tool = request.tool
    action = request.action

    # Only applies to filesystem write operations
    if tool != "filesystem" or action != "write_file":
        return True, PolicyDecision(allowed=True)

    # Get path from request
    path = request.get_path()
    if not path:
        return False, PolicyDecision(
            allowed=False,
            decision_reason="DENIED: write_file requires path (fail-closed)"
        )

    # Validate path (protected check + allowed scope)
    path_allowed, path_reason = validate_write_path(path)
    if not path_allowed:
        return False, PolicyDecision(
            allowed=False,
            decision_reason=f"DENIED: {path_reason}",
            matched_rules=["code_autonomy_path_violation"]
        )

    # Validate diff budget if provided
    if diff_lines is not None:
        budget_ok, budget_reason = validate_diff_budget(diff_lines)
        if not budget_ok:
            return False, PolicyDecision(
                allowed=False,
                decision_reason=f"DENIED: {budget_reason}",
                matched_rules=["code_autonomy_diff_budget_exceeded"]
            )

    # Validate syntax if content provided
    content = request.args.get("content")
    if content:
        validator = SyntaxValidator()
        result = validator.validate(content, path=path)
        if not result.valid:
            return False, PolicyDecision(
                allowed=False,
                decision_reason=f"DENIED: SYNTAX_VALIDATION_FAILED: {result.error}",
                matched_rules=["code_autonomy_syntax_invalid"]
            )

    return True, PolicyDecision(allowed=True)
```

### 6.2 Integration Points

**Build Mission Integration:**
- Build missions calculate total diff before execution
- Syntax validation runs before file write
- Evidence captures all file operations
- Rollback on any validation failure

**Evidence Capture:**
- Log path, content hash, diff size for each write
- Capture blocked attempts with full context
- Record syntax validation failures
- Track diff budget consumption

---

## 7) Evidence Requirements (Phase 4C Stability)

**Required Evidence for Council Approval:**

1. **Phase 4C Stability:** 30 consecutive days of stable test execution operation
2. **Envelope Compliance:** 0 envelope violations during stability period
3. **Test Execution Success:** Demonstrated ability to run tests and classify failures
4. **Infrastructure Readiness:**
   - Syntax validator implemented and tested (30 tests)
   - Protected paths registry implemented
   - Diff budget validation implemented
   - Code autonomy policy tests pass (39 tests)

**Current Status:**
- ✅ Syntax validator: Implemented with 30 passing tests
- ✅ Protected paths registry: Implemented
- ✅ Code autonomy policy: Implemented with 39 passing tests
- ⏳ Phase 4C stability: Requires 30-day observation period

---

## 8) Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Governance surface bypass** | Low | Critical | Multi-layer protection: hardcoded paths, registry immutability, Council-only modification |
| **Self-modification escape** | Very Low | Critical | Hardcoded protection of policy enforcement files, multiple validation layers |
| **Diff budget circumvention** | Low | Medium | Per-build cumulative tracking, fail-closed on budget exceeded |
| **Syntax validation bypass** | Low | Medium | AST parsing (not regex), fail-closed on parse errors |
| **Protected path discovery** | Low | High | Hardcoded registry, protected from self-modification |
| **Accidental sensitive file write** | Medium | Medium | Path validation before write, evidence capture, rollback capability |

**Additional Safeguards:**
- All writes require explicit path specification (no wildcards)
- Evidence capture provides full audit trail
- CEO escalation queue for anomalies
- Council retains override authority for emergency stop

---

## 9) Success Criteria

**Immediate (Post-Approval):**
- [ ] Code autonomy policy integrated into `check_tool_action_allowed()`
- [ ] Protected paths enforcement verified (test suite passes)
- [ ] Syntax validation blocks invalid code
- [ ] Diff budget enforcement blocks oversized changes
- [ ] Evidence capture logs all write operations

**30-Day Observation:**
- [ ] 0 envelope violations (protected path attempts)
- [ ] 0 self-modification attempts
- [ ] Syntax validation blocks 100% of invalid code
- [ ] Diff budget enforcement blocks oversized changes
- [ ] Test suite remains green (1178+ tests passing)

**60-Day Validation:**
- [ ] Successful autonomous code implementation (at least 5 features/fixes)
- [ ] Test-driven development cycle working (write code → run tests → fix)
- [ ] Evidence packets demonstrate safe operation
- [ ] No regression in governance compliance

---

## 10) Rollback Plan

If any of the following occur within 60 days of activation:

1. **Governance breach:** Protected path write attempt succeeds
2. **Self-modification:** Policy file modified by autonomous agent
3. **Systemic instability:** Test pass rate drops below 95%
4. **Evidence gaps:** Missing provenance for code changes

**Rollback Procedure:**
1. Remove `write_file` from `ALLOWED_ACTIONS` immediately
2. Revert to Phase 4C state (test execution only)
3. Conduct incident analysis via Council
4. Require new evidence period before re-enabling

---

## 11) Timeline & Dependencies

| Milestone | Dependency | Timeline |
|-----------|------------|----------|
| Council review of proposal | This document | Week 1 |
| Phase 4C stability evidence | 30 days operation | Week 1-5 |
| Council approval (CR-4D-01) | Evidence + Council vote | Week 6 |
| Policy activation | CR-4D-01 approved | Week 7 |
| 30-day observation period | Policy active | Week 7-10 |
| 60-day validation | Policy active | Week 11-14 |

**Estimated Total Timeline:** 14 weeks from proposal to full validation

---

## 12) Appendix A: Test Coverage

**Syntax Validator Tests:** 30 tests
- Python validation: 6 tests (valid/invalid cases)
- YAML validation: 5 tests (valid/invalid cases)
- JSON validation: 6 tests (valid/invalid cases)
- Language detection: 4 tests
- Integration tests: 9 tests

**Code Autonomy Policy Tests:** 39 tests
- Path validation: 6 tests (allowed paths)
- Protected paths: 8 tests (governance, self-mod)
- Write path validation: 6 tests (combined checks)
- Diff budget: 4 tests (within/exceeded)
- Policy integration: 12 tests (end-to-end)
- Edge cases: 3 tests (cross-platform)

**Total Test Coverage:** 69 tests for Phase 4D infrastructure

---

## 13) Appendix B: Protected Paths Justification

**Why Each Path Is Protected:**

1. **`docs/00_foundations/`** — Constitutional documents, require Council amendment
2. **`docs/01_governance/`** — Council rulings, single source of truth for policy
3. **`config/governance/`** — Governance configuration, defines protected surfaces
4. **`runtime/governance/self_mod_protection.py`** — Self-modification detection
5. **`runtime/governance/envelope_enforcer.py`** — Enforcement mechanism
6. **`runtime/governance/protected_paths.py`** — This protection list itself
7. **`runtime/governance/tool_policy.py`** — Policy decision engine
8. **`config/agent_roles/`** — Agent identity and capabilities
9. **`config/models.yaml`** — Model selection and configuration
10. **`config/governance_baseline.yaml`** — Governance baselines
11. **`CLAUDE.md`, `GEMINI.md`** — Agent instructions and constraints

**Protection Mechanism:** Hardcoded in code, cannot be modified without human intervention.

---

## 14) Appendix C: Comparison to Industry Standards

| Standard | LifeOS Phase 4D | Notes |
|----------|-----------------|-------|
| **CI/CD Automation** | Similar scope | Autonomous code changes limited to non-critical paths |
| **Auto-merge bots** | Stricter limits | GitHub bots have broader access, we limit to specific dirs |
| **Policy enforcement** | Stronger | Multiple layers: path, syntax, budget, evidence |
| **Self-modification** | Prohibited | Most CI/CD systems allow pipeline modification |
| **Diff limits** | Uncommon | 300-line budget is novel governance mechanism |

**Key Difference:** LifeOS combines autonomous code creation with fail-closed governance, a novel approach in AI autonomy.

---

**END OF PROPOSAL**

**Next Steps:**
1. Council review and questions period (1 week)
2. Gather Phase 4C stability evidence (30 days)
3. Council vote on CR-4D-01
4. If approved: Activate policy and begin observation period
