# Review Packet: BuildWithValidation Mission v0.1

**Date:** 2026-01-13
**Author:** Antigravity worker
**Mission:** Implement BuildWithValidationMission with subprocess smoke-first logic.

## Summary
Successfully implemented the BuildWithValidationMission type, replacing the previous LLM-loop placeholder. The new implementation follows a smoke-first validation pattern, executing compileall as a smoke gate and optionally pytest for full validation. It captures audit-grade evidence (stdout, stderr, exitcode) in a deterministic directory structure indexed by a run token.

## Issue Catalogue
- **I-1: Engine Argument Swap:** Detected a likely bug in engine.py / registry dispatch where MissionContext arguments (repo_root, baseline_commit) are swapped.
  - **Resolution:** Verified mission logic via direct execution and registry-bypass tests. Remediation of engine.py is out of scope for this mission (Non-goal).

## Acceptance Criteria
| ID | Criterion | Status |
|----|-----------|--------|
| AC-1 | CLI mission run build_with_validation returns standard JSON | PASS |
| AC-2 | Smoke mode captures compileall evidence | PASS |
| AC-3 | Deterministic run_token generation | PASS |
| AC-4 | unknown params fail-closed (schema enforced) | PASS |
| AC-5 | Evidence hashes match file contents | PASS |

## Non-Goals
- Repo-wide standardization of capture primitives.
- Fixing the suspected engine.py argument swap bug.

## Changes

| File | Change Type | Note |
|------|-------------|------|
| [build_with_validation_params_v0_1.json](file:///c:/Users/cabra/Projects/LifeOS/runtime/orchestration/missions/schemas/build_with_validation_params_v0_1.json) | NEW | Strict JSON schema for inputs |
| [build_with_validation_result_v0_1.json](file:///c:/Users/cabra/Projects/LifeOS/runtime/orchestration/missions/schemas/build_with_validation_result_v0_1.json) | NEW | Strict JSON schema for outputs |
| [build_with_validation.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/orchestration/missions/build_with_validation.py) | MODIFIED | Replaced placeholder with subprocess logic |
| [test_build_with_validation_mission.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tests/test_build_with_validation_mission.py) | MODIFIED | Updated for new deterministic logic |
| [test_cli_mission.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tests/test_cli_mission.py) | MODIFIED | Added integration coverage |

## Appendix: Flattened Files (Context Snippets)
(Flattened files available in the ZIP bundle and artifacts directory.)
