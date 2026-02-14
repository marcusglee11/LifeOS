"""
Doc freshness validator with mode-gated enforcement.

Implements Doc_Freshness_Gate_Spec_v1.0.md with structured contradiction detection.

Modes:
- off: No freshness checking
- warn: Emit warnings but do not fail
- block: Fail on violations

Mode is controlled by env var LIFEOS_DOC_FRESHNESS_MODE (default: off)
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def get_freshness_mode() -> str:
    """Get freshness mode from environment."""
    mode = os.environ.get("LIFEOS_DOC_FRESHNESS_MODE", "off")
    if mode not in {"off", "warn", "block"}:
        # Invalid mode, default to off
        return "off"
    return mode


def check_freshness(repo_root: str) -> tuple[list[str], list[str]]:
    """
    Check doc freshness and contradictions.

    Args:
        repo_root: Path to repository root

    Returns:
        Tuple of (warnings, errors)
        - warnings: List of warning messages
        - errors: List of error messages (blocking in block mode)
    """
    mode = get_freshness_mode()

    if mode == "off":
        # Freshness checking disabled
        return ([], [])

    warnings: list[str] = []
    errors: list[str] = []

    repo_path = Path(repo_root).resolve()
    status_file = repo_path / "artifacts" / "status" / "runtime_status.json"

    # Check if status file exists
    if not status_file.exists():
        msg = f"Runtime status file missing: {status_file}"
        if mode == "warn":
            warnings.append(msg)
        elif mode == "block":
            errors.append(msg)
        return (warnings, errors)

    # Check file age (24h SLA)
    try:
        file_mtime = datetime.fromtimestamp(status_file.stat().st_mtime, tz=timezone.utc)
        age = datetime.now(timezone.utc) - file_mtime
        sla_threshold = timedelta(hours=24)

        if age > sla_threshold:
            hours_stale = int(age.total_seconds() / 3600)
            msg = (
                f"Runtime status file is stale: {status_file} "
                f"(age: {hours_stale}h, SLA: 24h)"
            )
            if mode == "warn":
                warnings.append(msg)
            elif mode == "block":
                errors.append(msg)
    except Exception as e:
        msg = f"Failed to check file age for {status_file}: {e}"
        if mode == "warn":
            warnings.append(msg)
        elif mode == "block":
            errors.append(msg)

    # Load and check structured contradictions
    try:
        with status_file.open("r", encoding="utf-8") as f:
            status_data = json.load(f)

        contradictions = status_data.get("contradictions", [])

        # Process contradictions
        for contradiction in contradictions:
            if not isinstance(contradiction, dict):
                continue

            contradiction_id = contradiction.get("id", "unknown")
            severity = contradiction.get("severity", "warn")
            message = contradiction.get("message", "No message provided")
            refs = contradiction.get("refs", [])

            refs_str = ", ".join(refs) if refs else "no references"
            full_msg = (
                f"Contradiction [{contradiction_id}]: {message} "
                f"(refs: {refs_str})"
            )

            if severity == "block" and mode == "block":
                # Blocking contradiction in block mode
                errors.append(full_msg)
            else:
                # Warn severity, or block mode not active
                if mode in {"warn", "block"}:
                    warnings.append(full_msg)

    except json.JSONDecodeError as e:
        msg = f"Failed to parse runtime status JSON: {status_file}: {e}"
        if mode == "warn":
            warnings.append(msg)
        elif mode == "block":
            errors.append(msg)
    except Exception as e:
        msg = f"Failed to read runtime status file {status_file}: {e}"
        if mode == "warn":
            warnings.append(msg)
        elif mode == "block":
            errors.append(msg)

    return (warnings, errors)
