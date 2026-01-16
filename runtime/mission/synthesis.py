"""
Mission Registry v0.2 — Synthesis + Validation

Deterministic mission synthesis from structured inputs.
No I/O, no side effects, no timestamps, no randomness.

v0.2 Contract:
- Input: MissionSynthesisRequest (structured, explicit fields)
- Output: MissionDefinition (validated, deterministic)
- Validation: Hard failures for governance MUSTs

Contract Decisions (locked by tests):
- Tags: Order-significant, case-sensitive, no deduplication (matches v0.1 README)
- ID/Name whitespace: Reject empty/whitespace-only; allow leading/trailing in valid values

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


# =============================================================================
# v0.2 Data Types
# =============================================================================

@dataclass(frozen=True)
class MissionSynthesisRequest:
    """
    Structured request for mission synthesis.
    
    All fields are explicit — no interpretation, no defaults from environment,
    no timestamps, no randomness.
    
    Attributes:
        id: Mission identifier (required, non-empty, validated by MissionBoundaryConfig)
        name: Mission name (required, non-empty, validated by MissionBoundaryConfig)
        description: Optional description
        tags: Order-significant, case-sensitive tags
        metadata: Key-value pairs (sorted by key in output)
    """
    id: str
    name: str
    description: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: Optional[Dict[str, str]] = None


# =============================================================================
# v0.2 Validation
# =============================================================================

def _validate_request(
    request: MissionSynthesisRequest,
    config: MissionBoundaryConfig,
) -> None:
    """
    Validate a synthesis request before building.
    
    Internal function. Raises MissionBoundaryViolation on failure.
    """
    # ID validation — delegate to shared validator via MissionId
    # This ensures consistent error messages with v0.1 boundaries module
    mid = MissionId(value=request.id)
    validate_mission_id(mid, config)
    
    # Name validation
    if not request.name or len(request.name.strip()) == 0:
        raise MissionBoundaryViolation("Name must not be empty")
    
    if len(request.name) > config.max_name_chars:
        raise MissionBoundaryViolation(
            f"Name exceeds {config.max_name_chars} chars"
        )
    
    # Description validation
    if len(request.description) > config.max_description_chars:
        raise MissionBoundaryViolation(
            f"Description exceeds {config.max_description_chars} chars"
        )
    
    # Tags validation
    if len(request.tags) > config.max_tags:
        raise MissionBoundaryViolation(
            f"Too many tags: {len(request.tags)} > {config.max_tags}"
        )
    
    for i, tag in enumerate(request.tags):
        if not isinstance(tag, str):
            raise MissionBoundaryViolation(
                f"Tag[{i}] must be str, got {type(tag).__name__}"
            )
        if len(tag) > config.max_tag_chars:
            raise MissionBoundaryViolation(
                f"Tag[{i}] exceeds {config.max_tag_chars} chars"
            )
    
    # Metadata validation
    if request.metadata is not None:
        if len(request.metadata) > config.max_metadata_pairs:
            raise MissionBoundaryViolation(
                f"Too many metadata pairs: {len(request.metadata)} > {config.max_metadata_pairs}"
            )
        
        for key, value in request.metadata.items():
            if not isinstance(key, str):
                raise MissionBoundaryViolation(
                    f"Metadata key must be str, got {type(key).__name__}"
                )
            if not isinstance(value, str):
                raise MissionBoundaryViolation(
                    f"Metadata value for '{key}' must be str, got {type(value).__name__}"
                )
            if len(key) > config.max_metadata_key_chars:
                raise MissionBoundaryViolation(
                    f"Metadata key '{key}' exceeds {config.max_metadata_key_chars} chars"
                )
            if len(value) > config.max_metadata_value_chars:
                raise MissionBoundaryViolation(
                    f"metadata value for '{key}' exceeds {config.max_metadata_value_chars} chars"
                )


def _build_definition(
    request: MissionSynthesisRequest,
) -> MissionDefinition:
    """
    Build a MissionDefinition from a validated request.
    
    Internal function. Does not validate — caller must validate first.
    
    Metadata is sorted by key for canonical representation.
    """
    # Build sorted metadata tuple
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


# =============================================================================
# v0.2 Public API
# =============================================================================

def synthesize_mission(
    request: MissionSynthesisRequest,
    config: Optional[MissionBoundaryConfig] = None,
) -> MissionDefinition:
    """
    THE SINGLE EXTERNAL ENTRYPOINT for v0.2 mission synthesis.
    
    Chains: validate_request() → build_definition() → validate_definition()
    
    Args:
        request: Structured synthesis request with explicit fields
        config: Optional boundary configuration (uses defaults if None)
    
    Returns:
        Fully validated, immutable MissionDefinition
    
    Raises:
        MissionBoundaryViolation: On any validation failure (fail-closed)
    """
    if config is None:
        config = MissionBoundaryConfig()
    
    # Step 1: Validate request
    _validate_request(request, config)
    
    # Step 2: Build definition
    defn = _build_definition(request)
    
    # Step 3: Validate built definition (defense in depth)
    validate_mission_definition(defn, config)
    
    return defn


def validate_mission_definition_v0_2(
    defn: MissionDefinition,
    config: Optional[MissionBoundaryConfig] = None,
) -> None:
    """
    Validate a mission definition — v0.2 explicit entrypoint.
    
    Uses existing validation infrastructure from boundaries module.
    Specific, verbose name chosen to avoid ambiguity collision.
    
    Args:
        defn: Mission definition to validate
        config: Optional boundary configuration (uses defaults if None)
    
    Returns:
        None on success (validates successfully)
    
    Raises:
        MissionBoundaryViolation: On any validation failure (fail-closed)
    """
    if config is None:
        config = MissionBoundaryConfig()
    
    validate_mission_definition(defn, config)

