# PASS Report: Build Loop Phase 2 v1.1

**Date**: 2026-01-08T16:53+11:00
**Outcome**: **PASS**

---

## SHA256 Hashes

| Artifact | SHA256 |
|----------|--------|
| `Bundle_Build_Loop_Phase2_v1.1.zip` | `19851b19caa4453012d7ff6e31bcb022e288843d8258b07e5c7eaa929765ed69` |
| `manifest.txt` | `a59d33fa02d5470ada11bb6f56695afed61a2cc6135cbfec423d587a56527420` |
| `Deliverable_Workspace_Build_Loop_Phase2_v1.1.zip` | `9d390b67ceb0ff3cdb5b2d1f6a815670fdc4c94e55edc23fd6805ef42796d52d` |

---

## Audit Gate Result

**Command**: `python scripts/audit_gate_build_loop_phase2.py --zip artifacts/bundles/Bundle_Build_Loop_Phase2_v1.1.zip`

```
============================================================
AUDIT GATE: Build Loop Phase 2 Bundle
============================================================
ZIP: artifacts\bundles\Bundle_Build_Loop_Phase2_v1.1.zip

Extract dir: C:\Users\cabra\AppData\Local\Temp\audit_gate_p2_t1i8zrmq

Gate Checks:
  [OK] G1 ZIP Integrity: PASS
  [OK] G2 ZIP Portability: PASS
  [OK] G3 Manifest Format: PASS
      Valid format, 16 paths sorted
  [OK] G4 Manifest Hashes: PASS
      Verified 16 files
  [OK] G5 Import Sanity: PASS
  [OK] G6 Pytest: PASS
      stdout:
      ============================= test session starts =============================
      platform win32 -- Python 3.12.6, pytest-8.3.4, pluggy-1.5.0
      rootdir: C:\Users\cabra\AppData\Local\Temp\audit_gate_p2_t1i8zrmq
      configfile: pytest.ini
      testpaths: runtime/tests, tests_doc, tests_recursive
      plugins: anyio-4.7.0, asyncio-1.3.0, cov-6.2.1, mockito-0.0.4
      asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
      collected 58 items

      runtime\tests\test_envelope_enforcer.py ...ss.......                     [ 20%]
      runtime\tests\test_mission_journal.py ..........                         [ 37%]
      runtime\tests\test_operations.py .................                       [ 67%]
      runtime\tests\test_self_mod_protection.py ...................            [100%]

      ======================== 56 passed, 2 skipped in 0.13s ========================

============================================================
SUMMARY: 6 PASS, 0 FAIL, 0 BLOCKED
RESULT: PASS
```

---

## Pytest Result

**Command**: `python -m pytest -q`
**Result**: `56 passed, 2 skipped in 0.13s`

---

## Extracted Files (sorted, forward slashes)

```
docs/03_runtime/Implementation_Plan_Build_Loop_Phase2_v1.1.md
docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md
manifest.txt
pytest.ini
runtime/__init__.py
runtime/governance/__init__.py
runtime/governance/envelope_enforcer.py
runtime/governance/self_mod_protection.py
runtime/orchestration/__init__.py
runtime/orchestration/mission_journal.py
runtime/orchestration/operations.py
runtime/tests/__init__.py
runtime/tests/test_envelope_enforcer.py
runtime/tests/test_mission_journal.py
runtime/tests/test_operations.py
runtime/tests/test_self_mod_protection.py
scripts/audit_gate_build_loop_phase2.py
```

---

## Notes

1. **Test result alignment**: Plan states "56 passed, 2 skipped" — matches actual result. No correction needed.
2. **2 skipped tests**: Symlink tests (`test_symlink_rejected_when_enabled`, `test_symlink_allowed_when_disabled`) are skipped on Windows due to admin requirements.
3. **manifest.txt**: Enumerates 16 tracked files (excludes itself from hash verification).

---

**END OF PASS REPORT**
