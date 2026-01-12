# Test Protocol v2.0

**Status**: WIP (Non-Canonical)  
**Authority**: LifeOS Constitution v2.0 → Core TDD Principles v1.0  
**Effective**: 2026-01-07 (Provisional)  
**Supersedes**: Test Protocol v1.0

---

## 1. Purpose

Defines test governance for LifeOS: categories, coverage requirements, execution rules, and CI integration.

---

## 2. Test Categories

| Category | Location | Purpose |
|----------|----------|--------|
| **Unit** | `runtime/tests/test_*.py` | Module-level correctness |
| **TDD Compliance** | `tests_doc/test_tdd_compliance.py` | Deterministic envelope enforcement |
| **Integration** | `runtime/tests/test_*_integration.py` | Cross-module behaviour |
| **Governance** | `runtime/tests/test_governance_*.py` | Protected surface enforcement |

---

## 3. Coverage Requirements

### 3.1 Core Track (Deterministic Envelope)
- 100% of public functions must have tests
- All invariants must have negative tests (Negative-Path Parity)
- Golden fixtures required for serialized outputs

### 3.2 Support Track
- Coverage goal: 80%+
- Critical paths require tests

---

## 4. Execution Rules

### 4.1 CI Requirements
- All tests run on every PR
- Flaky tests are P0 bugs (no flake tolerance)
- Determinism: suite must pass twice with randomized order

### 4.2 Local Development
- Run relevant tests before commit: `pytest runtime/tests -q`
- TDD compliance check: `pytest tests_doc/test_tdd_compliance.py`

---

## 5. Flake Policy

- **Definition**: Test that passes/fails non-deterministically
- **Response**: Immediate quarantine and P0 fix ticket
- **No skip**: Flakes may not be marked `@pytest.mark.skip` without governance approval

---

## 6. Test Naming

Pattern: `test_<module>_<behaviour>_<condition>`

Example: `test_orchestrator_execute_fails_on_envelope_violation`

---

**END OF PROTOCOL**