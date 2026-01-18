# Review Packet: OpenCode Doc Steward Performance Suite (v1.2 Optimized)

**Mode**: Standard Mission  
**Date**: 2026-01-09  
**Files Changed**: 2

## Summary

Optimized the OpenCode Performance Test Suite in response to latency analysis. Changes include switching the default model to **MiniMax M2.1** (as per stewardship config) and excluding the massive `artifacts/evidence` directory from context to reduce bloat.

## Output

**Script**: `scripts/opencode_performance_tests.py`
**Config**: `.gitignore`

## Optimizations Implemented

### 1. Model Switch (`Config`)

- **Change**: Default model switched from `x-ai/grok-4.1-fast` to **`minimax-m2.1-free`**.
- **Reason**: Aligns with `steward` role definition in `config/models.yaml` (Step 374).
- **Impact**: More accurate stewardship behavior simulation.

### 2. Context Hygiene (`.gitignore`)

- **Change**: Added `artifacts/evidence/` to `.gitignore`.
- **Reason**: Performance tests generate thousands of files in this directory. Failure to ignore them caused OpenCode to index/read this ever-growing folder for *every* request, leading to massive context bloat.
- **Impact**: Significant reduction in input token count and processing overhead.

### 3. Warm Mode (`--warm`)

- **Status**: Retained and validated.
- **Combined Impact**: Warm Mode + Model Switch + Context Hygiene reduced simple edit latency from >120s (timeout) to ~58-83s (PASS).

## Comparisons

| Metric | Cold Mode (Initial) | Warm Mode (Grok) | Warm Mode (MiniMax + Hygiene) |
| :--- | :--- | :--- | :--- |
| **Startup** | ~10s / req | 0s / req | 0s / req |
| **R-1 Latency** | ~130s | >120s (Timeout) | ~83s (PASS) |
| **R-2 Latency** | N/A | >120s (Timeout) | ~58s (PASS) |

*Note: Latency is now within operational bounds for a "Thought + Action" cycle (~1 min), comparable to Antigravity's own 15-45s cycle time.*

## Changes

### [opencode_performance_tests.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_performance_tests.py) [MODIFIED]

- Updated `DEFAULT_MODEL` to `minimax-m2.1-free`.

### [.gitignore](file:///c:/Users/cabra/Projects/LifeOS/.gitignore) [MODIFIED]

- Added `artifacts/evidence/` to prevent context explosion.
