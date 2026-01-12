"""Council context pack transform."""

from typing import Dict, Any

from .base import register_transform


@register_transform("to_council_context_pack", version="1.0.0")
def to_council_context_pack(packet: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform BUILD_PACKET or REVIEW_PACKET into COUNCIL_CONTEXT_PACK.
    
    Per v0.3 spec: COUNCIL_CONTEXT_PACK with subject, context, review_type fields.
    """
    packet_type = packet.get("packet_type", "UNKNOWN")
    
    return {
        "packet_type": "COUNCIL_CONTEXT_PACK",
        "subject_ref": packet.get("subject_ref", context.get("subject_ref", "")),
        "subject_summary": packet.get("summary", packet.get("scope", {}).get("summary", "")),
        "review_type": "build_review" if packet_type == "BUILD_PACKET" else "completion_review",
        "context_refs": context.get("context_refs", []),
        "source_packet_type": packet_type,
        "phase": "council",
    }
