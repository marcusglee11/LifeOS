# Known Failures Gate v1.5 — Evidence Package

**Date**: 2026-01-09T09:31:56Z
**Version**: v1.5
**Status**: ✅ COMPLETE

---

## 1. Environment & Tools

- **System**: Windows 11
- **Python**: 3.12.6
- **Pytest**: v8.3.4
- **Packaging**: `zipfile` (Python) with POSIX paths (`/`)

## 2. Archive Entry List

The ZIP bundle contains the following entries (exact repo-relative paths):
```
artifacts/known_failures/EVIDENCE_PACKAGE.md
artifacts/known_failures/Known_Failures_Ledger_v1.0.md
artifacts/known_failures/MANIFEST.sha256
artifacts/known_failures/known_failures_ledger_v1.0.json
runtime/tests/test_known_failures_gate.py
scripts/check_known_failures_gate.py
```

## 3. Manifest Generation Procedure

The `MANIFEST.sha256` file was generated mechanically using the following logic:
1. Capture 64-hex SHA256 of all payload files.
2. Capture 64-hex SHA256 of this `EVIDENCE_PACKAGE.md` file.
3. Format each line as `<sha256>  <repo_path>` (exactly two spaces).
4. Sort lexicographically by repo path.
5. Exclude `MANIFEST.sha256` and the ZIP bundle hash from the manifest itself.

## 4. Verification Output: Gate Check

**Command**: `python scripts/check_known_failures_gate.py`
**Exit Code**: 0

```
================================================================================
Known Failures Gate Check v1.1
================================================================================
Timestamp: 2026-01-09T20:30:03.394900
Log file: C:\Users\cabra\Projects\LifeOS\artifacts\known_failures\gate_check_output_20260109_203003.txt

Running full test suite...
HEAD failures detected: 24
Pytest return code: 1
Ledger known failures: 24

✅ GATE PASS: No new failures detected.
   HEAD failures: 24
   All failures are documented in ledger.
```

## 5. Verification Output: Unit Tests

**Command**: `python -m pytest runtime/tests/test_known_failures_gate.py -v`
**Exit Code**: 0

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.4, pluggy-1.5.0 -- C:\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\cabra\Projects\LifeOS
configfile: pytest.ini
plugins: anyio-4.7.0, asyncio-1.3.0, cov-6.2.1, mockito-0.0.4
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 16 items

runtime/tests/test_known_failures_gate.py::TestParseFailingNodeids::test_parse_failed_lines PASSED [  6%]
runtime/tests/test_known_failures_gate.py::TestParseFailingNodeids::test_parse_error_lines PASSED [ 12%]
runtime/tests/test_known_failures_gate.py::TestParseFailingNodeids::test_parse_mixed_failed_and_error PASSED [ 18%]
runtime/tests/test_known_failures_gate.py::TestParseFailingNodeids::test_empty_output_returns_empty_set PASSED [ 25%]
runtime/tests/test_known_failures_gate.py::TestParseFailingNodeids::test_all_passing_returns_empty_set PASSED [ 31%]
runtime/tests/test_known_failures_gate.py::TestParseFailingNodeids::test_handles_parametrized_tests PASSED [ 37%]
runtime/tests/test_known_failures_gate.py::TestParseFailingNodeids::test_deterministic_ordering PASSED [ 43%]
runtime/tests/test_known_failures_gate.py::TestCompareFailures::test_identical_sets PASSED [ 50%]
runtime/tests/test_known_failures_gate.py::TestCompareFailures::test_new_failures_detected PASSED [ 56%]
runtime/tests/test_known_failures_gate.py::TestCompareFailures::test_improvements_detected PASSED [ 62%]
runtime/tests/test_known_failures_gate.py::TestCompareFailures::test_mixed_added_and_removed PASSED [ 68%]
runtime/tests/test_known_failures_gate.py::TestCompareFailures::test_empty_head PASSED [ 75%]
runtime/tests/test_known_failures_gate.py::TestCompareFailures::test_empty_ledger PASSED [ 81%]
runtime/tests/test_known_failures_gate.py::TestFailClosedBehavior::test_nonzero_return_with_no_parsed_failures_is_dangerous PASSED [ 87%]
runtime/tests/test_known_failures_gate.py::TestFailClosedBehavior::test_nonzero_return_with_parsed_failures_is_safe PASSED [ 93%]
runtime/tests/test_known_failures_gate.py::TestFailClosedBehavior::test_zero_return_with_no_failures_is_safe PASSED [100%]

============================= 16 passed in 0.13s ==============================
```

---
“Manifest excludes itself and ZIP hash to avoid self-referential recursion; all SHA256 values are full-length (64 hex).”