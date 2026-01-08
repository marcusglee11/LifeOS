"""Review phase packet transform."""

from typing import Dict, Any

from .base import register_transform


@register_transform("to_review_packet", version="1.0.0")
def to_review_packet(packet: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform build output + evidence into a REVIEW_PACKET.
    
    Per v0.3 spec: REVIEW_PACKET with artifacts_produced, test_results, summary.
    """
    return {
        "packet_type": "REVIEW_PACKET",
        "outcome": packet.get("outcome", "pending"),
        "artifacts_produced": packet.get("artifacts", []),
        "test_results": context.get("test_results", {}),
        "summary": packet.get("summary", ""),
        "verification_evidence": context.get("evidence", {}),
        "phase": "review",
    }
