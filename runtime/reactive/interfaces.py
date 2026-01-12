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
    """Immutable reactive task definition."""
    id: str
    title: str
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)  # tuple for immutability


@dataclass(frozen=True)
class ReactiveTaskRequest:
    """Immutable request for creating a reactive task surface."""
    id: str
    title: str
    description: str = ""
    tags: Optional[tuple[str, ...]] = None  # None -> [] in surface


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
    
    # Normalize tags: None -> []
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
    
    Pinned settings:
    - sort_keys=True
    - separators=(",", ":")
    - ensure_ascii=True
    - allow_nan=False
    """
    return json.dumps(
        surface,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False
    )


def surface_hash(surface: ReactivePlanSurface) -> str:
    """
    Compute SHA256 hash of canonical JSON representation.
    
    Returns 64-char hex string.
    """
    return hashlib.sha256(canonical_json(surface).encode("utf-8")).hexdigest()
