"""
OpenCode Governance Service — Error Taxonomy
"""
from dataclasses import dataclass
from typing import Optional

# Error Codes
INVALID_VERSION = "INVALID_VERSION"
MISSING_REQUEST_ID = "MISSING_REQUEST_ID"
INVALID_PAYLOAD = "INVALID_PAYLOAD"
INTERNAL_ERROR = "INTERNAL_ERROR"

@dataclass(frozen=True)
class GovernanceError:
    code: str
    message: str
    details: Optional[dict] = None
