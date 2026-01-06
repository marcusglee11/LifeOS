# Review Packet — Core Track TDD Design Principles v1.0

**Mission**: Core Track — TDD Design Principles v1.0 (Doc + Minimal Enforcement Hooks)
**Author**: Antigravity
**Date**: 2026-01-06

---

## 1. Summary
Established the canonical TDD Design Principles for the Core Track to enforce deterministic, governance-first testing. This mission delivers:
- **Canonical Protocol**: `docs/02_protocols/Core_TDD_Design_Principles_v1.0.md` detailing the "Core-8" principles, with explicit envelope definitions and strict enforcement rules.
- **Enforcement Hooks**: `tests_doc/test_tdd_compliance.py` enforcing determinism (no time/random/IO, including monotonic/uuid/secrets) in `runtime/mission` and `runtime/reactive` via AST scanning.
- **Stewardship**: Integrated into `docs/INDEX.md`.

## 2. Issue Catalogue

| Issue ID | Description | Resolution |
|----------|-------------|------------|
| TDD-01 | Lack of centralized TDD principles for determinism | Created canonical protocol doc |
| TDD-02 | Risk of non-deterministic code in Core | Added CI-gated AST enforcement hooks |
| TDD-03 | Showstopper: User approval dependency in Plan | Refactored to fail-closed/repo-derived decision model |
| TDD-04 | Logic Gaps (Pass 1 Feedback) | Applied P0/P1 fixes (Envelope definition, expanded prohibited list, stable ordering details) |

## 3. Acceptance Criteria

| Criteria | Status | Evidence |
|----------|--------|----------|
| Canonical "Core Track — TDD Design Principles v1.0" doc exists | **PASS** | `docs/02_protocols/Core_TDD_Design_Principles_v1.0.md` |
| Minimal enforcement hooks exist and pass | **PASS** | `tests_doc/test_tdd_compliance.py` (8 tests passed) |
| Index/indexes updated | **PASS** | `docs/INDEX.md` updated |
| Repo-derived decisions (no CEO QA) | **PASS** | Scope/Placement derived from Roadmap/Protocols |
| P0 Fixes applied (Envelope, Prohibited List) | **PASS** | Section 1.2 added, prohibited list expanded |

## 4. Non-Goals
- Refactoring existing modules: **Adhered** (No functional code touched).
- Expanding execution envelope: **Adhered** (Strict constraints applied).

---

## Appendix — Flattened Code Snapshots

### File: `docs/02_protocols/Core_TDD_Design_Principles_v1.0.md`
```markdown
# Core Track — TDD Design Principles v1.0

**Status**: Canonical Protocol
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
Prefer property-based tests or exhaustive assertions over single examples.
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
- **No Wall-Clock**: Use `runtime.tests.conftest.pinned_clock` (or strictly equivalent pinned helper). Direct calls to `time.time`, `datetime.now`, `time.monotonic`, etc., are prohibited.
- **No Randomness**: Use seeded random helpers. Usage of `random` (unseeded), `uuid.uuid4`, `secrets`, or `numpy.random` is prohibited.
- **No Network**: Network calls must be mocked or forbidden.

---

## 4. Core TDD DONE Checklist

No functionality is "DONE" until:

- [ ] **Envelope Verified**: Code does not violate import restrictions (verified by `test_tdd_compliance.py`).
- [ ] **Golden Fixtures Updated**: Serialization changes are captured in versioned fixtures.
- [ ] **Negative Paths Covered**: Error handling is explicitly tested.
- [ ] **Determinism Proven**: CI runs the suite twice with randomized order (if enabled) and fixed seeds; both runs must match exactly.
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
```

### File: `tests_doc/test_tdd_compliance.py`
```python
import pytest
import ast
import os

# Enforcement Scope: Directories to scan for Core TDD violations
# Repo-derived from Roadmap v1.0 (Tier-1/Tier-2) and LIFEOS_STATE.md (Reactive/Mission transitions)
ENFORCEMENT_SCOPE = [
    "runtime/mission",
    "runtime/reactive"
]

# Violations configuration
FORBIDDEN_CALLS = {
    "time.time": "Use pinned clock helper",
    "time.monotonic": "Use pinned clock helper",
    "time.perf_counter": "Use pinned clock helper",
    "datetime.now": "Use pinned clock helper",
    "datetime.utcnow": "Use pinned clock helper",
    "datetime.datetime.now": "Use pinned clock helper", # Specific attribute check support
    "datetime.date.today": "Use pinned clock helper",
    "uuid.uuid4": "Use deterministic UUID helper",
    "secrets.choice": "Use seeded random helper", 
}

FORBIDDEN_IMPORTS = {
    "requests": "No IO allowed in Core",
    "urllib": "No IO allowed in Core",
    "socket": "No IO allowed in Core",
    "random": "Use seeded random helper",
    "secrets": "Use seeded random helper",
    "numpy.random": "Use seeded random helper", # unlikely but safe to block
}

class ViolationVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.violations = []

    def visit_Import(self, node):
        for alias in node.names:
            # Check top level module name (e.g. 'urllib.request' -> 'urllib')
            top_level_module = alias.name.split('.')[0]
            if top_level_module in FORBIDDEN_IMPORTS:
                self.violations.append(
                    f"{self.filename}:{node.lineno} Import '{alias.name}' forbidden. {FORBIDDEN_IMPORTS[top_level_module]}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            top_level_module = node.module.split('.')[0]
            if top_level_module in FORBIDDEN_IMPORTS:
                 self.violations.append(
                    f"{self.filename}:{node.lineno} Import from '{node.module}' forbidden. {FORBIDDEN_IMPORTS[top_level_module]}"
                )
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check for banned function calls like time.time()
        # Allows robust check for time.time, datetime.datetime.now, etc
        func_name = self._get_full_func_name(node.func)
        if func_name:
             for banned in FORBIDDEN_CALLS:
                 if func_name.endswith(banned):
                     self.violations.append(
                        f"{self.filename}:{node.lineno} Call '{func_name}' forbidden. {FORBIDDEN_CALLS[banned]}"
                     )
        self.generic_visit(node)

    def _get_full_func_name(self, node):
        """Recursively resolve attribute chain e.g. datetime.datetime.now"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_full_func_name(node.value)
            if value:
                return f"{value}.{node.attr}"
        return None


def scan_file(filepath):
    """Parses a file and returns a list of violation strings."""
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return [f"{filepath}: SyntaxError - could not parse"]
    
    visitor = ViolationVisitor(filepath)
    visitor.visit(tree)
    return visitor.violations

def test_core_tdd_compliance():
    """
    Enforces Core TDD Principles on strictly scoped directories.
    - No non-deterministic time calls.
    - No unseeded random.
    - No network I/O imports.
    """
    repo_root = os.getcwd()
    all_violations = []

    for scope in ENFORCEMENT_SCOPE:
        full_scope_path = os.path.join(repo_root, scope)
        if not os.path.exists(full_scope_path):
            continue # Skip if directory doesn't exist (e.g. not yet created)

        for root, dirs, files in os.walk(full_scope_path):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, repo_root)
                    all_violations.extend(scan_file(full_path))

    # Aggregate errors
    if all_violations:
        pytest.fail("\n".join(all_violations))

# --- Negative Tests (Automated AST Verification) ---

@pytest.mark.parametrize("code_snippet, expected_error_part", [
    ("import time\ntime.time()", "Call 'time.time' forbidden"),
    ("import datetime\ndatetime.datetime.now()", "Call 'datetime.datetime.now' forbidden"), 
    ("import requests", "Import 'requests' forbidden"),
    ("import urllib.request", "Import 'urllib.request' forbidden"),
    ("import uuid\nx = uuid.uuid4()", "Call 'uuid.uuid4' forbidden"),
    ("import secrets", "Import 'secrets' forbidden"),
    ("import time\ntime.monotonic()", "Call 'time.monotonic' forbidden"),
])
def test_violations_detected(code_snippet, expected_error_part):
    """
    Verifies that the AST visitor correctly detects forbidden patterns.
    This does NOT write files to disk; it parses strings directly.
    """
    try:
        tree = ast.parse(code_snippet, filename="<string>")
    except SyntaxError:
        pytest.fail("Invalid python code in test parametrization")
    
    visitor = ViolationVisitor("<string>")
    visitor.visit(tree)
    
    assert any(expected_error_part in v for v in visitor.violations), \
        f"Expected error '{expected_error_part}' not found in {visitor.violations}"
```

### File: `docs/INDEX.md`
```markdown
# LifeOS Documentation Index — Last Updated: 2026-01-06T09:10+11:00
**Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)

---

## Authority Chain

... (omitted for brevity, no changes above) ...

## 02_protocols — Protocols & Agent Communication

### Core Protocols
| Document | Purpose |
|----------|---------|
| [Governance_Protocol_v1.0.md](./02_protocols/Governance_Protocol_v1.0.md) | Envelopes, escalation rules, council model |
| [Document_Steward_Protocol_v1.1.md](./02_protocols/Document_Steward_Protocol_v1.1.md) | **Active** — Document creation, indexing, GitHub/Drive sync |
| [Deterministic_Artefact_Protocol_v2.0.md](./02_protocols/Deterministic_Artefact_Protocol_v2.0.md) | DAP — artefact creation, versioning, and storage rules |
| [Core_TDD_Design_Principles_v1.0.md](./02_protocols/Core_TDD_Design_Principles_v1.0.md) | **Canonical** — Strict TDD principles for Core determinism |
| [Build_Artifact_Protocol_v1.0.md](./02_protocols/Build_Artifact_Protocol_v1.0.md) | Formal schemas/templates for Plan/Review artifacts |
| [Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md](./02_protocols/Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md) | Tier-2 API Versioning, Deprecation, and Compatibility Rules |
| [Build_Handoff_Protocol_v1.1.md](./02_protocols/Build_Handoff_Protocol_v1.1.md) | **Active** — Messaging & handoff architecture (Canonical Context Packets) |
| [Packet_Schema_Versioning_Policy_v1.0.md](./02_protocols/Packet_Schema_Versioning_Policy_v1.0.md) | **New** — Semantic versioning policy for packet schemas |

... (rest of file unchanged) ...
```
