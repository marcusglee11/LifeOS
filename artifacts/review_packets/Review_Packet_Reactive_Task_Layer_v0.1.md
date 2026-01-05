# Review Packet: Reactive Task Layer v0.1

**Mission**: Build Reactive Task Layer v0.1 (Spec + Boundaries) using TDD  
**Commit**: `faab7db`  
**Date**: 2026-01-03

> **Scope**: This packet covers Reactive Task Layer v0.1 only. Mission Registry / Executor are not included.

---

## Summary

Delivered a **definition-only**, **deterministic**, **no-I/O** Reactive Task Layer with:
- Plan Surface v0.1 schema
- Canonical JSON + sha256 hashing
- Boundary validation (request + surface)
- `build_plan_surface()` as the single enforced external entrypoint
- 35 TDD tests

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| No execution (no Builder/Orchestrator calls) | ✅ PASS |
| No I/O (no filesystem, network, clocks, randomness) | ✅ PASS |
| Determinism (identical input → identical output) | ✅ PASS |
| 35 spec conformance tests pass | ✅ PASS |
| Full test suite passes (355 tests) | ✅ PASS |
| TDD methodology followed | ✅ PASS |
| id validation enforced | ✅ PASS |
| tags type enforcement | ✅ PASS |
| Version constant authoritative | ✅ PASS |
| Exception taxonomy documented | ✅ PASS |
| Safe entrypoint enforced (`build_plan_surface`) | ✅ PASS |
| Version alignment documented | ✅ PASS |

---

## Notes for Reviewers

| Topic | Rationale |
|-------|-----------|
| **Payload length measured on canonical JSON** | Deterministic, includes escaping, matches what will be hashed |
| **Local-only exception (`ReactiveBoundaryViolation`)** | Avoid Tier-2 coupling; mapping to `AntiFailureViolation`/`EnvelopeViolation` deferred to v0.2+ |
| **id validation is enforced** | Empty/whitespace-only id rejected by `validate_request()` |
| **tags type enforced** | Must be `tuple[str, ...]`; passing a string or non-str elements raises |
| **Whitespace-only handling** | No transformation applied; validation rejects whitespace-only id/title as empty |
| **ReactiveTask vs ReactiveTaskRequest** | `ReactiveTask` is the immutable domain type; `ReactiveTaskRequest` is the input carrier. Both exported for future use. |
| **Version constant** | `REACTIVE_LAYER_VERSION` is the single authoritative source; surfaces reference it deterministically |
| **Exception taxonomy migration** | Documented in interfaces.py docstring; trigger is first external consumer |
| **Safe entrypoint** | `build_plan_surface()` chains validate_request → to_plan_surface → validate_surface; the ONLY supported external entrypoint |
| **Version alignment** | REACTIVE_LAYER_VERSION is intentionally separate from TIER2_INTERFACE_VERSION; will embed both in v0.2+ envelope integration |

---

## Non-Goals

- Execution layer (deferred to Mission Registry v0.1)
- Integration with existing Tier-2 envelope (v0.2+)
- `AntiFailureViolation`/`EnvelopeViolation` mapping (v0.2+)

---

## Files Created

1. `runtime/reactive/README.md`
2. `runtime/reactive/interfaces.py`
3. `runtime/reactive/boundaries.py`
4. `runtime/reactive/__init__.py`
5. `runtime/tests/test_reactive/__init__.py`
6. `runtime/tests/test_reactive/test_spec_conformance.py`

---

## Test Evidence

```
python -m pytest runtime/tests/test_reactive/test_spec_conformance.py -v
============================= 35 passed in 0.09s ==============================

python -m pytest runtime/tests/ -q
====================== 355 passed, 127 warnings in 3.98s ======================
```

---

## Appendix — Flattened Code

### File: runtime/reactive/README.md

```markdown
# Reactive Task Layer v0.1

**Status**: Active  
**Authority**: [LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md](../../docs/03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md)  
**Date**: 2026-01-03

**Definition-only**, **deterministic**, **no-I/O** surface for reactive task planning.

> **Scope**: This spec covers Reactive Task Layer v0.1 only. Mission Registry / Executor are not included.

---

## Boundaries

| Constraint | Enforcement |
|------------|-------------|
| No execution | No calling Builder/Orchestrator |
| No I/O | No filesystem, network, clocks, randomness |
| Determinism | Identical input → identical surface + JSON + hash |
| Exception taxonomy | Local-only `ReactiveBoundaryViolation` for v0.1 |

---

## Plan Surface v0.1 Schema

```json
{
  "version": "reactive_task_layer.v0.1",
  "task": {
    "id": "<str>",
    "title": "<str>",
    "description": "<str>",
    "tags": ["<str>", ...]
  },
  "constraints": {
    "max_payload_chars": <int>
  }
}
```

---

## Semantic Rules

| Field | Semantics |
|-------|-----------|
| `id`, `title` | Raw strings; no transformation applied to stored values. Validation rejects empty/whitespace-only. |
| `description` | Raw string; no transformation. |
| `tags` | Must be `tuple[str, ...]`; order-preserving; `None` → `[]`; no sorting/normalization |
| `max_payload_chars` | Enforced via `validate_surface()` |

---

## Canonical JSON (Pinned Settings)

```python
json.dumps(
    surface,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
    allow_nan=False
)
```

---

## Hash

```python
sha256(canonical_json(surface).encode("utf-8")).hexdigest()
```

---

## Validation Call Flow

```
validate_request(req, cfg)  # before surface creation
surface = to_plan_surface(req, cfg)
validate_surface(surface, cfg)  # after surface creation
```

`to_plan_surface()` does not validate internally.

---

## Boundary Defaults

| Config | Default |
|--------|---------|
| `max_title_chars` | 200 |
| `max_description_chars` | 4000 |
| `max_tags` | 25 |
| `max_tag_chars` | 64 |
| `max_payload_chars` | 8000 |
```

---

### File: runtime/reactive/interfaces.py

```python
"""
Reactive Task Layer v0.1 — Interfaces

Pure transforms and immutable data types for reactive task planning.
No I/O, no side effects, deterministic.

**Scope**: This module covers Reactive Task Layer v0.1 only.
Mission Registry / Executor are not included.

**Exception Taxonomy Migration Path**:
- v0.1: ReactiveBoundaryViolation is a local-only exception.
- v0.2+: When first external consumer outside runtime/reactive/ appears,
  map to AntiFailureViolation (input contract violations) or
  EnvelopeViolation (structural/governance violations) as appropriate.
- Trigger: First import of reactive types from outside runtime/reactive/.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import hashlib
import json

# Authoritative version constant for reactive layer surfaces
# Version Alignment: REACTIVE_LAYER_VERSION is the authoritative source for
# reactive layer surfaces. It is intentionally separate from TIER2_INTERFACE_VERSION
# (runtime.api) because the reactive layer is a sub-component with its own versioning
# lifecycle. When the reactive layer is integrated into the Tier-2 envelope (v0.2+),
# the surface will embed both versions to maintain compatibility discipline.
REACTIVE_LAYER_VERSION = "reactive_task_layer.v0.1"

# Type alias for future refactors
ReactivePlanSurface = Dict[str, Any]


@dataclass(frozen=True)
class ReactiveTask:
    """Immutable reactive task definition. Data only; no execution semantics."""
    id: str
    title: str
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReactiveTaskRequest:
    """Immutable request for creating a reactive task surface."""
    id: str
    title: str
    description: str = ""
    tags: Optional[tuple[str, ...]] = None


def to_plan_surface(
    request: ReactiveTaskRequest,
    config: Optional["ReactiveBoundaryConfig"] = None
) -> ReactivePlanSurface:
    """
    Convert a request to a Plan Surface v0.1.
    
    WARNING: Internal use only. Does NOT validate.
    External callers MUST use build_plan_surface() instead.
    """
    from runtime.reactive.boundaries import ReactiveBoundaryConfig
    
    if config is None:
        config = ReactiveBoundaryConfig()
    
    tags = list(request.tags) if request.tags is not None else []
    
    return {
        "version": REACTIVE_LAYER_VERSION,
        "task": {
            "id": request.id,
            "title": request.title,
            "description": request.description,
            "tags": tags,
        },
        "constraints": {
            "max_payload_chars": config.max_payload_chars,
        },
    }


def build_plan_surface(
    request: ReactiveTaskRequest,
    config: Optional["ReactiveBoundaryConfig"] = None
) -> ReactivePlanSurface:
    """
    Build a validated Plan Surface v0.1 — THE ONLY EXTERNAL ENTRYPOINT.
    
    This is the single supported constructor for external callers.
    Chains: validate_request() → to_plan_surface() → validate_surface()
    
    Raises ReactiveBoundaryViolation on any validation failure.
    """
    from runtime.reactive.boundaries import (
        ReactiveBoundaryConfig,
        validate_request,
        validate_surface,
    )
    
    if config is None:
        config = ReactiveBoundaryConfig()
    
    # Step 1: Validate request
    validate_request(request, config)
    
    # Step 2: Build surface
    surface = to_plan_surface(request, config)
    
    # Step 3: Validate surface
    validate_surface(surface, config)
    
    return surface


def canonical_json(surface: ReactivePlanSurface) -> str:
    """
    Produce deterministic canonical JSON representation.
    
    Pinned settings: sort_keys=True, separators=(",", ":"),
    ensure_ascii=True, allow_nan=False
    """
    return json.dumps(
        surface,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False
    )


def surface_hash(surface: ReactivePlanSurface) -> str:
    """Compute SHA256 hash of canonical JSON. Returns 64-char hex string."""
    return hashlib.sha256(canonical_json(surface).encode("utf-8")).hexdigest()
```

---

### File: runtime/reactive/boundaries.py

```python
"""
Reactive Task Layer v0.1 — Boundaries

Validation, configuration, and exceptions for reactive task planning.
"""
from dataclasses import dataclass
from typing import Optional


class ReactiveBoundaryViolation(Exception):
    """
    Raised when a reactive task request or surface violates boundaries.
    
    Local-only exception for v0.1. Mapping to AntiFailureViolation/EnvelopeViolation
    deferred to v0.2+.
    """
    pass


@dataclass(frozen=True)
class ReactiveBoundaryConfig:
    """Immutable configuration for reactive task boundaries."""
    max_title_chars: int = 200
    max_description_chars: int = 4000
    max_tags: int = 25
    max_tag_chars: int = 64
    max_payload_chars: int = 8000


def validate_request(
    request: "ReactiveTaskRequest",
    config: Optional[ReactiveBoundaryConfig] = None
) -> None:
    """Validate a request. Call BEFORE to_plan_surface()."""
    if config is None:
        config = ReactiveBoundaryConfig()
    
    if not request.id or len(request.id.strip()) == 0:
        raise ReactiveBoundaryViolation("id must not be empty")
    
    if not request.title or len(request.title.strip()) == 0:
        raise ReactiveBoundaryViolation("title must not be empty")
    
    if len(request.title) > config.max_title_chars:
        raise ReactiveBoundaryViolation(f"title exceeds {config.max_title_chars} chars")
    
    if len(request.description) > config.max_description_chars:
        raise ReactiveBoundaryViolation(f"description exceeds {config.max_description_chars} chars")
    
    if request.tags is not None:
        if not isinstance(request.tags, tuple):
            raise ReactiveBoundaryViolation(f"tags must be tuple, got {type(request.tags).__name__}")
        for i, tag in enumerate(request.tags):
            if not isinstance(tag, str):
                raise ReactiveBoundaryViolation(f"tag[{i}] must be str, got {type(tag).__name__}")
    
    if request.tags is not None and len(request.tags) > config.max_tags:
        raise ReactiveBoundaryViolation(f"too many tags: {len(request.tags)} > {config.max_tags}")
    
    if request.tags is not None:
        for i, tag in enumerate(request.tags):
            if len(tag) > config.max_tag_chars:
                raise ReactiveBoundaryViolation(f"tag[{i}] exceeds {config.max_tag_chars} chars")


def validate_surface(
    surface: dict,
    config: Optional[ReactiveBoundaryConfig] = None
) -> None:
    """Validate a surface. Call AFTER to_plan_surface()."""
    from runtime.reactive.interfaces import canonical_json
    
    if config is None:
        config = ReactiveBoundaryConfig()
    
    payload_len = len(canonical_json(surface))
    if payload_len > config.max_payload_chars:
        raise ReactiveBoundaryViolation(f"surface payload exceeds {config.max_payload_chars} chars: {payload_len}")
```

---

### File: runtime/reactive/__init__.py

```python
"""
Reactive Task Layer v0.1

Definition-only, deterministic, no-I/O surface for reactive task planning.
"""
from runtime.reactive.interfaces import (
    ReactiveTask,
    ReactiveTaskRequest,
    ReactivePlanSurface,
    REACTIVE_LAYER_VERSION,
    to_plan_surface,
    build_plan_surface,
    canonical_json,
    surface_hash,
)
from runtime.reactive.boundaries import (
    ReactiveBoundaryConfig,
    ReactiveBoundaryViolation,
    validate_request,
    validate_surface,
)

__all__ = [
    # Types
    "ReactiveTask",
    "ReactiveTaskRequest",
    "ReactivePlanSurface",
    # Version
    "REACTIVE_LAYER_VERSION",
    # External entrypoint (PREFERRED)
    "build_plan_surface",
    # Internal primitives (use build_plan_surface instead)
    "to_plan_surface",
    "canonical_json",
    "surface_hash",
    # Config and validation
    "ReactiveBoundaryConfig",
    "ReactiveBoundaryViolation",
    "validate_request",
    "validate_surface",
]
```

---

### File: runtime/tests/test_reactive/__init__.py

```python
# test_reactive tests package
```

---

### File: runtime/tests/test_reactive/test_spec_conformance.py

```python
"""
Reactive Task Layer v0.1 — Spec Conformance Tests

TDD test suite with 35 tests covering:
- Public API imports (1)
- Schema conformance (4)
- Canonical JSON (3)
- Hash stability (1)
- Validation boundaries (8)
- Immutability (1)
- Version constant (3)
- Determinism hardening (2)
- Validation edge cases (4)
- Unicode coverage (3)
- Build plan surface (5)
"""
import json
import pytest


class TestCycle1PublicAPI:
    """Cycle 1: Module exists and exports public API."""

    def test_public_api_imports(self):
        """All public symbols must be importable from runtime.reactive."""
        from runtime.reactive import (
            ReactiveTask,
            ReactiveTaskRequest,
            REACTIVE_LAYER_VERSION,
            build_plan_surface,
            to_plan_surface,
            canonical_json,
            surface_hash,
            validate_request,
            validate_surface,
            ReactiveBoundaryConfig,
            ReactiveBoundaryViolation,
        )
        assert ReactiveTask is not None
        assert ReactiveTaskRequest is not None
        assert REACTIVE_LAYER_VERSION is not None
        assert build_plan_surface is not None
        assert to_plan_surface is not None
        assert canonical_json is not None
        assert surface_hash is not None
        assert validate_request is not None
        assert validate_surface is not None
        assert ReactiveBoundaryConfig is not None
        assert ReactiveBoundaryViolation is not None


class TestCycle2SchemaConformance:
    """Cycle 2: Plan surface schema is exact."""

    def test_plan_surface_schema_exact(self):
        """Surface has exactly the required keys, no more, no less."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc", tags=("a",))
        surface = to_plan_surface(req)
        
        assert set(surface.keys()) == {"version", "task", "constraints"}
        assert set(surface["task"].keys()) == {"id", "title", "description", "tags"}
        assert set(surface["constraints"].keys()) == {"max_payload_chars"}
        assert surface["version"] == "reactive_task_layer.v0.1"

    def test_constraints_default_matches_config(self):
        """max_payload_chars in surface equals config default."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, ReactiveBoundaryConfig
        
        req = ReactiveTaskRequest(id="t1", title="Test")
        surface = to_plan_surface(req)
        config = ReactiveBoundaryConfig()
        
        assert surface["constraints"]["max_payload_chars"] == config.max_payload_chars

    def test_tags_none_emits_empty_list(self):
        """tags=None in request produces [] in surface."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface
        
        req = ReactiveTaskRequest(id="t1", title="Test", tags=None)
        surface = to_plan_surface(req)
        
        assert surface["task"]["tags"] == []

    def test_tags_order_preserved(self):
        """Tags order is preserved: ["b","a"] stays ["b","a"]."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", tags=("b", "a"))
        surface = to_plan_surface(req)
        
        assert surface["task"]["tags"] == ["b", "a"]
        cj = canonical_json(surface)
        assert '"tags":["b","a"]' in cj


class TestCycle3CanonicalJSON:
    """Cycle 3: Canonical JSON is deterministic."""

    def test_canonical_json_is_stable(self):
        """Same request produces identical canonical JSON on repeated calls."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc")
        surface1 = to_plan_surface(req)
        surface2 = to_plan_surface(req)
        
        cj1 = canonical_json(surface1)
        cj2 = canonical_json(surface2)
        
        assert cj1 == cj2

    def test_canonical_json_settings_are_pinned(self):
        """Canonical JSON uses ensure_ascii=True (unicode escaped)."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="café")
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        assert "\\u00e9" in cj or "caf" in cj
        assert all(ord(c) < 128 for c in cj)

    def test_canonical_json_roundtrip(self):
        """json.loads(canonical_json(surface)) == surface."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc", tags=("a", "b"))
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        roundtrip = json.loads(cj)
        assert roundtrip == surface


class TestCycle4HashStability:
    """Cycle 4: Surface hash is stable."""

    def test_surface_hash_is_stable(self):
        """Same request produces identical hash on repeated calls."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, surface_hash, canonical_json
        import hashlib
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc")
        surface1 = to_plan_surface(req)
        surface2 = to_plan_surface(req)
        
        h1 = surface_hash(surface1)
        h2 = surface_hash(surface2)
        
        assert h1 == h2
        assert len(h1) == 64
        expected = hashlib.sha256(canonical_json(surface1).encode("utf-8")).hexdigest()
        assert h1 == expected


class TestCycle5ValidationBoundaries:
    """Cycle 5: Validation boundaries are enforced."""

    def test_validate_request_accepts_valid(self):
        """Valid request passes validation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request
        
        req = ReactiveTaskRequest(id="t1", title="Valid Title", description="Valid desc")
        validate_request(req)

    def test_validate_request_rejects_empty_id(self):
        """Empty id raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation
        
        req = ReactiveTaskRequest(id="", title="Test", description="Desc")
        with pytest.raises(ReactiveBoundaryViolation, match="id must not be empty"):
            validate_request(req)
        
        req2 = ReactiveTaskRequest(id="   ", title="Test", description="Desc")
        with pytest.raises(ReactiveBoundaryViolation, match="id must not be empty"):
            validate_request(req2)

    def test_validate_request_rejects_invalid_tags_type(self):
        """tags must be tuple[str, ...], not string or other types."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation
        
        req = ReactiveTaskRequest(id="t1", title="Test", tags="abc")  # type: ignore
        with pytest.raises(ReactiveBoundaryViolation, match="tags must be tuple"):
            validate_request(req)
        
        req2 = ReactiveTaskRequest(id="t1", title="Test", tags=("valid", 123))  # type: ignore
        with pytest.raises(ReactiveBoundaryViolation, match=r"tag\[1\] must be str"):
            validate_request(req2)

    def test_validate_request_rejects_empty_title(self):
        """Empty title raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation
        
        req = ReactiveTaskRequest(id="t1", title="", description="Desc")
        with pytest.raises(ReactiveBoundaryViolation, match="title must not be empty"):
            validate_request(req)
        
        req2 = ReactiveTaskRequest(id="t1", title="   ", description="Desc")
        with pytest.raises(ReactiveBoundaryViolation, match="title must not be empty"):
            validate_request(req2)

    def test_validate_request_rejects_overlong_description(self):
        """Description exceeding max chars raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        long_desc = "x" * (config.max_description_chars + 1)
        req = ReactiveTaskRequest(id="t1", title="Test", description=long_desc)
        
        with pytest.raises(ReactiveBoundaryViolation, match="description exceeds"):
            validate_request(req, config)

    def test_validate_request_rejects_too_many_tags(self):
        """Too many tags raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        too_many = tuple(f"tag{i}" for i in range(config.max_tags + 1))
        req = ReactiveTaskRequest(id="t1", title="Test", tags=too_many)
        
        with pytest.raises(ReactiveBoundaryViolation, match="too many tags"):
            validate_request(req, config)

    def test_validate_request_rejects_overlong_tag(self):
        """Tag exceeding max chars raises ReactiveBoundaryViolation."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryViolation, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        long_tag = "x" * (config.max_tag_chars + 1)
        req = ReactiveTaskRequest(id="t1", title="Test", tags=(long_tag,))
        
        with pytest.raises(ReactiveBoundaryViolation, match=r"tag\[0\] exceeds"):
            validate_request(req, config)

    def test_validate_surface_rejects_oversized_payload(self):
        """Surface exceeding max_payload_chars raises ReactiveBoundaryViolation."""
        from runtime.reactive import (
            ReactiveTaskRequest, to_plan_surface, validate_surface,
            ReactiveBoundaryViolation, ReactiveBoundaryConfig
        )
        
        tiny_config = ReactiveBoundaryConfig(max_payload_chars=10)
        req = ReactiveTaskRequest(id="t1", title="Test", description="This will be too long")
        surface = to_plan_surface(req, tiny_config)
        
        with pytest.raises(ReactiveBoundaryViolation, match="surface payload exceeds"):
            validate_surface(surface, tiny_config)


class TestCycle6Immutability:
    """Cycle 6: Dataclasses are frozen."""

    def test_dataclasses_are_frozen(self):
        """Attempting mutation raises FrozenInstanceError."""
        from runtime.reactive import ReactiveTask, ReactiveTaskRequest, ReactiveBoundaryConfig
        from dataclasses import FrozenInstanceError
        
        task = ReactiveTask(id="t1", title="Test", description="Desc")
        with pytest.raises(FrozenInstanceError):
            task.title = "New Title"
        
        req = ReactiveTaskRequest(id="t1", title="Test")
        with pytest.raises(FrozenInstanceError):
            req.title = "New Title"
        
        config = ReactiveBoundaryConfig()
        with pytest.raises(FrozenInstanceError):
            config.max_tags = 100


class TestVersionConstant:
    """A3: Version constant is authoritative and deterministic."""

    def test_version_constant_exists_and_is_string(self):
        """REACTIVE_LAYER_VERSION exists and is a string."""
        from runtime.reactive import REACTIVE_LAYER_VERSION
        
        assert REACTIVE_LAYER_VERSION is not None
        assert isinstance(REACTIVE_LAYER_VERSION, str)

    def test_version_constant_matches_semantic_pattern(self):
        """Version follows expected semantic pattern."""
        from runtime.reactive import REACTIVE_LAYER_VERSION
        import re
        
        pattern = r"^reactive_task_layer\.v\d+\.\d+$"
        assert re.match(pattern, REACTIVE_LAYER_VERSION)

    def test_surface_uses_version_constant(self):
        """Surface version field matches the authoritative constant."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, REACTIVE_LAYER_VERSION
        
        req = ReactiveTaskRequest(id="t1", title="Test")
        surface = to_plan_surface(req)
        
        assert surface["version"] == REACTIVE_LAYER_VERSION


class TestDeterminismHardening:
    """B1: Construction-order invariance for determinism."""

    def test_dict_insertion_order_does_not_affect_canonical_json(self):
        """Two equivalent dicts with different insertion order produce identical canonical_json."""
        from runtime.reactive import canonical_json
        
        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"c": 3, "a": 1, "b": 2}
        
        cj1 = canonical_json(dict1)
        cj2 = canonical_json(dict2)
        
        assert cj1 == cj2

    def test_request_field_order_does_not_affect_surface(self):
        """ReactiveTaskRequest with same values produces identical surface."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req1 = ReactiveTaskRequest(id="t1", title="Test", description="Desc", tags=("a", "b"))
        req2 = ReactiveTaskRequest(title="Test", id="t1", tags=("a", "b"), description="Desc")
        
        cj1 = canonical_json(to_plan_surface(req1))
        cj2 = canonical_json(to_plan_surface(req2))
        
        assert cj1 == cj2


class TestValidationEdgeCases:
    """B2: Boundary edge tests."""

    def test_validate_request_at_exact_title_limit(self):
        """Title at exactly max_title_chars passes."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        exact_title = "x" * config.max_title_chars
        req = ReactiveTaskRequest(id="t1", title=exact_title)
        
        validate_request(req, config)

    def test_validate_request_at_exact_description_limit(self):
        """Description at exactly max_description_chars passes."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        exact_desc = "x" * config.max_description_chars
        req = ReactiveTaskRequest(id="t1", title="Test", description=exact_desc)
        
        validate_request(req, config)

    def test_validate_request_at_exact_tags_limit(self):
        """Exactly max_tags tags passes."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        exact_tags = tuple(f"t{i}" for i in range(config.max_tags))
        req = ReactiveTaskRequest(id="t1", title="Test", tags=exact_tags)
        
        validate_request(req, config)

    def test_validate_request_at_exact_tag_char_limit(self):
        """Tag at exactly max_tag_chars passes."""
        from runtime.reactive import ReactiveTaskRequest, validate_request, ReactiveBoundaryConfig
        
        config = ReactiveBoundaryConfig()
        exact_tag = "x" * config.max_tag_chars
        req = ReactiveTaskRequest(id="t1", title="Test", tags=(exact_tag,))
        
        validate_request(req, config)


class TestUnicodeCoverage:
    """B3: Unicode handling in canonicalization."""

    def test_unicode_in_title_is_escaped(self):
        """Unicode in title is escaped via ensure_ascii=True."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Tâche prioritaire", description="Desc")
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        assert all(ord(c) < 128 for c in cj)
        assert "\\u00e2" in cj

    def test_unicode_in_description_is_escaped(self):
        """Unicode in description is escaped."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="日本語テスト")
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        assert all(ord(c) < 128 for c in cj)

    def test_unicode_in_tags_is_escaped(self):
        """Unicode in tags is escaped."""
        from runtime.reactive import ReactiveTaskRequest, to_plan_surface, canonical_json
        
        req = ReactiveTaskRequest(id="t1", title="Test", tags=("étiquette", "标签"))
        surface = to_plan_surface(req)
        cj = canonical_json(surface)
        
        assert all(ord(c) < 128 for c in cj)


class TestBuildPlanSurface:
    """Tests for the enforced safe entrypoint."""

    def test_build_plan_surface_is_importable(self):
        """build_plan_surface is exported from runtime.reactive."""
        from runtime.reactive import build_plan_surface
        assert build_plan_surface is not None

    def test_build_plan_surface_produces_valid_surface(self):
        """build_plan_surface returns a valid surface for valid input."""
        from runtime.reactive import ReactiveTaskRequest, build_plan_surface, REACTIVE_LAYER_VERSION
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc", tags=("a", "b"))
        surface = build_plan_surface(req)
        
        assert surface["version"] == REACTIVE_LAYER_VERSION
        assert surface["task"]["id"] == "t1"
        assert surface["task"]["title"] == "Test"

    def test_build_plan_surface_rejects_invalid_request(self):
        """build_plan_surface raises on invalid request (chains validation)."""
        from runtime.reactive import ReactiveTaskRequest, build_plan_surface, ReactiveBoundaryViolation
        
        req = ReactiveTaskRequest(id="", title="Test")
        with pytest.raises(ReactiveBoundaryViolation, match="id must not be empty"):
            build_plan_surface(req)

    def test_build_plan_surface_rejects_oversized_payload(self):
        """build_plan_surface raises if surface exceeds max_payload_chars."""
        from runtime.reactive import ReactiveTaskRequest, build_plan_surface, ReactiveBoundaryConfig, ReactiveBoundaryViolation
        
        tiny_config = ReactiveBoundaryConfig(max_payload_chars=10)
        req = ReactiveTaskRequest(id="t1", title="Test", description="This will be too long")
        
        with pytest.raises(ReactiveBoundaryViolation, match="surface payload exceeds"):
            build_plan_surface(req, tiny_config)

    def test_build_plan_surface_is_deterministic(self):
        """Same input produces identical output via build_plan_surface."""
        from runtime.reactive import ReactiveTaskRequest, build_plan_surface, canonical_json, surface_hash
        
        req = ReactiveTaskRequest(id="t1", title="Test", description="Desc")
        s1 = build_plan_surface(req)
        s2 = build_plan_surface(req)
        
        assert canonical_json(s1) == canonical_json(s2)
        assert surface_hash(s1) == surface_hash(s2)
```
