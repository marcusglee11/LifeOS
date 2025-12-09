"""
FP-4.x CND-5: Tier-1 Halt Procedure
Emergency halt and AMU₀ rollback functionality.
"""
import sys
import json
import shutil
from typing import Optional, NoReturn
from pathlib import Path
from dataclasses import dataclass

from runtime.util.atomic_write import atomic_write_json


class HaltError(Exception):
    """Raised when halt procedure encounters an error."""
    pass


@dataclass
class HaltEvent:
    """Record of a halt event."""
    timestamp: str
    reason: str
    triggered_by: str
    rollback_performed: bool
    rollback_target: Optional[str]


def log_halt_event(
    lineage,
    timestamp: str,
    reason: str,
    triggered_by: str = "system"
) -> None:
    """
    Log a halt event to AMU₀ lineage.
    
    Args:
        lineage: AMU0Lineage instance.
        timestamp: ISO timestamp.
        reason: Reason for the halt.
        triggered_by: What triggered the halt.
    """
    if lineage:
        try:
            lineage.append_entry(
                entry_id=f"halt_{timestamp}",
                timestamp=timestamp,
                artefact_hash="HALT_EVENT",
                attestation={
                    "type": "runtime_halt",
                    "reason": reason,
                    "triggered_by": triggered_by
                },
                state_delta={"halted": True}
            )
        except Exception:
            # If we can't log, we still need to halt
            pass


def find_last_good_snapshot(amu0_root: str) -> Optional[str]:
    """
    Find the last known good AMU₀ snapshot.
    
    Args:
        amu0_root: Path to AMU₀ root directory.
        
    Returns:
        Path to the last good snapshot, or None if not found.
    """
    snapshots_dir = Path(amu0_root) / "snapshots"
    
    if not snapshots_dir.exists():
        return None
    
    # Find most recent snapshot
    snapshots = sorted(
        [d for d in snapshots_dir.iterdir() if d.is_dir()],
        key=lambda x: x.name,
        reverse=True
    )
    
    for snapshot in snapshots:
        manifest = snapshot / "amu0_manifest.json"
        if manifest.exists():
            return str(snapshot)
    
    return None


def rollback_to_snapshot(
    current_state_path: str,
    snapshot_path: str
) -> bool:
    """
    Rollback current state to a previous snapshot.
    
    Args:
        current_state_path: Path to current state directory.
        snapshot_path: Path to snapshot to restore.
        
    Returns:
        True if rollback succeeded.
    """
    try:
        current = Path(current_state_path)
        snapshot = Path(snapshot_path)
        
        if not snapshot.exists():
            return False
        
        # Backup current state before rollback
        backup_path = current.parent / f"{current.name}.pre_rollback"
        if current.exists():
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.move(str(current), str(backup_path))
        
        # Copy snapshot to current
        shutil.copytree(str(snapshot), str(current))
        
        return True
        
    except Exception:
        return False


def halt_runtime(
    reason: str,
    timestamp: str,
    lineage=None,
    amu0_root: Optional[str] = None,
    current_state_path: Optional[str] = None,
    exit_code: int = 1
) -> NoReturn:
    """
    Execute Tier-1 halt procedure.
    
    1. Log halt event to AMU₀ (if possible)
    2. Attempt rollback to last known good snapshot (if applicable)
    3. Exit process
    
    Args:
        reason: Reason for the halt.
        timestamp: ISO timestamp.
        lineage: Optional AMU0Lineage instance.
        amu0_root: Optional path to AMU₀ root for rollback.
        current_state_path: Optional path to current state for rollback.
        exit_code: Exit code to use (default: 1).
        
    This function does not return.
    """
    # Log halt event
    log_halt_event(lineage, timestamp, reason, "halt_procedure")
    
    # Attempt rollback if paths provided
    rollback_performed = False
    rollback_target = None
    
    if amu0_root and current_state_path:
        snapshot = find_last_good_snapshot(amu0_root)
        if snapshot:
            rollback_target = snapshot
            rollback_performed = rollback_to_snapshot(
                current_state_path,
                snapshot
            )
    
    # Log final halt status
    halt_event = HaltEvent(
        timestamp=timestamp,
        reason=reason,
        triggered_by="halt_runtime",
        rollback_performed=rollback_performed,
        rollback_target=rollback_target
    )
    
    # Write halt report (best effort)
    if amu0_root:
        try:
            report_path = Path(amu0_root) / "HALT_REPORT.json"
            atomic_write_json(report_path, {
                "event": {
                    "timestamp": halt_event.timestamp,
                    "reason": halt_event.reason,
                    "triggered_by": halt_event.triggered_by,
                    "rollback_performed": halt_event.rollback_performed,
                    "rollback_target": halt_event.rollback_target
                }
            })
        except Exception:
            pass
    
    # Exit
    sys.exit(exit_code)


def halt_on_health_failure(
    health_statuses: list,
    timestamp: str,
    lineage=None,
    amu0_root: Optional[str] = None,
    current_state_path: Optional[str] = None
) -> None:
    """
    Check health statuses and halt if any critical failures.
    
    Args:
        health_statuses: List of HealthStatus objects.
        timestamp: ISO timestamp.
        lineage: Optional AMU0Lineage instance.
        amu0_root: Optional path for rollback.
        current_state_path: Optional path for rollback.
    """
    critical_failures = [s for s in health_statuses if not s.ok]
    
    if critical_failures:
        reasons = [f"{s.component}: {s.reason}" for s in critical_failures]
        halt_runtime(
            reason=f"Critical health check failures: {'; '.join(reasons)}",
            timestamp=timestamp,
            lineage=lineage,
            amu0_root=amu0_root,
            current_state_path=current_state_path
        )
