"""
FP-4.x CND-5: Health Checks
Health verification for DAP, INDEX, and AMU₀.
"""
import os
import json
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HealthStatus:
    """Status of a health check."""
    ok: bool
    component: str
    reason: str
    details: Optional[dict] = None


def check_dap_write_health(
    dap_gateway,
    test_path: str
) -> HealthStatus:
    """
    Check DAP write gateway health.
    
    Attempts a validation (not actual write) to verify
    the gateway is functioning correctly.
    
    Args:
        dap_gateway: DAPWriteGateway instance.
        test_path: Path within allowed boundaries to test.
        
    Returns:
        HealthStatus indicating gateway health.
    """
    try:
        # Just validate - don't actually write
        dap_gateway.validate_write(test_path, "health_check")
        return HealthStatus(
            ok=True,
            component="DAP",
            reason="DAP gateway validation successful"
        )
    except Exception as e:
        return HealthStatus(
            ok=False,
            component="DAP",
            reason=f"DAP gateway validation failed: {e}"
        )


def check_index_coherence(
    index_updater
) -> HealthStatus:
    """
    Check INDEX coherence with directory contents.
    
    Args:
        index_updater: IndexUpdater instance.
        
    Returns:
        HealthStatus indicating INDEX health.
    """
    try:
        is_coherent, missing, orphaned = index_updater.verify_coherence()
        
        if is_coherent:
            return HealthStatus(
                ok=True,
                component="INDEX",
                reason="INDEX is coherent with directory contents"
            )
        else:
            return HealthStatus(
                ok=False,
                component="INDEX",
                reason="INDEX is incoherent",
                details={
                    "missing_from_index": missing,
                    "orphaned_in_index": orphaned
                }
            )
    except Exception as e:
        return HealthStatus(
            ok=False,
            component="INDEX",
            reason=f"INDEX coherence check failed: {e}"
        )


def check_amu0_readability(
    lineage_path: str
) -> HealthStatus:
    """
    Check AMU₀ lineage readability.
    
    Args:
        lineage_path: Path to AMU₀ lineage file.
        
    Returns:
        HealthStatus indicating AMU₀ health.
    """
    try:
        path = Path(lineage_path)
        
        if not path.exists():
            return HealthStatus(
                ok=False,
                component="AMU0",
                reason=f"AMU₀ lineage file not found: {lineage_path}"
            )
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Basic structure validation
        if "entries" not in data:
            return HealthStatus(
                ok=False,
                component="AMU0",
                reason="AMU₀ lineage missing 'entries' key"
            )
        
        entry_count = len(data.get("entries", []))
        return HealthStatus(
            ok=True,
            component="AMU0",
            reason=f"AMU₀ lineage readable ({entry_count} entries)",
            details={"entry_count": entry_count}
        )
        
    except json.JSONDecodeError as e:
        return HealthStatus(
            ok=False,
            component="AMU0",
            reason=f"AMU₀ lineage JSON parse error: {e}"
        )
    except Exception as e:
        return HealthStatus(
            ok=False,
            component="AMU0",
            reason=f"AMU₀ readability check failed: {e}"
        )


def check_amu0_chain_integrity(lineage) -> HealthStatus:
    """
    Check AMU₀ hash chain integrity.
    
    Args:
        lineage: AMU0Lineage instance.
        
    Returns:
        HealthStatus indicating chain integrity.
    """
    try:
        is_valid, errors = lineage.verify_chain()
        
        if is_valid:
            return HealthStatus(
                ok=True,
                component="AMU0_CHAIN",
                reason="AMU₀ hash chain is valid"
            )
        else:
            return HealthStatus(
                ok=False,
                component="AMU0_CHAIN",
                reason="AMU₀ hash chain integrity failure",
                details={"errors": errors}
            )
    except Exception as e:
        return HealthStatus(
            ok=False,
            component="AMU0_CHAIN",
            reason=f"AMU₀ chain verification failed: {e}"
        )


def run_all_health_checks(
    dap_gateway=None,
    test_path: str = None,
    index_updater=None,
    lineage_path: str = None,
    lineage=None
) -> list[HealthStatus]:
    """
    Run all available health checks.
    
    Args:
        dap_gateway: Optional DAPWriteGateway instance.
        test_path: Test path for DAP health check.
        index_updater: Optional IndexUpdater instance.
        lineage_path: Path to AMU₀ lineage file.
        lineage: Optional AMU0Lineage instance.
        
    Returns:
        List of HealthStatus results.
    """
    results = []
    
    if dap_gateway and test_path:
        results.append(check_dap_write_health(dap_gateway, test_path))
    
    if index_updater:
        results.append(check_index_coherence(index_updater))
    
    if lineage_path:
        results.append(check_amu0_readability(lineage_path))
    
    if lineage:
        results.append(check_amu0_chain_integrity(lineage))
    
    return results
