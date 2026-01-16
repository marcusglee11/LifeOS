# Review Packet — Mission Registry v0.2 (Synthesis + Validation)

**Mission:** Core — Mission Registry v0.2 (Synthesis + Validation) via TDD  
**Date:** 2026-01-06  
**Author:** Antigravity  
**Version:** 1.0  
**Status:** READY FOR REVIEW  

---

## Summary

Implemented Mission Registry v0.2 adding deterministic mission synthesis and explicit validation entrypoints. All 64 tests pass (40 v0.1 + 24 v0.2). v0.1 backward compatibility fully preserved.

## Issue Catalogue

| ID | Issue | Resolution |
|----|-------|------------|
| P0 | Context acquisition | ✅ Located v0.1 impl, tests, council ruling |
| P1 | v0.2 contract | ✅ Defined synthesis pattern (validate→build→validate) |
| P2 | TDD suite | ✅ 24 tests across 7 cycles |
| P3 | Implementation | ✅ `synthesis.py` with deterministic assembly |
| P4 | Docs | ✅ README v0.2 delta section added |

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Synthesis function exists | ✅ PASS | `synthesize_mission()` in `synthesis.py` |
| Covered by deterministic golden tests | ✅ PASS | Golden hash: `4907f6d1...` |
| Validation entrypoint exists | ✅ PASS | `validate()` exported |
| Rejects 5+ invalid cases | ✅ PASS | 7 cases: empty ID, whitespace ID, long ID, empty name, long name, invalid metadata, too many tags |
| Test suite passes | ✅ PASS | 64 passed in 0.11s |
| v0.1 backward compatible | ✅ PASS | All 40 v0.1 tests still pass |
| Minimal doc update | ✅ PASS | README v0.2 delta section |

## Non-Goals (Explicit)

- ❌ No execution logic — definitions only
- ❌ No Reactive Planner integration — separate scope
- ❌ No timestamp/version injection — explicit inputs only
- ❌ No dynamic registry mutation — immutable pattern

---

## Files Changed

### New Files

| File | Purpose |
|------|---------|
| [synthesis.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/mission/synthesis.py) | v0.2 synthesis + validation module |
| [test_mission_registry_v0_2.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tests/test_mission_registry/test_mission_registry_v0_2.py) | 24 TDD tests |

### Modified Files

| File | Change |
|------|--------|
| [__init__.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/mission/__init__.py) | Added v0.2 exports |
| [README.md](file:///c:/Users/cabra/Projects/LifeOS/runtime/mission/README.md) | Added v0.2 delta section |

---

## Evidence Package

### Test Report

```
============================= 64 passed in 0.11s ==============================

v0.1 tests: 40 passed
v0.2 tests: 24 passed
```

### Determinism Proof

```
RUN1: 4907f6d1d305089e05d16cb3e89fde4b7b200db8173b3734e2ebebe2222751b7
RUN2: 4907f6d1d305089e05d16cb3e89fde4b7b200db8173b3734e2ebebe2222751b7

MATCH: ✅ Identical hashes confirm deterministic synthesis
```

### v0.2 Test Categories

| Cycle | Tests | Status |
|-------|-------|--------|
| 1: Public API | 3 | ✅ PASS |
| 2: Schema | 3 | ✅ PASS |
| 3: Determinism | 4 | ✅ PASS |
| 4: Invariant Validation | 7 | ✅ PASS |
| 5: Validate Entrypoint | 3 | ✅ PASS |
| 6: Error Taxonomy | 2 | ✅ PASS |
| 7: Golden Fixture | 2 | ✅ PASS |

---

## Appendix — Flattened Code Snapshots

### File: `runtime/mission/synthesis.py`

```python
"""
Mission Registry v0.2 — Synthesis + Validation

Deterministic mission synthesis from structured inputs.
No I/O, no side effects, no timestamps, no randomness.

v0.2 Contract:
- Input: MissionSynthesisRequest (structured, explicit fields)
- Output: MissionDefinition (validated, deterministic)
- Validation: Hard failures for governance MUSTs

Pattern follows reactive layer: validate → build → validate
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from runtime.mission.interfaces import (
    MissionId,
    MissionDefinition,
)
from runtime.mission.boundaries import (
    MissionBoundaryViolation,
    MissionBoundaryConfig,
    validate_mission_id,
    validate_mission_definition,
)


@dataclass(frozen=True)
class MissionSynthesisRequest:
    """Structured request for mission synthesis."""
    id: str
    name: str
    description: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: Optional[Dict[str, str]] = None


def _validate_request(
    request: MissionSynthesisRequest,
    config: MissionBoundaryConfig,
) -> None:
    """Validate a synthesis request before building."""
    if not request.id or len(request.id.strip()) == 0:
        raise MissionBoundaryViolation("mission id must not be empty")
    if len(request.id) > config.max_id_chars:
        raise MissionBoundaryViolation(
            f"Mission ID exceeds max length of {config.max_id_chars}"
        )
    if not request.name or len(request.name.strip()) == 0:
        raise MissionBoundaryViolation("name must not be empty")
    if len(request.name) > config.max_name_chars:
        raise MissionBoundaryViolation(
            f"name exceeds {config.max_name_chars} chars"
        )
    if len(request.description) > config.max_description_chars:
        raise MissionBoundaryViolation(
            f"description exceeds {config.max_description_chars} chars"
        )
    if len(request.tags) > config.max_tags:
        raise MissionBoundaryViolation(
            f"too many tags: {len(request.tags)} > {config.max_tags}"
        )
    for i, tag in enumerate(request.tags):
        if not isinstance(tag, str):
            raise MissionBoundaryViolation(
                f"tag[{i}] must be str, got {type(tag).__name__}"
            )
        if len(tag) > config.max_tag_chars:
            raise MissionBoundaryViolation(
                f"tag[{i}] exceeds {config.max_tag_chars} chars"
            )
    if request.metadata is not None:
        if len(request.metadata) > config.max_metadata_pairs:
            raise MissionBoundaryViolation(
                f"too many metadata pairs: {len(request.metadata)} > {config.max_metadata_pairs}"
            )
        for key, value in request.metadata.items():
            if not isinstance(key, str):
                raise MissionBoundaryViolation(
                    f"metadata key must be str, got {type(key).__name__}"
                )
            if not isinstance(value, str):
                raise MissionBoundaryViolation(
                    f"metadata value for '{key}' must be str, got {type(value).__name__}"
                )
            if len(key) > config.max_metadata_key_chars:
                raise MissionBoundaryViolation(
                    f"metadata key '{key}' exceeds {config.max_metadata_key_chars} chars"
                )
            if len(value) > config.max_metadata_value_chars:
                raise MissionBoundaryViolation(
                    f"metadata value for '{key}' exceeds {config.max_metadata_value_chars} chars"
                )


def _build_definition(request: MissionSynthesisRequest) -> MissionDefinition:
    """Build a MissionDefinition from a validated request."""
    metadata_tuple: tuple[tuple[str, str], ...] = ()
    if request.metadata:
        sorted_items = sorted(request.metadata.items(), key=lambda x: x[0])
        metadata_tuple = tuple(sorted_items)
    return MissionDefinition(
        id=MissionId(value=request.id),
        name=request.name,
        description=request.description,
        tags=request.tags,
        metadata=metadata_tuple,
    )


def synthesize_mission(
    request: MissionSynthesisRequest,
    config: Optional[MissionBoundaryConfig] = None,
) -> MissionDefinition:
    """THE SINGLE EXTERNAL ENTRYPOINT for v0.2 mission synthesis."""
    if config is None:
        config = MissionBoundaryConfig()
    _validate_request(request, config)
    defn = _build_definition(request)
    validate_mission_definition(defn, config)
    return defn


def validate(
    defn: MissionDefinition,
    config: Optional[MissionBoundaryConfig] = None,
) -> None:
    """Validate a mission definition."""
    if config is None:
        config = MissionBoundaryConfig()
    validate_mission_definition(defn, config)
```

### File: `runtime/mission/__init__.py` (v0.2 additions)

```diff
+# v0.2 synthesis API
+from runtime.mission.synthesis import (
+    MissionSynthesisRequest,
+    synthesize_mission,
+    validate,
+)

 __all__ = [
     ...
+    # v0.2 Synthesis API
+    "MissionSynthesisRequest",
+    "synthesize_mission",
+    "validate",
 ]
```

---

## DONE Definition Checklist

- [x] Mission Registry v0.2 synthesis function exists and is covered by deterministic golden tests
- [x] Mission Registry v0.2 validation entrypoint exists and rejects at least 5 representative invalid cases
- [x] Test suite passes in a clean run (64 passed)
- [x] Minimal doc update completed (v0.2 delta + pointer to tests)
- [x] Evidence package complete (test report, determinism proof, discovery notes)
