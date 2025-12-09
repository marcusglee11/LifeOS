"""
FP-4.x CND-3: Governance Override Protocol
Council-only override path with AMU₀ logging.
"""
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from runtime.governance.HASH_POLICY_v1 import hash_json
from runtime.util.atomic_write import atomic_write_json


class OverrideProtocolError(Exception):
    """Raised when override protocol violations occur."""
    pass


@dataclass
class HumanApproval:
    """Human approval attestation for overrides."""
    approver_id: str
    approval_type: str  # "intent" | "approve" | "veto"
    timestamp: str
    signature: str = ""


@dataclass
class OverrideRequest:
    """Request model for governance surface override."""
    id: str
    timestamp: str
    reason: str
    target_surface: str
    requested_change_hash: str
    human_approval: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def compute_hash(self) -> str:
        return hash_json(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OverrideRequest':
        return cls(**data)


class OverrideProtocol:
    """
    Council-only override protocol for governance surfaces.
    
    Provides:
    - Request preparation (no write)
    - Override application (council-controlled)
    - AMU₀ lineage logging of all overrides
    """
    
    def __init__(self, lineage_manager=None, override_log_path: Optional[str] = None):
        """
        Initialize override protocol.
        
        Args:
            lineage_manager: AMU0Lineage instance for logging.
            override_log_path: Path to override log file.
        """
        self.lineage_manager = lineage_manager
        self.override_log_path = Path(override_log_path) if override_log_path else None
        self._pending_requests: Dict[str, OverrideRequest] = {}
    
    def prepare_override_request(
        self,
        request_id: str,
        timestamp: str,
        reason: str,
        target_surface: str,
        requested_change_hash: str,
        human_approval: Dict[str, Any]
    ) -> OverrideRequest:
        """
        Prepare an override request (no write operation).
        
        This can be called by runtime to structure a request,
        but does not apply the override.
        
        Args:
            request_id: Unique identifier for this request.
            timestamp: ISO timestamp.
            reason: Reason for the override.
            target_surface: Path to the governance surface.
            requested_change_hash: Hash of the proposed change.
            human_approval: Approval attestation.
            
        Returns:
            Prepared OverrideRequest.
        """
        request = OverrideRequest(
            id=request_id,
            timestamp=timestamp,
            reason=reason,
            target_surface=target_surface,
            requested_change_hash=requested_change_hash,
            human_approval=human_approval
        )
        
        self._pending_requests[request_id] = request
        return request
    
    def apply_override(
        self,
        request: OverrideRequest,
        council_key: str
    ) -> bool:
        """
        Apply a governance override (council-controlled path).
        
        This method should only be callable when explicitly
        triggered through council-controlled mechanisms.
        
        Args:
            request: The override request to apply.
            council_key: Council authorization key.
            
        Returns:
            True if override was applied successfully.
            
        Raises:
            OverrideProtocolError: If authorization fails.
        """
        # Validate council authorization
        if not self._validate_council_key(council_key):
            raise OverrideProtocolError(
                "Council authorization failed. Override not applied."
            )
        
        # Validate human approval is present
        if not request.human_approval:
            raise OverrideProtocolError(
                "Human approval required for governance override."
            )
        
        # Log to AMU₀ lineage if available
        if self.lineage_manager:
            self.lineage_manager.append_entry(
                entry_id=f"override_{request.id}",
                timestamp=request.timestamp,
                artefact_hash=request.requested_change_hash,
                attestation={
                    "type": "governance_override",
                    "target": request.target_surface,
                    "reason": request.reason,
                    "human_approval": request.human_approval
                },
                state_delta={"override_request": request.to_dict()}
            )
        
        # Log to override log if configured
        if self.override_log_path:
            self._append_to_log(request)
        
        # Remove from pending
        if request.id in self._pending_requests:
            del self._pending_requests[request.id]
        
        return True
    
    def _validate_council_key(self, key: str) -> bool:
        """
        Validate council authorization key.
        
        For Tier-1, this is a placeholder that accepts
        a specific test key. In production, this would
        verify cryptographic signatures.
        """
        # Tier-1 placeholder validation
        return key == "COUNCIL_TIER1_TEST_KEY"
    
    def _append_to_log(self, request: OverrideRequest) -> None:
        """Append override request to log file."""
        log = []
        if self.override_log_path.exists():
            with open(self.override_log_path, 'r') as f:
                log = json.load(f)
        
        log.append({
            "request": request.to_dict(),
            "request_hash": request.compute_hash()
        })
        
        atomic_write_json(self.override_log_path, log)
    
    def get_pending_requests(self) -> Dict[str, OverrideRequest]:
        """Get all pending override requests."""
        return self._pending_requests.copy()
