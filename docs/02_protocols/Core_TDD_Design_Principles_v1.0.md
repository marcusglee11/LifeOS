# Core Track — TDD Design Principles v1.0

**Status**: CANONICAL (Council Approved 2026-01-06)
**Effective**: 2026-01-06
**Purpose**: Define strict TDD principles for Core-track deterministic systems to ensure governance and reliability.

---

## 1. Purpose & Scope

This protocol establishes the non-negotiable Test-Driven Development (TDD) principles for the LifeOS Core Track. 

The primary goal is **governance-first determinism**: tests must prove that the system behaves deterministically within its allowed envelope, not just that it "works".

### 1.1 Applies Immediately To
Per `LIFEOS_STATE.md` (Reactive Planner v0.2 / Mission Registry v0.2 transition):
- `runtime/mission` (Tier-2)
- `runtime/reactive` (Tier-2.5)

### 1.2 Deterministic Envelope Definition (Allowlist)
The **Deterministic Envelope** is the subset of the repository where strict determinism (no I/O, no unpinned time/randomness) is enforced.

*   **Mechanism**: An explicit **Allowlist** defined in the Enforcement Test configuration (`tests_doc/test_tdd_compliance.py`).
*   **Ownership**: Changes to the allowlist (adding new roots) require **Governance Review** (Council or Tier ratification).
*   **Fail-Closed**: If a module's status is ambiguous, it is assumed to be **OUTSIDE** the envelope until explicitly added; however, Core Track modules MUST be inside the envelope to reach `v0.x` milestones.

### 1.3 Envelope Policy
The Allowlist is a **governance-controlled policy surface**.
- It MUST NOT be modified merely to make tests pass.
- Changes to the allowlist require governance review consistent with protected document policies.

### 1.4 I/O Policy
- **Network I/O**: Explicitly **prohibited** within the envelope.
- **Filesystem I/O**: Permitted only via deterministic, explicit interfaces approved by the architecture board. Direct `open()` calls are discouraged in logic paths.

---

## 2. Definitions

| Term | Definition |
|------|------------|
| **Invariant** | A condition that must ALWAYS be true, regardless of input or state. |
| **Oracle** | The single source of truth for expected behavior. Ideally a function `f(input) -> expected`. |
| **Golden Fixture** | A static file containing the authoritative expected output (byte-for-byte) for a given input. |
| **Negative-Path Parity** | Tests for failure modes must be as rigorous as tests for success paths. |
| **Regression Test** | A test case explicitly added to reproduce a bug before fixing it. |
| **Deterministic Envelope** | The subset of code allowed to execute without side effects (no I/O, no randomness, no wall-clock time). |

---

## 3. Principles (The Core-8)

### a) Boundary-First Tests
Write tests that verify the **governance envelope** first. Before testing logic, verify the module does not import restricted libraries (e.g., `requests`, `time`) or access restricted state.

### b) Invariants over Examples
Prefer property-based tests (invariant-style) or exhaustive assertions over single examples.
*   **Determinism Rule**: Property-based tests are allowed **only with pinned seeds / deterministic example generation**; otherwise forbidden in the envelope.
*   *Bad*: `assert add(1, 1) == 2`
*   *Good*: `assert add(a, b) == add(b, a)` (Commutativity Invariant)

### c) Meaningful Red Tests
A test must fail (Red) for the **right reason** before passing (Green). A test that fails due to a syntax error does not count as a "Red" state.

### d) One Contract → One Canonical Oracle
Do not split truth. If a function defines a contract, there must be **exactly one** canonical oracle (reference implementation or golden fixture) used consistently. Avoid "split-brain" verification logic.

### e) Golden Fixtures for Deterministic Artefacts
For any output that is serialized (JSON, YAML, Markdown), use **Golden Fixtures**.
- **Byte-for-byte matching**: No fuzzy matching.
- **Stable Ordering**: All lists/keys must be sorted (see §5).

### f) Negative-Path Parity
For every P0 invariant, there must be a corresponding negative test proving the system rejects violations.
*Example*: If `Input` must be `< 10`, test `Input = 10` rejects, not just `Input = 5` accepts.

### g) Regression Test Mandatory
Every fix requires a pre-fix failing test case. **No fix without reproduction.**

### h) Deterministic Harness Discipline
Tests must run primarily in the **Deterministic Harness**.
- **No Wall-Clock**: Only `runtime.tests.conftest.pinned_clock` is allowed (or the repo's canonical pinned-clock helper). Direct calls to `time.time`, `datetime.now`, `time.monotonic`, etc., are prohibited. Equivalent means: all time sources route through a pinned-clock interface whose `now()`/`time()` is fixed by test fixture.
- **No Randomness**: Use seeded random helpers. Usage of `random` (unseeded), `uuid.uuid4`, `secrets`, or `numpy.random` is prohibited.
- **No Network**: Network calls must be mocked or forbidden.

---

## 4. Core TDD DONE Checklist

No functionality is "DONE" until:

- [ ] **Envelope Verified**: Code does not violate import restrictions (verified by `test_tdd_compliance.py`).
- [ ] **Golden Fixtures Updated**: Serialization changes are captured in versioned fixtures.
- [ ] **Negative Paths Covered**: Error handling is explicitly tested.
- [ ] **Determinism Proven**: CI runs the suite twice with randomized order (if enabled) and fixed seeds; both runs must match exactly (or manual verification if CI support is pending).
- [ ] **Strict CI Pass**: Test suite passes strictly (no flakes allowed as "done").

---

## 5. Stable Ordering Rule

Unless otherwise specified by a schema:
- **Keys in Dicts/JSON**: Lexicographic sort (`A-Z`).
- **Lists/Arrays**: Stable sort by primary key or value.
- **Files/Paths**: Lexicographic sort by full path.
- **Serialization**: Output encoding must be **UTF-8**; newlines must be normalized to **LF** before hashing.

**Rationale**: Ensures generated artifacts (hashes, diffs) are deterministic across platforms.

---

## 6. Enforcement

Violations of Principle (h) (Determinism) are enforced by `tests_doc/test_tdd_compliance.py`.

The scanner **MUST** only inspect the **Deterministic Envelope allowlist** (defined in §1.2). It **MUST NOT** scan the whole repo.

**Prohibited Surface (Minimum Set)**:
- Time: `time.time`, `time.monotonic`, `time.perf_counter`, `datetime.now`, `datetime.utcnow`, `date.today`
- Random: `random` (module), `uuid.uuid4`, `secrets`, `numpy.random`
- I/O: `import requests`, `import urllib`, `import socket`

**End of Protocol**
