"""
Tier-2 Deprecation Utilities.

Provides a deterministic mechanism for emitting deprecation warnings
as structured timeline events, safe for replay.
"""
import runtime.config.flags as flags

def warn_deprecated(
    surface: str,
    replacement: str,
    removal_target: str,
    interface_version: str,
    first_seen_at: str,
    emit_event_fn = None
) -> None:
    """
    Emit a deprecation warning if enabled via flags.DEBUG_DEPRECATION_WARNINGS.
    
    Args:
        surface: The feature/surface being deprecated.
        replacement: The suggested replacement.
        removal_target: Target version for removal.
        interface_version: Current interface version.
        first_seen_at: Deterministic timestamp/identifier for when this was seen.
        emit_event_fn: Callable to emit a timeline event. 
                       
    Note:
        This function is a no-op if flags.DEBUG_DEPRECATION_WARNINGS is False.
        It does NOT emit to stdout/logger, only via emit_event_fn.
    """
    if not flags.DEBUG_DEPRECATION_WARNINGS:
        return

    # Payload for the event
    payload = {
        "event_type": "deprecation_warning",
        "interface_version": interface_version,
        "deprecated_surface": surface,
        "replacement_surface": replacement,
        "removal_target_version": removal_target,
        "first_seen_at": first_seen_at,
    }
    
    if emit_event_fn:
        emit_event_fn(payload)
