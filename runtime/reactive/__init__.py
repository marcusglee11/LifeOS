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
