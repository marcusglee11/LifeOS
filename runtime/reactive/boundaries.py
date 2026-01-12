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
    """
    Immutable configuration for reactive task boundaries.
    
    All defaults are deterministic.
    """
    max_title_chars: int = 200
    max_description_chars: int = 4000
    max_tags: int = 25
    max_tag_chars: int = 64
    max_payload_chars: int = 8000


def validate_request(
    request: "ReactiveTaskRequest",
    config: Optional[ReactiveBoundaryConfig] = None
) -> None:
    """
    Validate a reactive task request against boundary config.
    
    Raises ReactiveBoundaryViolation on violations.
    Call BEFORE to_plan_surface().
    """
    if config is None:
        config = ReactiveBoundaryConfig()
    
    # ID: must not be empty
    if not request.id or len(request.id.strip()) == 0:
        raise ReactiveBoundaryViolation("id must not be empty")
    
    # Title: must not be empty (whitespace-only counts as empty)
    if not request.title or len(request.title.strip()) == 0:
        raise ReactiveBoundaryViolation("title must not be empty")
    
    # Title: length check
    if len(request.title) > config.max_title_chars:
        raise ReactiveBoundaryViolation(
            f"title exceeds {config.max_title_chars} chars"
        )
    
    # Description: length check
    if len(request.description) > config.max_description_chars:
        raise ReactiveBoundaryViolation(
            f"description exceeds {config.max_description_chars} chars"
        )
    
    # Tags: type check (must be tuple, not string)
    if request.tags is not None:
        if not isinstance(request.tags, tuple):
            raise ReactiveBoundaryViolation(
                f"tags must be tuple, got {type(request.tags).__name__}"
            )
        for i, tag in enumerate(request.tags):
            if not isinstance(tag, str):
                raise ReactiveBoundaryViolation(
                    f"tag[{i}] must be str, got {type(tag).__name__}"
                )
    
    # Tags: count check
    if request.tags is not None and len(request.tags) > config.max_tags:
        raise ReactiveBoundaryViolation(
            f"too many tags: {len(request.tags)} > {config.max_tags}"
        )
    
    # Tags: individual length check
    if request.tags is not None:
        for i, tag in enumerate(request.tags):
            if len(tag) > config.max_tag_chars:
                raise ReactiveBoundaryViolation(
                    f"tag[{i}] exceeds {config.max_tag_chars} chars"
                )


def validate_surface(
    surface: dict,
    config: Optional[ReactiveBoundaryConfig] = None
) -> None:
    """
    Validate a plan surface against boundary config.
    
    Enforces max_payload_chars via len(canonical_json(surface)).
    Call AFTER to_plan_surface().
    """
    from runtime.reactive.interfaces import canonical_json
    
    if config is None:
        config = ReactiveBoundaryConfig()
    
    payload_len = len(canonical_json(surface))
    if payload_len > config.max_payload_chars:
        raise ReactiveBoundaryViolation(
            f"surface payload exceeds {config.max_payload_chars} chars: {payload_len}"
        )
