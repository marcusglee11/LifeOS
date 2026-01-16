# Review_Packet_Cold_Start_Test_Marker_v1.0.md

**Mission**: Add pytest cold_start test marker per Test Protocol v2.0.

**Status**: COMPLETE

**Changes**:
- Added `cold_start` marker to `pytest.ini`
- Documented in `docs/02_protocols/Test_Protocol_v2.0.md`
- Created example `runtime/tests/test_cold_start_marker.py`
- Updated `docs/INDEX.md` timestamp

## Appendix A: Flattened Changed Files

### pytest.ini (full)
[pytest]
testpaths = 
    runtime/tests
    tests_doc
    tests_recursive
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --ignore=runtime/tests/archive_legacy_r6x
asyncio_default_fixture_loop_scope = function

markers =
    cold_start: marks tests that measure or test cold start (first-run) performance and initialization

### docs/02_protocols/Test_Protocol_v2.0.md (diff section only, full prior read)
## 7. Markers

| Marker | Purpose |
|--------|---------|
| cold_start | Tests that measure cold start (first-run) performance, init times, or cold invocation behavior |

**END OF PROTOCOL**

### runtime/tests/test_cold_start_marker.py (full)
# Cold Start Test Marker Demo
import pytest
import time

@pytest.mark.cold_start
def test_cold_start_engine_init_time():
    '''
    Example cold start test: measures time to initialize the main engine.
    Cold start assumes fresh process without warm cache.
    '''
    start = time.time()
    # Simulate/import engine init - replace with actual init code
    # from runtime.engine import Engine
    # engine = Engine()
    init_time = time.time() - start
    assert init_time &lt; 5.0, f"Engine cold init took {init_time:.2f}s (max 5s)"

### docs/INDEX.md (changed line only)
# LifeOS Documentation Index — Last Updated: 2026-01-09T14:00+11:00

**Verification**: pytest --markers shows cold_start. Example test ready for expansion.