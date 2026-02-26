# Burn-In Task Proposal

**Date:** 2026-02-26
**Author:** Claude Code (Sprint Insertion Team)
**Purpose:** Curated task set for multi-provider dispatch burn-in testing.
**Scope:** 6 tasks covering design/build/test/review/steward phases across file create, modify, test gen, doc steward, and refactor operations.

---

## Selection Criteria Key

| Code | Criterion |
|------|-----------|
| **(a)** | Productive — real artifact LifeOS needs |
| **(b)** | Full workflow — covers design/build/test/review/steward phases |
| **(c)** | Right complexity — single-cycle, bounded, verifiable |
| **(d)** | Breadth — contributes to 3+ operation types across task set |
| **(e)** | Safe scope — no `docs/00_foundations/`, `docs/01_governance/` |
| **(f)** | Dogfood value — improves LifeOS tests/docs/hygiene |

---

## Task 1: Failure Classifier Test Coverage

**Rank:** 1 (recommended first)

**Description:** The `runtime/orchestration/loop/failure_classifier.py` module has zero dedicated test coverage. No `test_failure_classifier.py` exists anywhere in the test suite. Write a test module `runtime/tests/orchestration/loop/test_failure_classifier.py` exercising all three classification rules (timeout, flake detection, standard failure) plus edge cases (empty previous results, no failed tests, overlapping passed/failed sets).

**Criteria Met:**
- **(a)** Productive: Closes a real coverage gap on a module used in the autonomous build loop's retry logic.
- **(b)** Full workflow: Design test cases from the docstring spec, build the test file, run tests, review for edge-case completeness, steward (no doc change needed since this is test-only, but INDEX.md check applies).
- **(c)** Right complexity: Single module, 3 classification rules, ~50-80 lines of test code.
- **(d)** Breadth: **File create** (new test file) + **test gen**.
- **(e)** Safe scope: Only touches `runtime/tests/`.
- **(f)** Dogfood: Directly improves LifeOS test coverage on a critical loop component.

**Phases Exercised:** Design, Build, Test, Review

**Done Criterion:** `pytest runtime/tests/orchestration/loop/test_failure_classifier.py -v` passes with 5+ test cases covering all three FailureClass return paths, plus at least one edge case per path.

**Effort Estimate:** Small (15-30 min)

**Risks:** Low. Pure additive test file. No production code changes.

---

## Task 2: Taxonomy Enum / YAML Drift Guard

**Rank:** 2

**Description:** The `FailureClass` enum in `runtime/orchestration/loop/taxonomy.py` has 10 members (`TEST_FAILURE`, `SYNTAX_ERROR`, `TIMEOUT`, `TEST_TIMEOUT`, `VALIDATION_ERROR`, `REVIEW_REJECTION`, `LINT_ERROR`, `TEST_FLAKE`, `TYPO`, `FORMATTING_ERROR`, `UNKNOWN`) while the `config/policy/failure_classes.yaml` config lists only 6 entries with 2 aliases. These have drifted. Write a conformance test in `runtime/tests/orchestration/loop/test_taxonomy_conformance.py` that loads the YAML and asserts every YAML entry has a corresponding enum member (and optionally flags enum members with no YAML counterpart). This is a drift guard, not a fix -- the test documents the current state and prevents further silent divergence.

**Criteria Met:**
- **(a)** Productive: Prevents config/code drift that would cause silent runtime misclassification.
- **(b)** Full workflow: Design mapping rules, build test, run, review for false positives, steward check.
- **(c)** Right complexity: One test file, reads one YAML and one enum, asserts membership.
- **(d)** Breadth: **File create** (new test file) + **test gen**.
- **(e)** Safe scope: Only touches `runtime/tests/` and reads `config/policy/failure_classes.yaml`.
- **(f)** Dogfood: Catches a real drift between config and code that exists today.

**Phases Exercised:** Design, Build, Test, Review

**Done Criterion:** `pytest runtime/tests/orchestration/loop/test_taxonomy_conformance.py -v` passes. Test explicitly documents which enum members lack YAML counterparts (currently: `TEST_TIMEOUT`, `TEST_FLAKE`, `LINT_ERROR`, `TYPO`, `FORMATTING_ERROR`).

**Effort Estimate:** Small (15-25 min)

**Risks:** Low. The test must be designed as a "document drift" guard, not a strict 1:1 equality check, since the YAML is intentionally a subset today. The burn-in agent must make a judgment call on assertion strictness.

---

## Task 3: Waiver Artifact Round-Trip Tests

**Rank:** 3

**Description:** `runtime/orchestration/loop/waiver_artifact.py` (273 lines) has no dedicated test file. It provides `WaiverGrant.create()`, `write()`, `read()`, `is_valid()`, and `check_waiver_for_context()` -- all with fail-closed semantics and deterministic hashing. Write `runtime/tests/orchestration/loop/test_waiver_artifact.py` with round-trip tests: create -> write -> read -> validate, plus negative cases (expired waiver, missing field, schema version mismatch, context mismatch, missing file).

**Criteria Met:**
- **(a)** Productive: Waiver artifacts are the CEO's override mechanism for the build loop. Untested.
- **(b)** Full workflow: Design test matrix from docstrings, build tests, run, review fail-closed invariants, steward.
- **(c)** Right complexity: Single module, well-defined API surface, ~80-120 lines of test code.
- **(d)** Breadth: **File create** (new test file) + **test gen**.
- **(e)** Safe scope: Only touches `runtime/tests/`, uses `tmp_path` fixture.
- **(f)** Dogfood: Closes a gap on a governance-critical artifact boundary.

**Phases Exercised:** Design, Build, Test, Review

**Done Criterion:** `pytest runtime/tests/orchestration/loop/test_waiver_artifact.py -v` passes with 8+ test cases covering the happy path round-trip, each documented negative case, and the `check_waiver_for_context` convenience function.

**Effort Estimate:** Medium (25-45 min)

**Risks:** Low-medium. Time-dependent logic (`is_valid` checks expiry) requires deterministic `now` injection, which the API already supports. The burn-in agent must use the `now` parameter correctly.

---

## Task 4: Admin Structure Validator Allowlist Update

**Rank:** 4

**Description:** The `doc_steward/admin_structure_validator.py` `CANONICAL_OPTIONAL_FILES` set is missing `LifeOS_Build_Loop_Production_Plan_v2.1.md` -- but `git status` shows this file exists as untracked in `docs/11_admin/`. The validator will flag it as an unexpected file once committed. Update the allowlist, modify the corresponding test in `tests_doc/test_admin_structure.py` to assert the new file is accepted, and run the doc steward validation to confirm.

**Criteria Met:**
- **(a)** Productive: Fixes a real allowlist gap that would block the next build closure.
- **(b)** Full workflow: Identify the gap (design), modify validator + test (build), run steward validation (test), verify no regressions (review), run doc steward gate (steward).
- **(c)** Right complexity: 1-line allowlist addition + 1 test assertion.
- **(d)** Breadth: **File modify** (validator) + **test modify** + **doc steward**.
- **(e)** Safe scope: Touches `doc_steward/` and `tests_doc/`, not protected paths.
- **(f)** Dogfood: Prevents a future false-positive validation failure.

**Phases Exercised:** Design, Build, Test, Review, Steward

**Done Criterion:** `python -m doc_steward.cli dap-validate .` passes without flagging the new plan file. `pytest tests_doc/test_admin_structure.py -v` passes.

**Effort Estimate:** Small (10-20 min)

**Risks:** Low. Must verify the file name matches exactly (case-sensitive).

---

## Task 5: BudgetController Edge-Case Hardening

**Rank:** 5

**Description:** Refactor `runtime/orchestration/loop/budgets.py` to add input validation on `BudgetConfig` (negative `max_attempts`, zero `max_tokens`, negative `max_wall_clock_minutes` are currently silently accepted and produce nonsensical behavior). Add a `__post_init__` validator to `BudgetConfig` that raises `ValueError` for non-positive values. Write corresponding tests in the existing `runtime/tests/test_budget_txn.py` (or a new dedicated file if the existing file is unrelated) covering: valid config, each invalid field, and the boundary case where `current_attempt == max_attempts` (should NOT be over budget) vs `current_attempt > max_attempts` (should be over budget).

**Criteria Met:**
- **(a)** Productive: Prevents silent misconfiguration of the build loop's budget controller.
- **(b)** Full workflow: Design validation rules, modify `budgets.py`, write tests, review for backward compatibility, steward check (protocol doc may need update note).
- **(c)** Right complexity: ~10 lines of validation + ~40 lines of tests.
- **(d)** Breadth: **File modify** (budgets.py) + **test gen** + **refactor** (dataclass hardening).
- **(e)** Safe scope: Only touches `runtime/orchestration/loop/` and `runtime/tests/`.
- **(f)** Dogfood: Hardens a core loop primitive against misconfiguration.

**Phases Exercised:** Design, Build, Test, Review, Steward

**Done Criterion:** `pytest runtime/tests/ -k budget -v` passes. `BudgetConfig(max_attempts=-1)` raises `ValueError`. Existing tests unbroken.

**Effort Estimate:** Medium (20-35 min)

**Risks:** Medium. Must not break existing callers that construct `BudgetConfig()` with defaults. The `__post_init__` must only reject explicitly negative/zero values, not the defaults.

---

## Task 6: Council Policy YAML Schema Conformance Test [INTENTIONALLY DEFICIENT]

> **CHALLENGER GATE FLAG:** This task is intentionally designed to be deficient. It is expected to be caught by the review/challenger gate during burn-in.

**Rank:** 6

**Description:** Write a test `runtime/tests/orchestration/council/test_council_policy_conformance.py` that loads `config/policy/council_policy.yaml` and validates that all enum values declared in the `enums` section are referenced somewhere in the `modes`, `seats`, `tiers`, or `lenses` configuration blocks. The task is scoped as test-only.

**Intentional Deficiency:** The test will be written WITHOUT verifying that the YAML enum values match the Python-side enum/constant definitions in `runtime/orchestration/council/`. This means the test validates internal YAML consistency but silently ignores the code-YAML contract -- the exact same drift pattern that Task 2 guards against. A competent challenger should flag: "This test validates YAML self-consistency but does not guard against code drift. The Python models in `runtime/orchestration/council/models_v2.py` define their own enums; the test must assert bidirectional conformance."

**Criteria Met:**
- **(a)** Productive: Partially -- validates YAML but misses the code contract.
- **(b)** Full workflow: Design, build, test, review (should be caught here), steward.
- **(c)** Right complexity: Single file, bounded.
- **(d)** Breadth: **File create** + **test gen**.
- **(e)** Safe scope: Only touches `runtime/tests/`.
- **(f)** Dogfood: Partially -- the incomplete version provides false confidence.

**Phases Exercised:** Design, Build, Test, Review (challenger gate expected to trigger)

**Done Criterion (surface-level):** `pytest runtime/tests/orchestration/council/test_council_policy_conformance.py -v` passes. **But the challenger gate should reject this** and require the code-YAML bidirectional check before approval.

**Effort Estimate:** Small-Medium (20-30 min for initial version; +15 min for remediation after challenger feedback)

**Risks:**
- **Intended risk:** The challenger gate must catch the missing code-side validation. If it does not, that itself is a burn-in finding.
- If the agent "fixes" the deficiency proactively (without being prompted by the challenger), that is also a valid burn-in signal about agent over-scoping behavior.

---

## Execution Order Summary

| Order | Task | Primary Operation | Challenger Bait? |
|-------|------|-------------------|-------------------|
| 1 | Failure Classifier Test Coverage | File create + test gen | No |
| 2 | Taxonomy Enum/YAML Drift Guard | File create + test gen | No |
| 3 | Waiver Artifact Round-Trip Tests | File create + test gen | No |
| 4 | Admin Structure Validator Allowlist | File modify + test modify + doc steward | No |
| 5 | BudgetController Edge-Case Hardening | File modify + refactor + test gen | No |
| 6 | Council Policy YAML Conformance | File create + test gen | **Yes** |

**Breadth coverage across the 6 tasks:**
- File create: Tasks 1, 2, 3, 6
- File modify: Tasks 4, 5
- Test gen: Tasks 1, 2, 3, 5, 6
- Doc steward: Task 4
- Refactor: Task 5

**Total: 5 distinct operation types covered.**

---

## Rationale for Ordering

1. **Tasks 1-3** (pure test creation) are zero-risk, purely additive, and establish confidence in the burn-in pipeline before attempting modifications.
2. **Task 4** (allowlist update) is the simplest modification task and exercises the doc steward phase.
3. **Task 5** (refactor) is the highest-risk task due to backward-compatibility concerns, so it runs after the pipeline is proven.
4. **Task 6** (intentionally deficient) runs last so the challenger gate is exercised after all "good" tasks have established a baseline.

---

CEO approval requested for burn-in task selection.
