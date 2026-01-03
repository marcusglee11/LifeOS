"""
Runtime Exception Taxonomy — Shared Base Classes

This module provides the foundational exception hierarchy for the LifeOS runtime.
All exception types are imported from here to avoid cross-tier coupling.

Exception Hierarchy:
    AntiFailureViolation  - Input contract / boundary violations
    EnvelopeViolation     - Structural / governance envelope violations
"""


class AntiFailureViolation(Exception):
    """
    Raised when an operation violates Anti-Failure input contracts or boundaries.
    
    Used for:
    - Step-count and human-step limit violations (orchestration)
    - Mission boundary validations (mission registry)
    - Input validation failures
    """
    pass


class EnvelopeViolation(Exception):
    """
    Raised when an operation violates execution envelope constraints.
    
    Used for:
    - Disallowed step kinds (only 'runtime' and 'human' permitted)
    - Forbidden I/O operations
    - Structural/governance constraint violations
    """
    pass
