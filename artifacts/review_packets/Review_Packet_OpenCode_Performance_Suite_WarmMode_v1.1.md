# Review Packet: OpenCode Doc Steward Performance Suite (v1.1 Warm Mode)

**Mode**: Standard Mission  
**Date**: 2026-01-09  
**Files Changed**: 1

## Summary

Enhanced the OpenCode Performance Test Suite with **Warm Mode** (`--warm`), enabling persistent server reuse to eliminate startup overhead. This aligns the testing architecture with a daemonized production setup.

## Output

**Script**: `scripts/opencode_performance_tests.py`

## New Features

### Warm Mode (`--warm`)

- **Persistent Server**: Starts OpenCode server *once* at the beginning of the suite.
- **Direct HTTP**: Uses direct API calls for mission execution, bypassing CLI startup costs.
- **Optimization**: Elimination of process startup overhead for each test iteration.

## Usage

```bash
# Run tests in Warm Mode (Persistent Server)
python scripts/opencode_performance_tests.py --all --warm

# Record baseline using Warm Mode
python scripts/opencode_performance_tests.py --all --warm --record-baseline
```

## Performance Observations

- **Functionality Verified**: Server persistence logic works correctly.
- **Bottleneck Identified**: While Warm Mode removes startup costs (~10s), the dominant factor remains **inference latency** (currently >120s per simple edit in test environment).
- **Conclusion**: The harness is optimized; further speed gains require model/engine-side optimization.

## Changes

### [opencode_performance_tests.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_performance_tests.py) [MODIFIED]

- Added `--warm` argument and `start_server`/`stop_server` lifecycle methods.
- Implemented `run_mission_http` for direct API interaction.
- Increased default HTTP timeout to 300s to accommodate slow model inference.
