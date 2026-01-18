# TEST_REPORT: G-CBS Promotion Admissible (v0.2)

**Date**: 2026-01-06T22:25:00+11:00
**Mission**: FixPack v0.3 — Counting Rule Consistency
**Status**: PASS

---

## 1. Governance Evidence

**Activated Index**: `docs/01_governance/ARTEFACT_INDEX.json`
**Version**: 3.2.0
**SHA256 (Raw Bytes)**: `5A5B11D89F234DEF7CFE812C57364F3C5BBD4769A389674802D7B80FA0E67EB7`

### Counting Rule (verbatim from meta)

```
artefacts_count = count of non-comment keys in 'artefacts'
protocols_count = count of keys whose path starts with 'docs/02_protocols/'
```

### Derivation

```python
import json
with open('docs/01_governance/ARTEFACT_INDEX.json', 'r') as f:
    data = json.load(f)
artefacts = data['artefacts']
non_comment = [k for k in artefacts.keys() if not k.startswith('_')]
protocols = [k for k in non_comment if artefacts[k].startswith('docs/02_protocols/')]
print(f'Non-comment keys: {len(non_comment)}')  # 20
print(f'Protocol keys: {len(protocols)}')        # 9
```

### Computed Counts

| Metric | Value |
|--------|-------|
| Non-comment keys | 20 |
| Protocol paths | 9 |
| Meta description | "20 artefacts, 9 protocols" |

**Status**: MATCH

---

## 2. Test Execution Results

### 2.1 TDD Compliance

**Command**: `pytest tests_doc/test_tdd_compliance.py -v`
**Result**: 12/12 PASSED

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.4, pluggy-1.5.0
collected 12 items

tests_doc/test_tdd_compliance.py::test_core_tdd_compliance PASSED        [  8%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[import time\ntime.time()-Call 'time.time' forbidden] PASSED [ 16%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[import datetime\ndatetime.datetime.now()-Call 'datetime.datetime.now' forbidden] PASSED [ 25%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[import requests-Import 'requests' forbidden] PASSED [ 33%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[import urllib.request-Import 'urllib.request' forbidden] PASSED [ 41%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[import uuid\nx = uuid.uuid4()-Call 'uuid.uuid4' forbidden] PASSED [ 50%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[import secrets-Import 'secrets' forbidden] PASSED [ 58%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[import time\ntime.monotonic()-Call 'time.monotonic' forbidden] PASSED [ 66%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[eval('os.system("rm -rf")')-Call 'eval' forbidden] PASSED [ 75%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[exec('import os')-Call 'exec' forbidden] PASSED [ 83%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[__import__('os')-Call '__import__' forbidden] PASSED [ 91%]
tests_doc/test_tdd_compliance.py::test_violations_detected_selftest[import importlib\nimportlib.import_module('os')-Import 'importlib' forbidden] PASSED [100%]

============================= 12 passed in 0.07s ==============================
```

### 2.2 Closure Bundle Regression Suite

**Command**: `pytest scripts/closure/tests/test_gcbs_a1a2_regressions.py -v`
**Result**: 11/11 PASSED

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.4, pluggy-1.5.0
collected 11 items

scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestDetachedDigest::test_detached_digest_happy_path PASSED [  9%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestDetachedDigest::test_detached_digest_missing PASSED [ 18%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestDetachedDigest::test_detached_digest_mismatch PASSED [ 27%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestZipDeterminism::test_bundle_zip_is_deterministic PASSED [ 36%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestEvidenceHygiene::test_no_transient_paths PASSED [ 45%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestLegacies::test_posix_path_accepted PASSED [ 54%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestLegacies::test_sha_mismatch_rejected PASSED [ 63%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestLegacies::test_truncation_token_rejected PASSED [ 72%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestLegacies::test_validator_transcript_completeness PASSED [ 81%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestProvenanceAndVersioning::test_provenance_hash_mismatch_fails PASSED [ 90%]
scripts/closure/tests/test_gcbs_a1a2_regressions.py::TestProvenanceAndVersioning::test_missing_gcbs_standard_version_fails_closed PASSED [100%]

============================= 11 passed in 2.37s ==============================
```

### 2.3 Governance Index Validation

**Command**: `python tools/validate_governance_index.py`
**Result**: PASSED

```
Validating governance index at: C:\Users\cabra\Projects\LifeOS

[PASSED] Validation passed: All artefacts valid and files exist.
```

---

## 3. Changes from v0.2

| Change | Rationale |
|--------|-----------|
| ARTEFACT_INDEX counts 17→20 | Original count was wrong; 20 non-comment keys exist |
| docs/INDEX.md reverted | Out-of-scope for this fix pack |
| Version bump 3.1.0→3.2.0 | Counts corrected |

---

## 4. Conclusion

All requirements satisfied:
- [x] Counts reproducible (20 artefacts, 9 protocols)
- [x] counting_rule explicit in meta
- [x] Test report totals match ARTEFACT_INDEX
- [x] docs/INDEX.md changes reverted
- [x] All tests PASS
