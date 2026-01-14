"""
OpenCode Governance Service — Phase 1 Skeleton

LIFEOS_TODO[P1][area: opencode_governance/service.py][exit: builder implementation complete + pytest opencode_governance/tests/] When OpenCode builder functionality is implemented, ensure it follows TODO_Standard_v1.0.md for all code generation (use LIFEOS_TODO tags, not generic TODO)
"""
import hashlib
import json
from typing import Any, Dict

from opencode_governance.errors import (
    INVALID_VERSION,
    MISSING_REQUEST_ID,
    INVALID_PAYLOAD,
    INTERNAL_ERROR,
)

API_VERSION = "1.0"

def _canonical_json(obj: Any) -> bytes:
    """Normalize JSON for determinism (Sorted Keys + Separators)."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

def invoke(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main Entrypoint for OpenCode Governance Service.
    
    Args:
        request: Dict containing 'version', 'request_id', 'payload', 'metadata'.
        
    Returns:
        Dict containing 'status', 'request_id', 'output'|'error', 'output_hash'.
    """
    try:
        # 1. Validation
        if not isinstance(request, dict):
            return {
                "status": "ERROR",
                "request_id": "unknown",
                "error": {"code": INVALID_PAYLOAD, "message": "Request must be a dict"}
            }

        request_id = request.get("request_id")
        # Best-effort ID extraction for error cases
        rid = request_id if request_id else "unknown"

        if not request_id:
            return {
                "status": "ERROR",
                "request_id": rid,
                "error": {"code": MISSING_REQUEST_ID, "message": "Missing request_id"}
            }

        version = request.get("version")
        if version != API_VERSION:
            return {
                "status": "ERROR",
                "request_id": rid,
                "error": {
                    "code": INVALID_VERSION, 
                    "message": f"Unsupported version: {version}. Expected: {API_VERSION}"
                }
            }

        payload = request.get("payload")
        if payload is None:
             return {
                "status": "ERROR",
                "request_id": rid,
                "error": {"code": INVALID_PAYLOAD, "message": "Missing payload"}
            }
        
        if not isinstance(payload, dict):
             return {
                "status": "ERROR",
                "request_id": rid,
                "error": {"code": INVALID_PAYLOAD, "message": "Payload must be a dict"}
            }
            
        # 2. Processing (Skeleton: Echo payload)
        # LIFEOS_TODO[P1][area: opencode_governance/service.py:invoke][exit: pytest opencode_governance/tests/test_service.py] Implement real governance processing logic (currently just echoing payload)
        output = {
            "echo": payload,
            "processed": True
        }

        # 3. Determinism
        output_bytes = _canonical_json(output)
        output_hash = hashlib.sha256(output_bytes).hexdigest()

        return {
            "status": "OK",
            "request_id": rid,
            "output": output,
            "output_hash": output_hash
        }

    except Exception:
        # P0: Catch-all for internal errors
        # Safe fallback ID if variable was bound, else 'unknown'
        safe_rid = locals().get("rid", "unknown")
        if safe_rid == "unknown":
            # Try to grab from request one last time in case crash happened before rid binding
            # (though rid is bound early)
            if isinstance(request, dict):
                 safe_rid = request.get("request_id", "unknown")

        return {
            "status": "ERROR",
            "request_id": safe_rid,
            "error": {
                "code": INTERNAL_ERROR,
                "message": "Internal error"
            }
        }
