"""
FP-4.x CND-6: Governance API
Read-only facade for governance interactions.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from runtime.governance.HASH_POLICY_v1 import HASH_ALGORITHM, hash_json
from runtime.amu0.lineage import AMU0Lineage, LineageEntry

# Re-export tool policy functions for use by runtime modules
from runtime.governance.tool_policy import (
    resolve_sandbox_root,
    check_tool_action_allowed,
    check_pytest_scope,
    GovernanceUnavailable,
    PolicyDenied,
)

# Re-export policy loader for loop controller
from runtime.governance.policy_loader import PolicyLoader, PolicyLoadError

# Re-export self-mod protection for orchestration and missions
from runtime.governance.self_mod_protection import (
    PROTECTED_PATHS,
    is_protected,
    SelfModProtector,
)

__all__ = [
    "GovernanceAPI",
    "resolve_sandbox_root",
    "check_tool_action_allowed",
    "check_pytest_scope",
    "GovernanceUnavailable",
    "PolicyDenied",
    "PolicyLoader",
    "PolicyLoadError",
    "PROTECTED_PATHS",
    "is_protected",
    "SelfModProtector",
    "hash_json",
    "HASH_ALGORITHM",
]


class GovernanceAPI:
    """
    Read-only API for governance layer interactions.
    
    Runtime modules must use this API to access governance data.
    Direct access to governance internals is prohibited.
    """
    
    def __init__(self, lineage: Optional[AMU0Lineage] = None):
        self._lineage = lineage
    
    def get_hash_algorithm(self) -> str:
        """Get the council-approved hash algorithm."""
        return HASH_ALGORITHM
    
    def hash_data(self, data: Any) -> str:
        """Compute hash of JSON-serializable data."""
        return hash_json(data)
    
    def get_lineage_entries(self) -> List[Dict[str, Any]]:
        """Get all AMU₀ lineage entries."""
        if not self._lineage:
            return []
        return [e.to_dict() for e in self._lineage.get_entries()]
    
    def get_latest_entry(self) -> Optional[Dict[str, Any]]:
        """Get the most recent lineage entry."""
        if not self._lineage:
            return None
        entry = self._lineage.get_last_entry()
        return entry.to_dict() if entry else None
    
    def verify_chain_integrity(self) -> tuple[bool, List[str]]:
        """Verify AMU₀ hash chain integrity."""
        if not self._lineage:
            return (True, [])
        return self._lineage.verify_chain()
